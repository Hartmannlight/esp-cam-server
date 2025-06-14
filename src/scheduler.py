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
                    sh, sm = map(int, trig.start_time.split(':'))
                    eh, em = map(int, trig.end_time.split(':'))
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
                    scheduler.add_job(
                        worker.flush,
                        CronTrigger(hour=str(eh), minute=str(em), second='0'),
                        id=f'{job_base}_end_flush',
                    )
                else:
                    scheduler.add_job(worker.job, 'interval', seconds=sec, id=job_base)
            else:
                cron_args = {
                    k: v for k, v in trig.dict().items()
                    if k != 'type' and v is not None
                }
                cron = CronTrigger(**cron_args)
                scheduler.add_job(worker.job, cron, id=job_base)

        flush_cron = CronTrigger(hour='0', minute='0', second='0')
        scheduler.add_job(worker.flush, flush_cron, id=f'{worker.id}_flush')

        if worker.notifier:
            interval_sec = next(
                (t.seconds for t in worker.triggers
                 if isinstance(t, IntervalTriggerConfig)),
                60,
            )
            scheduler.add_job(
                worker.heartbeat,
                'interval',
                seconds=interval_sec,
                id=f'{worker.id}_heartbeat',
            )

    scheduler.start()
    return scheduler
