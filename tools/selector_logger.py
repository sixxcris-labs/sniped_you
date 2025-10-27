import datetime
import subprocess
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"selector_report_{datetime.date.today()}.log"


def run_selector_test():
    result = subprocess.run(
        ["python", "tools/test_selectors.py"], capture_output=True, text=True
    )
    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(f"\n=== Run @ {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===\n")
        log.write(result.stdout)
        log.write("\n" + "=" * 80 + "\n")

    print(f"[logger] Selector test logged to {LOG_FILE}")


if __name__ == "__main__":
    run_selector_test()
