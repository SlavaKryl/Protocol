import pickle
import time
from collections import defaultdict
from threading import Lock


class DNSCache:
    def __init__(self, cache_file):
        self.cache_file = cache_file
        self.lock = Lock()
        self.name_to_records = defaultdict(set)
        self.value_to_names = defaultdict(set)
        self.load()

    def update(self, dns_packet):
        """Обновление кэша на основе DNS пакета"""
        with self.lock:
            # Обрабатываем все секции
            for record in dns_packet.answers + dns_packet.authorities + dns_packet.additionals:
                self._add_record(record)

    def _add_record(self, record):
        """Добавление одной записи в кэш"""
        name = record.name.lower()
        value = getattr(record, 'value', None)

        # Добавляем в name_to_records
        self.name_to_records[name].add(record)

        # Добавляем в value_to_names, если есть значение
        if value:
            self.value_to_names[value].add(name)

    def load(self):
        """Загрузка кэша с диска"""
        try:
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)
                self.name_to_records = data['name_to_records']
                self.value_to_names = data['value_to_names']
                self.cleanup()  # Удаляем просроченные записи при загрузке
        except (FileNotFoundError, EOFError, pickle.PickleError):
            print("Не удалось загрузить кэш, начнем с пустого")
            self.name_to_records = defaultdict(set)
            self.value_to_names = defaultdict(set)

    def save(self):
        """Сохранение кэша на диск"""
        with self.lock:
            try:
                with open(self.cache_file, 'wb') as f:
                    pickle.dump({
                        'name_to_records': self.name_to_records,
                        'value_to_names': self.value_to_names
                    }, f)
            except Exception as e:
                print(f"Ошибка сохранения кэша: {e}")

    def get_response(self, request):
        """Попытка получить ответ из кэша"""
        with self.lock:
            # Проверяем, есть ли запрашиваемые данные в кэше
            # Это упрощенная версия - в реальности нужно проверять тип записи и т.д.
            query_name = request.questions[0].name.lower()

            if query_name in self.name_to_records:
                # Создаем ответ на основе данных из кэша
                response = request.create_response()
                for record in self.name_to_records[query_name]:
                    if time.time() < record.expiration_time:
                        response.add_answer(record)
                    else:
                        # Удаляем просроченную запись
                        self._remove_record(record)

                if len(response.answers) > 0:
                    return response

        return None

    def _remove_record(self, record):
        """Удаление записи из кэша"""
        name = record.name.lower()
        value = record.value.lower() if hasattr(record, 'value') else None

        if name in self.name_to_records and record in self.name_to_records[name]:
            self.name_to_records[name].remove(record)
            if not self.name_to_records[name]:
                del self.name_to_records[name]

        if value and value in self.value_to_names and name in self.value_to_names[value]:
            self.value_to_names[value].remove(name)
            if not self.value_to_names[value]:
                del self.value_to_names[value]

    def cleanup(self):
        """Очистка просроченных записей"""
        with self.lock:
            current_time = time.time()
            expired_records = []

            for name, records in self.name_to_records.items():
                for record in records:
                    if current_time >= record.expiration_time:
                        expired_records.append(record)

            for record in expired_records:
                self._remove_record(record)