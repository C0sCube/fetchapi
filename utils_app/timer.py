import time
from contextlib import ContextDecorator

from utils.logger import info


class Timer(ContextDecorator):

    def __init__(self, name):

        self.name = name
        self.start = None
        self.end = None
        self.elapsed = None

    def __enter__(self):

        self.start = time.perf_counter()
        info(f"{self.name} started")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.end = time.perf_counter()
        self.elapsed = self.end - self.start

        info(
            f"{self.name} completed in "
            f"{self.elapsed:.2f} sec"
        )

        return False


class Stopwatch:

    def __init__(self):

        self.start = time.perf_counter()

    def elapsed(self):

        return time.perf_counter() - self.start

    def reset(self):

        self.start = time.perf_counter()