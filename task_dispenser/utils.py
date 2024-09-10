from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, Generic, Generator
import traceback
import sys
import os
import logging
import time
import subprocess as sp
import contextlib
import importlib


logger = logging.getLogger()


class TaskDispenserBaseError(Exception):
    pass


P = ParamSpec('P')
T = TypeVar('T')


class TaskFailed(TaskDispenserBaseError):
    def __init__(self, original: Exception, queue: str, func: Callable[P, T]) -> None:
        self.original = original
        self.tb = ''.join(traceback.format_exception(self.original))
        self.queue = queue
        self.func = func

    def __str__(self) -> str:
        return f'{repr(self.original)}'

    def get_traceback(self) -> str:
        return self.tb


class ErrorWrapper(Generic[T]):
    def __init__(self, queue: str, func: Callable[P, T]) -> None:
        self.queue = queue
        self.func = func

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return self.func(*args, **kwargs)  # type: ignore
        except Exception as e:
            raise TaskFailed(e, self.queue, self.func) from e


def import_by_name(name: str) -> Any:
    '''
    Import object by name.

    >>> import_by_name('print')
    <built-in function print>

    >>> import_by_name('itertools:product')
    <class 'itertools.product'>

    >>> import_by_name('collections:Counter')
    <class 'collections.Counter'>

    >>> import collections
    >>> most_common = import_by_name('collections:Counter.most_common')
    >>> assert collections.Counter.most_common is most_common

    >>> import_by_name('task_dispenser/utils.py:import_by_name').__name__
    'import_by_name'
    '''
    if ':' not in name:
        name = f'builtins:{name}'

    module_path, key = name.split(':', 1)
    attrs = key.split('.')
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        spec = importlib.util.spec_from_file_location(
            os.path.splitext(os.path.basename(module_path))[0], module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        sys.path.append(os.path.dirname(module_path))
        module = importlib.import_module(os.path.splitext(os.path.basename(module_path))[0])

    res = module
    for attr in attrs:
        res = getattr(res, attr)
    return res


@contextlib.contextmanager
def noop_ctx(*args: Any, **kwargs: Any) -> Generator[None, None, None]:
    yield


@contextlib.contextmanager
def start_redis(
        port: int = 6379, password: str | None = None, delay: float = 0.01, datadir: str | Path = '/tmp/redis',
        extra_args: list[str] | None = None,
        ) -> Generator[sp.Popen[Any], None, None]:

    logger.info('Start redis: localhost:%d', port)
    os.makedirs(datadir, exist_ok=True)

    cmd_args = [
        'redis-server', '--port', str(port), "--loglevel",  "warning",
        "--save", "20", "1", '--dir', datadir]
    if extra_args:
        cmd_args.extend(extra_args)
    ping_args = ['redis-cli', "-p", str(port), 'ping']
    if password is not None:
        cmd_args.extend(['--requirepass', password])
        ping_args = ['redis-cli', '-a', password, "-p", str(port), 'ping']

    with sp.Popen(cmd_args, stdout=sp.PIPE, stderr=sp.PIPE) as proc:
        ping_out = None
        while proc.poll() is None:
            if delay:
                time.sleep(delay)

            ping_proc = sp.Popen(ping_args, stdout=sp.PIPE, stderr=sp.PIPE)
            ping_out, ping_err = ping_proc.communicate()
            ping_out = ping_out.strip()

            if ping_out == b'PONG':
                break

            logger.debug((ping_out or ping_err).decode('utf8').strip())

        if ping_out == b'PONG':
            logger.debug('Redis server initialized successfully')
        else:
            proc_out, proc_err = proc.communicate()
            err = (proc_out or proc_err).decode('utf8').strip()
            logging.error(err)
            raise RuntimeError('Can\'t start redis server')

        try:
            yield proc
        finally:
            proc.terminate()


def failed_task(*args: Any, **kwargs: Any) -> None:
    raise ValueError('Failed')


def raise_error(e: Exception) -> None:
    raise e


def log_error(e: TaskFailed) -> None:
    logger.error(
        'Error while executing task %s:%s\n%s',
        e.queue, e.func.__name__, e.get_traceback())


ErrorHandler = Callable[[TaskFailed], None]

def get_error_handler(policy: str) -> ErrorHandler:
    return {'fail': raise_error, 'log': log_error}[policy]

