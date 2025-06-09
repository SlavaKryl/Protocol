import socket
import threading
import time
from DnsServer.main.dns_packet import DNSPacket
from DnsServer.main.cache import DNSCache


class DNSServer:
    def __init__(self, cache_file='data/cache.pickle'):
        self.cache = DNSCache(cache_file)
        self.running = False
        self.cleanup_thread = threading.Thread(target=self.cleanup_cache)
        self.cleanup_thread.daemon = True

    def start(self, port=53):
        """Запуск DNS сервера на указанном порту"""
        try:
            self.running = True
            self.cleanup_thread.start()

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('0.0.0.0', port))
                print(f"DNS сервер запущен на порту {port}")

                while self.running:
                    try:
                        data, addr = sock.recvfrom(512)
                        threading.Thread(target=self.handle_request, args=(sock, data, addr)).start()
                    except socket.error as e:
                        print(f"Ошибка сокета: {e}")
                    except Exception as e:
                        print(f"Неожиданная ошибка: {e}")

        except Exception as e:
            print(f"Не удалось запустить сервер: {e}")
        finally:
            self.stop()

    def handle_request(self, sock, data, addr):
        """Обработка DNS запроса"""
        try:
            # Парсим запрос
            request = DNSPacket.parse(data)

            # Проверяем кэш
            response = self.cache.get_response(request)

            if not response:
                # Если нет в кэше, выполняем рекурсивный запрос
                response = self.recursive_resolve(request)
                if response:
                    # Добавляем все записи в кэш
                    self.cache.update(response)

            if response:
                sock.sendto(response.raw_data, addr)
            else:
                # Отправляем ошибку, если не удалось разрешить
                error_response = request.create_error_response()
                sock.sendto(error_response.raw_data, addr)

        except Exception as e:
            print(f"Ошибка обработки запроса: {e}")

    def recursive_resolve(self, request):
        """Рекурсивное разрешение DNS запроса"""
        # Здесь должна быть логика рекурсивного запроса к корневым серверам
        # Это упрощенная версия - в реальности нужно реализовать полный алгоритм

        try:
            # Запрос к Google DNS (как пример)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(5)  # Таймаут 5 секунд
                s.sendto(request.raw_data, ('8.8.8.8', 53))
                data, _ = s.recvfrom(512)
                return DNSPacket.parse(data)
        except socket.timeout:
            print("Таймаут при запросе к вышестоящему DNS серверу")
            return None
        except Exception as e:
            print(f"Ошибка рекурсивного разрешения: {e}")
            return None

    def cleanup_cache(self):
        """Периодическая очистка кэша от просроченных записей"""
        while self.running:
            time.sleep(60)  # Проверка каждую минуту
            self.cache.cleanup()

    def stop(self):
        """Остановка сервера"""
        self.running = False
        self.cache.save()
        print("DNS сервер остановлен")