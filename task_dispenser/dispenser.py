import subprocess as sp
from contextlib import _GeneratorContextManager
from typing import Any, Callable, cast, reveal_type, Generator
from types import TracebackType
import multiprocessing as mp
import time
import json
import redis
import logging

logger = logging.getLogger(__file__)

from .utils import (
    start_redis, noop_ctx, raise_error, ErrorWrapper, ErrorHandler, get_error_handler, TaskFailed,
)


def get_delay(
        flush_interval: float, next_flush_times: dict[str, float | None], max_llen: int, now: float | None = None
        ) -> tuple[float | None, float]:

    if now is None:
        now = time.time()

    if max_llen == 0:
        return None, now

    next_flush_time = min(
        (next_flush_time for next_flush_time in next_flush_times.values() if next_flush_time is not None),
        default=None)

    if next_flush_time is None:
        return None, now

    delay = next_flush_time - now

    assert delay >= 0, (delay, flush_interval, next_flush_times, max_llen, now)
    return delay, now


def rpopn(r: redis.Redis, n: int, qname: str) -> Any:  # type: ignore
    """pop n items from redis list queue"""

    with r.pipeline(transaction=True) as pipe:
        items, status = (
            pipe
            .lrange(qname, -n, -1)
            .ltrim(qname, 0, -n -1)
            .execute()
        )

        assert status
    return items

Task = Callable[[Any], Any]
Tasks = dict[str, Task]

class Dispenser:
    """
    Dispenser.

    :param tasks: Dictionary of tasks. `"queue_name": task_handler`
    :param batch_size: Number of accumulated tasks groupped before `task_handler` called forcefully
    :param flush_interval: Maximum interval in seconds between `task_handler` called
    :param host: redis host
    :param port: redis port
    :param password: redis password
    :param redis_start: start redis server on beckground if `True`
    :param procs_number: Spawn workers pool for tasks functions if procs_number > 0 else use main loop process.
    :param on_error: handler for errors occured during task execution
    """
    def __init__(
            self, tasks: Tasks, batch_size: int, flush_interval: float,
            host: str = '127.0.0.1', port: int = 6379, password: str | None = None,
            redis_start: bool = False, procs_number: int = 0, on_error: ErrorHandler | str | None = None):

        self.tasks = {key: ErrorWrapper(key, task) for key, task in tasks.items()}
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.host = host
        self.port = port
        self.password = password
        self.redis_start = redis_start
        self.procs_number = procs_number
        self.on_error = cast(
            Callable[[BaseException], None] | None,
            get_error_handler(on_error) if isinstance(on_error, str) else on_error)

        self._redis_ctx: _GeneratorContextManager[sp.Popen[Any] | None] | None = None
        self._redis: sp.Popen[Any] | None = None
        self._pool_ctx: mp.pool.Pool | None = None
        self._pool: mp.pool.Pool | None = None

    def setup(self, host: str | None = None, port: int | None = None) -> None:
        """
        Initialize connecion to redis.

        :param host: redis host
        :param port: redis port
        """

        r = redis.Redis(host=host or self.host, port=port or self.port, decode_responses=True, password=self.password)
        p = r.pubsub()

        # https://redis.io/docs/manual/keyspace-notifications/
        logger.info('Set redis: notify-keyspace-events=Kl')
        r.config_set('notify-keyspace-events', 'Kl')

        qnames = sorted(self.tasks.keys())
        subscribe = [f"__keyspace@0__:{qname}" for qname in qnames]
        p.psubscribe(subscribe)  # type: ignore
        logger.info('Subscribe to redis events: %s', str(subscribe))
        self.r = r
        self.p = p

    def apply_task(self, task: Task, batch: list[Any]) -> None:
        """
        Execute tasks batch.

        :param task: task executor
        :param batch: list of accumulated arguments
        """

        if self._pool is None:
            try:
                task(batch)
            except KeyboardInterrupt:
                raise
            except TaskFailed as e:
                if self.on_error is not None:
                    self.on_error(e)
        else:
            self._pool.apply_async(task, args=(batch,), error_callback=self.on_error)

    def __enter__(self) -> 'Dispenser':
        assert self._redis_ctx is None, self._redis_ctx
        assert self._redis is None, self._redis
        assert self._pool_ctx is None, self._pool_ctx
        assert self._pool is None, self._pool

        self._redis_ctx = (start_redis(port=self.port, password=self.password) if self.redis_start else noop_ctx())
        self._redis = self._redis_ctx.__enter__()

        if self.procs_number > 0:
            self._pool_ctx = mp.Pool(self.procs_number)
            self._pool = self._pool_ctx.__enter__()
            logger.info('Workers pool created: procs_number=%d', self.procs_number)

        self.setup()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        if self._redis_ctx is not None:
            self._redis_ctx.__exit__(exc_type, exc_val, exc_tb)

    def run(self) -> None:
        '''
        Start executor.
        '''

        llens: dict[str, int] = {qname: self.r.llen(qname) for qname in self.tasks.keys()}
        logger.info('Queues state: %s', str(llens))
        next_flush_times = {qname: None if llens[qname] == 0 else time.time() + self.flush_interval for qname in self.tasks.keys()}

        logger.info('Starting message loop')
        while True:
            delay, now = get_delay(self.flush_interval, next_flush_times, max(llens.values()))
            logger.debug('Wait delay %s', str(delay))

            if (delay is None or delay > 0) and max(llens.values()) < self.batch_size:
                message = self.p.get_message(timeout=delay)  # type: ignore
                if message is None:
                    logger.debug('Check by timeout')
                elif message['data'] != 'lpush':
                    logger.debug('Skip message by type: %s', str(message))
                    continue
                else:
                    _, cur_qname = message['channel'].split(':', 1)
                    llens[cur_qname] += 1
                    if llens[cur_qname] == 1:
                        next_flush_times[cur_qname] = time.time() + self.flush_interval

            for qname, llen in llens.items():
                now = time.time()
                if llen == 0:
                    logger.debug('Nothing to do. Empty queue: %s', qname)
                    continue

                is_timeout = False
                if (
                        llen >= self.batch_size
                        or (is_timeout := (next_flush_times[qname] is not None and now > cast(float, next_flush_times[qname])))
                    ):
                    cur_pop = min(llen, self.batch_size)
                    items = rpopn(self.r, cur_pop, qname)
                    argss = [json.loads(item) for item in items]

                    logger.debug('Apply task: %s', json.dumps({
                        'qname': qname,
                        'llen': llen, 'grouped': len(argss),
                        'reason': 'timeout' if is_timeout else 'batch_size',
                        'llens': llens, 'cur_pop': cur_pop,
                    }, sort_keys=True, ensure_ascii=False))
                    self.apply_task(self.tasks[qname], argss)

                    llens[qname] = llen - cur_pop

                    assert llens[qname] >= 0

                    if 0 < llens[qname] < self.batch_size:
                        next_flush_times[qname] = time.time() + self.flush_interval
                    else:
                        next_flush_times[qname] = None

                else:
                    logger.debug('Accumulate batch. Queue: %s', qname)

