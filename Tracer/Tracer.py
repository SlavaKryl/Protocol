import logging
import os
import re
import subprocess
from ipaddress import ip_address, IPv4Address
from typing import Tuple, Optional, List

import requests


class Tracer:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AS_Tracer')

    @staticmethod
    def is_public_ip(ip: str) -> bool:
        try:
            ip_obj = ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return False
            return isinstance(ip_obj, IPv4Address)  # Сделал поддержку только для Ipv4, IPv6 не трогал
        except ValueError:
            return False

    def get_asn_info(self, ip: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if not self.is_public_ip(ip):
            return None, None, None
        try:
            response = requests.get(
                f"https://stat.ripe.net/data/whois/data.json?resource={ip}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            asn = country = provider = None

            for record_group in data.get('data', {}).get('records', []):
                for record in record_group:
                    key = record.get('key', '').lower()
                    value = record.get('value', '')

                    if key == 'origin' and not asn:
                        asn = value.split()[-1]
                    elif key == 'country' and not country:
                        country = value
                    elif key == 'netname' and not provider:
                        provider = value

            return asn, country, provider
        except (requests.RequestException, ValueError) as e:
            self.logger.error(f"Ошибка запроса WHOIS для {ip}: {str(e)}")
            return None, None, None

    def trace_route(self, target: str) -> Optional[List[str]]:
        try:
            if os.name == 'nt':
                cmd = ['tracert', '-d', target]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='ignore'
                )
            else:
                cmd = ['traceroute', '-n', target]
                env = os.environ.copy()
                env['LANG'] = 'C.UTF-8'
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    env=env
                )

            output = []
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                clean_line = line.strip()
                output.append(clean_line)
                if '***' in clean_line:
                    break

            return output if output else None

        except subprocess.SubprocessError as e:
            self.logger.error(f"Ошибка трассировки: {str(e)}")
            return None

    @staticmethod
    def parse_trace_output(output: List[str]) -> List[str]:
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        hops = []

        for line in output:
            if '***' in line:
                break

            ips = re.findall(ip_pattern, line)
            if not ips:
                continue

            hop_ip = ips[-1] if len(ips) > 1 else ips[0]
            if hop_ip not in hops:  # Исключаем дубликаты
                hops.append(hop_ip)

        return hops
