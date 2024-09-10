import pytest
import redis
from typing import Generator, Any
import time
import multiprocessing as mp
import sys
import shlex
from task_dispenser.main import main
from task_dispenser.utils import start_redis
import contextlib
import json

from conftest import get_global_redis_client, get_redis_results


@contextlib.contextmanager
def patch_args(args: str | list[Any]) -> Generator[None, None, None]:
    if isinstance(args, str):
        args = shlex.split(args.replace('\n', ' '))
    args = list(map(str, args))

    cur_args = sys.argv
    try:
        sys.argv = args
        yield
    finally:
        sys.argv = cur_args


def log_to_redis(tasks: list[Any]) -> None:
    i = tasks[0]
    with get_global_redis_client() as r:
        assert r.lpush(str(i), json.dumps(tasks))


@contextlib.contextmanager
def start_dispenser(server_args: str | list[str], wait_start: int = 1) -> Generator[None, None, None]:
    with patch_args(server_args):
        p = mp.Process(target=main)
        p.start()
        time.sleep(wait_start)

        try:
            yield
        finally:
            p.terminate()
            p.join()

DISPENSER_DEFAULT_ARGS = '''task-dispenser start
        -t q1 tests/test_main.py:log_to_redis
        -t q2 tests/test_main.py:log_to_redis
        --redis-start --procs-number 0 --on-error=log --batch-size=3 --log-level=debug\n'''

@pytest.mark.parametrize('batch_size, flush_interval, n, wait_after', [
    (2, 100, 10, 1),
    (100, 1, 10, 2),
    (4, 1, 10, 2),
])
def test_main(batch_size: int, flush_interval: int, n: int, wait_after: int, global_redis: redis.Redis) -> None:  # type: ignore
    key = 't'
    server_args = DISPENSER_DEFAULT_ARGS + f'--batch-size {batch_size} --flush-interval {flush_interval}'
    add_args = f'''task-dispenser add -t q1 '"{key}"' --log-level=debug -n {n}'''

    with start_dispenser(server_args):
        with patch_args(add_args):
            main()
        time.sleep(wait_after)

    assert get_redis_results(global_redis, key) == (
        [[key] * batch_size] * (n // batch_size) + (([[key] * (n % batch_size)] if n % batch_size != 0 else []))
    )

@pytest.mark.parametrize('procs', [0, 1, 2])
def test_procs_number(procs: int, global_redis: redis.Redis) -> None:  # type: ignore
    key = 't'
    server_args = DISPENSER_DEFAULT_ARGS + f'--batch-size 2 --flush-interval 1 --procs-number {procs}'
    add_args = f'''task-dispenser add -t q1 '"{key}"' --log-level=debug -n 10'''

    with start_dispenser(server_args):
        with patch_args(add_args):
            main()
        time.sleep(1)

    assert get_redis_results(global_redis, key) == [[key] * 2] * 5


def test_auth(global_redis: redis.Redis) -> None:  # type: ignore
    key = 't'
    server_args = DISPENSER_DEFAULT_ARGS + f'--batch-size 2 --flush-interval 1 --redis-pass p'

    with start_dispenser(server_args):
        add_args = f'''task-dispenser add -t q1 '"{key}"' --log-level=debug -n 10 --redis-pass p'''
        with patch_args(add_args):
            main()
        time.sleep(1)
        assert get_redis_results(global_redis, key) == [[key] * 2] * 5

        add_args = f'''task-dispenser add -t q1 '"{key}"' --log-level=debug -n 10'''
        with pytest.raises(redis.exceptions.AuthenticationError):
            with patch_args(add_args):
                main()
        time.sleep(1)
        assert get_redis_results(global_redis, key) == []

        add_args = f'''task-dispenser add -t q1 '"{key}"' --log-level=debug -n 10 --redis-pass wrong'''
        with pytest.raises(redis.exceptions.AuthenticationError):
            with patch_args(add_args):
                main()
        time.sleep(1)
        assert get_redis_results(global_redis, key) == []
