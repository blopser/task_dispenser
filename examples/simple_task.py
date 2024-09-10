from typing import Any
import logging

logger = logging.getLogger()


def task_func(*batch: Any) -> None:
    logger.info('Process args %d', len(batch))
