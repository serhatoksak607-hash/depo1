import os

from redis import Redis
from rq import Connection, Queue, Worker


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_NAME = os.getenv("RQ_QUEUE", "upload_processing")


def main() -> None:
    redis_conn = Redis.from_url(REDIS_URL)
    with Connection(redis_conn):
        worker = Worker([Queue(QUEUE_NAME)])
        worker.work()


if __name__ == "__main__":
    main()
