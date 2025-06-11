# src/worker.py
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config import CameraConfig
from src.notifier import KumaNotifier
from src.processors import build_postprocessors
from src.storages import SingleImageStorage, VideoSnippetStorage


class CameraWorker:
    def __init__(self, cfg: CameraConfig):
        self.id = cfg.id
        self.url = str(cfg.url)
        self.storages = [self._create_storage(s) for s in cfg.storage]
        self.post_processors = build_postprocessors(cfg)
        self.notifier = (
            KumaNotifier(cfg.kuma.push_url, cfg.kuma.failure_threshold)
            if cfg.kuma
            else None
        )
        self.triggers = cfg.triggers

        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        self.session = session

    def _create_storage(self, s):
        if s.type == 'single_image':
            return SingleImageStorage(s.root)
        return VideoSnippetStorage(s.root, s.batch_size, s.fps, s.crf, s.preset)

    def job(self):
        try:
            response = self.session.get(self.url, timeout=10)
            response.raise_for_status()
            img = response.content
            for pp in self.post_processors:
                img = pp.process(img)
            for storage in self.storages:
                storage.store(self.id, img)
            if self.notifier:
                self.notifier.success()
        except Exception as e:
            logging.error(f'error for {self.id}: {e}')
            if self.notifier:
                self.notifier.failure(str(e))

    def flush(self):
        for storage in self.storages:
            if isinstance(storage, VideoSnippetStorage):
                storage.flush(self.id)
