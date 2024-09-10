import json
import time
import argparse
import logging

from task_dispenser import Dispenser, DispenserClient
from task_dispenser.utils import import_by_name, start_redis, noop_ctx, get_error_handler


logger = logging.getLogger(__file__)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('-H', '--redis-host', default='127.0.0.1', help='Redis host.')
    parser.add_argument('-P', '--redis-port', default=6379, type=int, help='Redis port.')
    parser.add_argument('-p', '--redis-pass', default=None, help='Redis password if authentication is activated.')
    parser.add_argument('-l', '--log-level', type=lambda x: logging.getLevelName(x.upper()), default='info', help='Log level.')
    parser.add_argument('-f', '--log-file', type=str, help='Path to log file. Stdout by default.')
    parser.add_argument(
        '-F', '--log-format',
        type=str, default='[%(asctime)s %(levelname)s %(filename)s:%(lineno)d]: %(message)s',
        help='Log format.')


def args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(required=True)

    parser_start = subparsers.add_parser('start', help='Start task dispenser server')
    parser_start.set_defaults(func=start)
    parser_start.add_argument(
        '-t', '--task', nargs=2, action='append',
        help=(
            'Pairs of queue name and task handler. Task handler loaded by `task_dispenser.utils.import_by_name`. So'
            ' it can be builtin function, function in module in form `module.other:func` or path to function in file: `path/file.py:func`.'
            ' Example: -t q1 print -t q2 print'
        ),
        dest='tasks', required=True)
    parser_start.add_argument('-b', '--batch-size', default=20, type=int, help='Number of accumulated tasks groupped before `task_handler` called forcefully')
    parser_start.add_argument('-i', '--flush-interval', default=5, type=float, help='Maximum interval in seconds between `task_handler` called')
    parser_start.add_argument(
        '-n', '--procs-number', default=1, type=int,
        help='Spawn workers pool for tasks functions if procs_number > 0 else use main loop process')
    parser_start.add_argument('-e', '--on-error', default='fail', choices=['fail', 'log'], help='Pandler for errors occured during task execution')
    parser_start.add_argument('-S', '--redis-start', default=False, action='store_true', help='Start redis server in subprocess or not.')
    parser_start.add_argument('-D', '--redis-datadir', default='/tmp/redis', help='If start redis server then you can specify path to redis data to be saved.')
    add_common_args(parser_start)

    parser_add = subparsers.add_parser('add', help='Add task from cli client.')
    parser_add.set_defaults(func=add)
    parser_add.add_argument(
        '-t', '--task', nargs=2, action='append',
        help='Example: -t q1 1 -t q2 2', dest='tasks', required=True)
    parser_add.add_argument('-n', '--num', default=1, type=int)
    add_common_args(parser_add)
    return parser


def parse_args() -> argparse.Namespace:
    return args_parser().parse_args()


def start(args: argparse.Namespace) -> None:
    tasks = {qname: import_by_name(taskname) for qname, taskname in args.tasks}

    dispenser = Dispenser(
        tasks,
        batch_size=args.batch_size,
        flush_interval=args.flush_interval,
        host=args.redis_host,
        port=args.redis_port,
        password=args.redis_pass,
        redis_start=args.redis_start,
        procs_number=args.procs_number,
        on_error=args.on_error,
    )

    with dispenser:
        dispenser.run()


def add(args: argparse.Namespace) -> None:
    client = DispenserClient(host=args.redis_host, port=args.redis_port, password=args.redis_pass)
    client.setup()

    for n in range(args.num):
        for qname, task_args in args.tasks:
            client.add(qname, json.loads(task_args))


def main() -> None:
    args = parse_args()

    logging.basicConfig(filename=args.log_file, level=args.log_level, format=args.log_format)
    args.func(args)

if __name__ == '__main__':
    main()
