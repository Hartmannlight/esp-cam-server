# main.py
import logging
import time
import signal
import sys

from pydantic import ValidationError
from src.config import load_config
from src.scheduler import setup_scheduler
from src.worker import CameraWorker


def main():
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt=date_format)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)

    try:
        cfg = load_config('config.yml')
    except ValidationError as e:
        logging.error(f'configuration error:\n{e}')
        return

    workers = [CameraWorker(cam) for cam in cfg.cameras]
    scheduler = setup_scheduler(workers)

    def shutdown(signum, frame):
        logging.info('shutting down, flushing pending frames')
        scheduler.shutdown(wait=False)
        for w in workers:
            w.flush()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        time.sleep(3600)


if __name__ == '__main__':
    main()
