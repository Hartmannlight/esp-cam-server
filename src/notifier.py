import logging
import requests
from pydantic import HttpUrl


class KumaNotifier:
    def __init__(self, url: HttpUrl, threshold: int):
        self.url = url
        self.threshold = threshold
        self.fail_count = 0

    def success(self):
        self.fail_count = 0
        self._notify('up', 'OK')

    def failure(self, msg: str):
        self.fail_count += 1
        if self.fail_count >= self.threshold:
            self._notify('down', msg)
            self.fail_count = 0

    def _notify(self, status: str, msg: str):
        try:
            requests.get(f'{self.url}?status={status}&msg={msg}', timeout=5)
            logging.debug(f'Kuma notified {status}')
        except Exception as e:
            logging.error(f'Kuma notify failed: {e}')
