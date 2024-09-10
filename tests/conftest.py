import json
from typing import Generator, Any
import contextlib
import redis
import pytest

from task_dispenser.utils import start_redis

GLOBAL_REDIS_CLIENT = 16379


@contextlib.contextmanager
def get_redis(port: int) -> Generator[redis.Redis, None, None]:  # type: ignore
    with start_redis(port=port, extra_args=['--save', "", '--appendonly', 'no']) as r_proc, redis.Redis(host='localhost', port=port) as r:
        yield r

def get_redis_results(r: redis.Redis, qname: str) -> list[Any]:  # type: ignore
    n = r.llen(qname)
    with r.pipeline(transaction=True) as pipe:
        items, status = (
            pipe
            .lrange(qname, -n, -1)
            .ltrim(qname, 0, -n -1)
            .execute()
        )

    assert items is not None
    return [json.loads(res.decode('utf8')) for res in items][::-1]

@contextlib.contextmanager
def get_global_redis_client() -> Generator[redis.Redis, None, None]:  # type: ignore
    with redis.Redis(host='localhost', port=GLOBAL_REDIS_CLIENT) as r:
        yield r


@pytest.fixture(scope='session')
def global_redis() -> Generator[redis.Redis, None, None]:  # type: ignore
    with get_redis(GLOBAL_REDIS_CLIENT) as r:
        yield r
