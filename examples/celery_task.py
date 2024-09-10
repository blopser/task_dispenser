from typing import Any
import logging
from celery import Celery

logger = logging.getLogger()

app = Celery('hello', broker='redis://:@localhost:6379/0')


@app.task
def simple_celery_task_func(*batch: Any) -> None:
    print('c', batch)


@app.task
def celery_task_func(batch: list[Any]) -> None:
    print('c', batch)


def task_func(batch: list[Any]) -> None:
    print('batch', [batch])
    logger.info('Process args %d (%s)', len(batch), str(batch))
    celery_task_func.apply_async(args=(batch,))
