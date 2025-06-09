import unittest
import threading
import time
import socket

from DnsServer.main.cache import DNSCache
from DnsServer.main.server import DNSServer
from DnsServer.main.dns_packet import DNSPacket, DNSQuestion, DNSRecord


class TestDNSServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = DNSServer(":memory:")
        cls.test_port = 53535  # Используем другой порт
        cls.server_thread = threading.Thread(target=cls.server.start, kwargs={'port': cls.test_port})
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(1)  # Увеличиваем время ожидания запуска сервера

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        import gc
        gc.collect()

    def test_server_start(self):
        """Тестирование базовой функциональности сервера"""
        # Проверяем, что сервер запущен и слушает порт
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(2)

            # Простой DNS запрос для example.com (корректно сформированный)
            query = (
                b'\xab\xcd'  # ID
                b'\x01\x00'  # Flags: стандартный запрос
                b'\x00\x01'  # 1 вопрос
                b'\x00\x00'  # 0 ответов
                b'\x00\x00'  # 0 authority
                b'\x00\x00'  # 0 additional
                b'\x07example\x03com\x00'  # Домен
                b'\x00\x01'  # Тип A
                b'\x00\x01'  # Класс IN
            )

            try:
                s.sendto(query, ('127.0.0.1', self.test_port))
                data, _ = s.recvfrom(512)

                # Проверяем минимальные требования к ответу
                self.assertGreater(len(data), 12, "Ответ слишком короткий")
                self.assertEqual(data[:2], b'\xab\xcd', "ID ответа не совпадает с запросом")
                # Проверяем что это ответ (бит QR=1)
                self.assertTrue(data[2] & 0x80, "Это не DNS ответ")

            except socket.timeout:
                # Проверяем, действительно ли сервер слушает порт
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check_sock:
                    result = check_sock.connect_ex(('127.0.0.1', self.test_port))
                    if result == 0:
                        self.fail("Сервер запущен, но не отвечает на DNS запросы")
                    else:
                        self.fail(f"Сервер не запущен (порт {self.test_port} не занят)")

    def test_cache_operation(self):
        """Тестирование работы кэша"""
        # Создаем тестовый DNS пакет
        question = DNSQuestion("test.com", 1, 1)  # A record
        record = DNSRecord("test.com", 1, 1, 300, socket.inet_aton("127.0.0.1"))
        packet = DNSPacket(
            id=1234,
            flags=0x8180,
            questions=[question],
            answers=[record],
            authorities=[],
            additionals=[]
        )

        # Проверяем кэш
        self.server.cache.update(packet)
        cached_response = self.server.cache.get_response(packet)
        self.assertIsNotNone(cached_response, "Ответ не найден в кэше")
        self.assertEqual(len(cached_response.answers), 1, "Неверное количество записей в кэше")


class TestDNSCache(unittest.TestCase):
    def setUp(self):
        self.cache = DNSCache(":memory:")

    def test_cache_expiration(self):
        """Тестирование очистки кэша по TTL"""
        record = DNSRecord("expire.com", 1, 1, 1, socket.inet_aton("127.0.0.1"))  # TTL=1 секунда
        packet = DNSPacket(
            id=1234,
            flags=0x8180,
            questions=[DNSQuestion("expire.com", 1, 1)],
            answers=[record],
            authorities=[],
            additionals=[]
        )

        self.cache.update(packet)
        self.assertTrue("expire.com" in self.cache.name_to_records, "Запись не добавлена в кэш")

        time.sleep(1.1)  # Ждем истечения TTL
        self.cache.cleanup()
        self.assertFalse("expire.com" in self.cache.name_to_records, "Просроченная запись не удалена")


if __name__ == '__main__':
    unittest.main()