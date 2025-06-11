# src/scheduler.py
from pytz import timezone
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from src.worker import CameraWorker
from src.config import IntervalTriggerConfig, CronTriggerConfig


def setup_scheduler(workers: List[CameraWorker]) -> BackgroundScheduler:
    executors = {'default': ThreadPoolExecutor(max_workers=5)}
    job_defaults = {'coalesce': False, 'max_instances': 3}
    scheduler = BackgroundScheduler(
        timezone=timezone('Europe/Berlin'),
        executors=executors,
        job_defaults=job_defaults,
        jobstores={'default': MemoryJobStore()},
    )

    for worker in workers:
        for idx, trig in enumerate(worker.triggers):
            job_base = f'{worker.id}_{idx}'
            if isinstance(trig, IntervalTriggerConfig):
                sec = trig.seconds
                if trig.start_time and trig.end_time:
                    sh = int(trig.start_time.split(':')[0])
                    eh = int(trig.end_time.split(':')[0])
                    ranges = []
                    if sh < eh:
                        ranges.append(f'{sh}-{eh-1}')
                    else:
                        ranges.append(f'{sh}-23')
                        if eh > 0:
                            ranges.append(f'0-{eh-1}')
                    for hr in ranges:
                        cron = CronTrigger(second=f'*/{sec}', minute='*', hour=hr)
                        scheduler.add_job(worker.job, cron, id=job_base + f'_{hr}')
                else:
                    scheduler.add_job(worker.job, 'interval', seconds=sec, id=job_base)
            else:  # CronTriggerConfig
                cron_args = {
                    k: v
                    for k, v in trig.dict().items()
                    if k != 'type' and v is not None
                }
                cron = CronTrigger(**cron_args)
                scheduler.add_job(worker.job, cron, id=job_base)

        # nightly flush at 00:00
        flush_cron = CronTrigger(hour='0', minute='0', second='0')
        scheduler.add_job(worker.flush, flush_cron, id=f'{worker.id}_flush')

    scheduler.start()
    return scheduler
