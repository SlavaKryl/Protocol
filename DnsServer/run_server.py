import argparse
from DnsServer.main.server import DNSServer

def main():
    parser = argparse.ArgumentParser(description='Кэширующий DNS сервер')
    parser.add_argument('--port', type=int, default=53535, help='Порт для прослушивания (по умолчанию: 53535)')
    parser.add_argument('--cache-file', default='data/cache.pickle', help='Файл для хранения кэша')
    args = parser.parse_args()

    server = DNSServer(args.cache_file)
    try:
        server.start(args.port)
    except KeyboardInterrupt:
        print("\nСервер останавливается...")
        server.stop()

if __name__ == '__main__':
    main()