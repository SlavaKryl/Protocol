import struct
import socket
import time
from dataclasses import dataclass
from enum import IntEnum


class DNSType(IntEnum):
    A = 1
    NS = 2
    CNAME = 5
    SOA = 6
    MX = 15
    AAAA = 28


class DNSClass(IntEnum):
    IN = 1


@dataclass
class DNSQuestion:
    name: str
    type: DNSType
    cls: DNSClass


@dataclass(frozen=True)  # Добавляем frozen=True для хешируемости
class DNSRecord:
    name: str
    type: int
    cls: int
    ttl: int
    data: bytes

    def __post_init__(self):
        object.__setattr__(self, 'expiration_time', time.time() + self.ttl)

    @property
    def value(self):
        if self.type == 1:  # A record
            return socket.inet_ntoa(self.data)
        return self.data.decode('ascii', errors='ignore')


@dataclass
class DNSPacket:
    id: int
    flags: int
    questions: list[DNSQuestion]
    answers: list[DNSRecord]
    authorities: list[DNSRecord]
    additionals: list[DNSRecord]
    raw_data: bytes = b''

    @classmethod
    def parse(cls, data):
        """Парсинг DNS пакета из bytes"""
        raw_data = data
        header = struct.unpack('!HHHHHH', data[:12])
        id = header[0]
        flags = header[1]
        qdcount = header[2]
        ancount = header[3]
        nscount = header[4]
        arcount = header[5]

        offset = 12
        questions = []
        for _ in range(qdcount):
            name, offset = cls.parse_name(data, offset)
            qtype, qclass = struct.unpack('!HH', data[offset:offset + 4])
            questions.append(DNSQuestion(name, DNSType(qtype), DNSClass(qclass)))
            offset += 4

        answers = cls.parse_records(data, offset, ancount)
        offset += ancount * (12 if ancount else 0)  # Упрощение
        authorities = cls.parse_records(data, offset, nscount)
        offset += nscount * (12 if nscount else 0)  # Упрощение
        additionals = cls.parse_records(data, offset, arcount)

        return cls(id, flags, questions, answers, authorities, additionals, raw_data)

    @staticmethod
    def parse_name(data, offset):
        """Парсинг доменного имени"""
        parts = []
        while True:
            length = data[offset]
            if length == 0:
                offset += 1
                break
            if length & 0xC0 == 0xC0:  # Указатель
                pointer = struct.unpack('!H', data[offset:offset + 2])[0] & 0x3FFF
                part, _ = DNSPacket.parse_name(data, pointer)
                parts.append(part)
                offset += 2
                break
            else:
                offset += 1
                parts.append(data[offset:offset + length].decode('ascii'))
                offset += length
        return '.'.join(parts), offset

    @staticmethod
    def parse_records(data, offset, count):
        """Парсинг DNS записей"""
        records = []
        for _ in range(count):
            name, offset = DNSPacket.parse_name(data, offset)
            rtype, rclass, ttl, rdlength = struct.unpack('!HHIH', data[offset:offset + 10])
            offset += 10
            rdata = data[offset:offset + rdlength]
            offset += rdlength

            if DNSType(rtype) == DNSType.A and rdlength == 4:
                records.append(DNSRecord(name, DNSType(rtype), DNSClass(rclass), ttl, rdata))
            elif DNSType(rtype) == DNSType.AAAA and rdlength == 16:
                records.append(DNSRecord(name, DNSType(rtype), DNSClass(rclass), ttl, rdata))
            elif DNSType(rtype) in (DNSType.NS, DNSType.CNAME):
                name_value, _ = DNSPacket.parse_name(data, offset - rdlength)
                records.append(DNSRecord(name, DNSType(rtype), DNSClass(rclass), ttl, rdata))
            else:
                records.append(DNSRecord(name, DNSType(rtype), DNSClass(rclass), ttl, rdata))
        return records

    def create_response(self):
        """Создание ответного пакета"""
        # Упрощенная версия - в реальности нужно правильно формировать флаги и заголовок
        return DNSPacket(
            id=self.id,
            flags=0x8180,  # QR=1, RD=1, RA=1, RCODE=0
            questions=self.questions,
            answers=[],
            authorities=[],
            additionals=[]
        )

    def add_answer(self, record):
        """Добавление записи в ответ"""
        self.answers.append(record)

    def create_error_response(self):
        """Создание пакета с ошибкой"""
        return DNSPacket(
            id=self.id,
            flags=0x8183,  # QR=1, RD=1, RA=1, RCODE=3 (Name Error)
            questions=self.questions,
            answers=[],
            authorities=[],
            additionals=[]
        )