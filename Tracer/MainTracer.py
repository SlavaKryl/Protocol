import argparse
import socket

from Tracer import Tracer
from typing import List, Dict, Optional


def print_results_table(results: List[Dict]):
    """Выводит результаты в виде таблицы"""
    print("\nРезультаты трассировки автономных систем:")
    print("{:<5} {:<15} {:<10} {:<10} {:<20}".format(
        "№", "IP", "AS", "Страна", "Провайдер"
    ))
    print("-" * 60)

    for res in results:
        print("{:<5} {:<15} {:<10} {:<10} {:<20}".format(
            res['hop'],
            res['ip'],
            res['asn'] if res['asn'] else "N/A",
            res['country'] if res['country'] else "N/A",
            res['provider'] if res['provider'] else "N/A"
        ))


def resolve_target(target: str) -> Optional[str]:
    """Преобразует домен в IP, если нужно"""
    try:
        if not Tracer.is_public_ip(target):
            return socket.gethostbyname(target)
        return target
    except (socket.gaierror, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Трассировка автономных систем с определением страны и провайдера'
    )
    parser.add_argument(
        'target',
        type=str,
        help='Целевой домен или IP-адрес'
    )
    args = parser.parse_args()

    tracer = Tracer()
    resolved_target = resolve_target(args.target)

    if not resolved_target:
        print("Ошибка: неверный домен или IP-адрес")
        return

    print(f"\nНачало трассировки к {args.target} ({resolved_target})...")
    trace_output = tracer.trace_route(resolved_target)

    if not trace_output:
        print("Ошибка при выполнении трассировки")
        return

    print("\nПромежуточные узлы:")
    for line in trace_output:
        print(line)

    hops = tracer.parse_trace_output(trace_output)
    if not hops:
        print("\nНе удалось определить IP-адреса маршрутизаторов")
        return

    results = []
    for i, ip in enumerate(hops, 1):
        asn, country, provider = tracer.get_asn_info(ip)
        results.append({
            'hop': i,
            'ip': ip,
            'asn': asn,
            'country': country,
            'provider': provider
        })

    print_results_table(results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
