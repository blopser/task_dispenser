from typing import Any
import json
import redis


class DispenserClient:
    """
    Dispenser client.

    :param host: redis host
    :param port: redis port
    :param password: redis password
    :param setup: call setup in initialization and connect to redis
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 6379, password: str | None = None, setup: bool = True) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.r: redis.Redis[str] | None = None

        if setup:
            self.setup()

    def setup(self) -> None:
        """
        Initialize connecion to redis.
        """
        self.r = redis.Redis(host=self.host, port=self.port, decode_responses=True, password=self.password)

    def add(self, qname: str, args: Any) -> Any:
        """
        Add task to queue.

        :param qname: queue name
        :param args: task arguments
        """
        assert self.r is not None, 'Redis not connected. Call client.setip()'
        return self.r.lpush(qname, json.dumps(args, sort_keys=True, ensure_ascii=False))
