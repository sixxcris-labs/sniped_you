from __future__ import annotations
import time
from typing import Dict

class Metrics:
    """Simple runtime and counter metrics tracker."""

    def __init__(self) -> None:
        self.timers: Dict[str, float] = {}
        self.durations: Dict[str, float] = {}
        self.counters: Dict[str, int] = {}

    # ------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------
    def start_timer(self, name: str) -> None:
        self.timers[name] = time.perf_counter()

    def stop_timer(self, name: str) -> None:
        if name in self.timers:
            self.durations[name] = time.perf_counter() - self.timers.pop(name)

    def get_duration(self, name: str) -> float:
        return self.durations.get(name, 0.0)

    # ------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------
    def inc(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def get_count(self, name: str) -> int:
        return self.counters.get(name, 0)

    # ------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------
    def report(self) -> None:
        print("\n--- Metrics Report ---")
        for name, dur in self.durations.items():
            print(f"{name:20} {dur:8.2f}s")
        for name, count in self.counters.items():
            print(f"{name:20} {count:8d}")
        print("----------------------\n")
