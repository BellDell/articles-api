import time
from collections import defaultdict, deque
from typing import DefaultDict, Deque


class RateLimiter:
    def __init__(self) -> None:
        self.buffer = []
        self.max_requests: int
        self.time_window: time.time
        self._requests: DefaultDict[object, Deque[float]] = defaultdict(deque)

    def add_new_record(self, ip_address):
        self.buffer.append(
            {
                ip_address: {
                    "time":  time.time
                }
             }
        )

    def get_records(self):
        return self.buffer


if __name__ == "__main__":
    rl = RateLimiter()
    address = ["123", "1234", "1254", "1232", "4231"]
    for i in address:
        rl.add_new_record(i)

    print(rl.get_records())
