import argparse
import json
import sys
import os
import time
import warnings
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, List, Optional, Sequence, Tuple

# Curb noisy logging before libraries initialise.
os.environ.setdefault("PADDLE_LOG_LEVEL", "ERROR")
os.environ.setdefault("FLAGS_logtostderr", "0")
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import easyocr
except ImportError as exc:  # pragma: no cover - hard failure
    raise SystemExit("easyocr must be installed in the active environment") from exc

try:
    from paddleocr import PaddleOCR
except ImportError as exc:  # pragma: no cover - hard failure
    raise SystemExit("paddleocr must be installed in the active environment") from exc

DEFAULT_LIMIT = 10
DEFAULT_TIMEOUT = 10.0
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE_DIR = PROJECT_ROOT / "data" / "screenshots"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "benchmark_results.json"


@dataclass
class BenchmarkResult:
    image: str
    easyocr_conf: Optional[float]
    paddle_conf: Optional[float]
    easyocr_time: Optional[float]
    paddle_time: Optional[float]

    def to_payload(self, conf_precision: int = 3, time_precision: int = 2) -> dict:
        return {
            "image": self.image,
            "easyocr_conf": (
                round(self.easyocr_conf, conf_precision)
                if self.easyocr_conf is not None
                else None
            ),
            "paddle_conf": (
                round(self.paddle_conf, conf_precision)
                if self.paddle_conf is not None
                else None
            ),
            "easyocr_time": (
                round(self.easyocr_time, time_precision)
                if self.easyocr_time is not None
                else None
            ),
            "paddle_time": (
                round(self.paddle_time, time_precision)
                if self.paddle_time is not None
                else None
            ),
        }


@dataclass
class BenchmarkSettings:
    image_dir: Path
    output_path: Path
    limit: Optional[int]
    timeout: float
    recursive: bool
    pattern: Optional[str]
    engines: Sequence[str]
    allow_slow: bool
    quiet: bool
    show_skipped: bool


@contextmanager
def suppress_output() -> Iterable[None]:
    """Temporarily silence stdout/stderr at the Python and OS level."""
    try:
        stdout_fd = sys.stdout.fileno()
        stderr_fd = sys.stderr.fileno()
    except (AttributeError, OSError):
        with open(os.devnull, "w") as devnull:
            with redirect_stdout(devnull), redirect_stderr(devnull):
                yield
        return

    with open(os.devnull, "w") as devnull:
        stdout_dup = os.dup(stdout_fd)
        stderr_dup = os.dup(stderr_fd)
        try:
            os.dup2(devnull.fileno(), stdout_fd)
            os.dup2(devnull.fileno(), stderr_fd)
            with redirect_stdout(devnull), redirect_stderr(devnull):
                yield
        finally:
            os.dup2(stdout_dup, stdout_fd)
            os.dup2(stderr_dup, stderr_fd)
            os.close(stdout_dup)
            os.close(stderr_dup)


def parse_args(argv: Optional[Sequence[str]] = None) -> BenchmarkSettings:
    parser = argparse.ArgumentParser(description="Benchmark EasyOCR vs PaddleOCR.")
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=DEFAULT_IMAGE_DIR,
        help="Directory containing screenshots.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Glob pattern to filter images (applied to filenames).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search image directory recursively.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of images to process (<=0 means no limit).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Maximum allowed runtime per image; slower images are skipped.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination JSON file for benchmark data.",
    )
    parser.add_argument(
        "--engines",
        nargs="+",
        choices=("easyocr", "paddleocr"),
        default=("easyocr", "paddleocr"),
        help="Select which OCR engines to benchmark.",
    )
    parser.add_argument(
        "--allow-slow",
        action="store_true",
        help="Keep results even if runtime exceeds the timeout threshold.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console summary (still writes JSON).",
    )
    parser.add_argument(
        "--show-skipped",
        action="store_true",
        help="Print reasons for skipped images.",
    )

    args = parser.parse_args(argv)
    limit = args.limit if args.limit > 0 else None
    engines = tuple(dict.fromkeys(args.engines))  # Deduplicate while preserving order.

    return BenchmarkSettings(
        image_dir=args.image_dir,
        output_path=args.output,
        limit=limit,
        timeout=args.timeout,
        recursive=args.recursive,
        pattern=args.pattern,
        engines=engines,
        allow_slow=args.allow_slow,
        quiet=args.quiet,
        show_skipped=args.show_skipped,
    )


def collect_images(
    directory: Path, recursive: bool, pattern: Optional[str], limit: Optional[int]
) -> List[Path]:
    exts = {".png", ".jpg", ".jpeg"}

    if not directory.is_dir():
        return []

    if pattern:
        iterator = directory.rglob(pattern) if recursive else directory.glob(pattern)
        files = [
            path for path in iterator if path.is_file() and path.suffix.lower() in exts
        ]
    else:
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        files = [
            path for path in iterator if path.is_file() and path.suffix.lower() in exts
        ]

    files.sort()
    return files[:limit] if limit is not None else files


def average(values: Iterable[float]) -> float:
    collected = list(values)
    return float(mean(collected)) if collected else 0.0


def build_readers(
    engines: Sequence[str],
) -> Tuple[Optional[easyocr.Reader], Optional[PaddleOCR]]:
    easy_reader: Optional[easyocr.Reader] = None
    paddle_reader: Optional[PaddleOCR] = None

    with suppress_output():
        if "easyocr" in engines:
            easy_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        if "paddleocr" in engines:
            paddle_reader = PaddleOCR(lang="en")

    return easy_reader, paddle_reader


def run_easyocr(reader: easyocr.Reader, image_path: Path) -> Tuple[float, float]:
    start = time.perf_counter()
    with suppress_output():
        results = reader.readtext(str(image_path))
    elapsed = time.perf_counter() - start
    confidences = [float(item[2]) for item in results if len(item) >= 3]
    return average(confidences), elapsed


def run_paddleocr(reader: PaddleOCR, image_path: Path) -> Tuple[float, float]:
    start = time.perf_counter()
    with suppress_output():
        results = reader.predict([str(image_path)])
    elapsed = time.perf_counter() - start

    confidences: List[float] = []
    for page in results:
        if isinstance(page, dict):
            scores = page.get("rec_scores") or []
            confidences.extend(float(score) for score in scores if score is not None)
        elif isinstance(page, (list, tuple)):
            for entry in page:
                if isinstance(entry, (list, tuple)) and len(entry) > 1:
                    value = entry[1]
                    if isinstance(value, (list, tuple)) and len(value) >= 2:
                        confidences.append(float(value[1]))

    return average(confidences), elapsed


def to_summary_line(
    label: str, conf: Optional[float], runtime: Optional[float]
) -> Optional[str]:
    if conf is None or runtime is None:
        return None
    return f"{label} -> {conf:.3f} avg conf | {runtime:.2f}s avg runtime"


def summarise(
    results: Sequence[BenchmarkResult], engines: Sequence[str], output_path: Path
) -> str:
    lines = ["--- Benchmark Summary ---"]

    if "easyocr" in engines:
        easy_conf = average(
            res.easyocr_conf for res in results if res.easyocr_conf is not None
        )
        easy_time = average(
            res.easyocr_time for res in results if res.easyocr_time is not None
        )
        line = to_summary_line("EasyOCR", easy_conf, easy_time)
        if line:
            lines.append(line)

    if "paddleocr" in engines:
        paddle_conf = average(
            res.paddle_conf for res in results if res.paddle_conf is not None
        )
        paddle_time = average(
            res.paddle_time for res in results if res.paddle_time is not None
        )
        line = to_summary_line("PaddleOCR", paddle_conf, paddle_time)
        if line:
            lines.append(line)

    relative: Path | str = output_path
    try:
        relative = output_path.relative_to(PROJECT_ROOT)
    except ValueError:
        pass
    if isinstance(relative, Path):
        relative = relative.as_posix()
    lines.append(f"Results saved -> {relative}")
    return "\n".join(lines)


def persist_results(results: Sequence[BenchmarkResult], output_path: Path) -> None:
    payload = [item.to_payload() for item in results]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))


def process_image(
    image_path: Path,
    easy_reader: Optional[easyocr.Reader],
    paddle_reader: Optional[PaddleOCR],
    timeout: float,
    allow_slow: bool,
) -> Tuple[Optional[BenchmarkResult], Optional[str]]:
    easy_conf = easy_time = paddle_conf = paddle_time = None

    try:
        if easy_reader is not None:
            easy_conf, easy_time = run_easyocr(easy_reader, image_path)
        if paddle_reader is not None:
            paddle_conf, paddle_time = run_paddleocr(paddle_reader, image_path)
    except Exception as exc:  # pragma: no cover - best effort recovery
        return None, f"{image_path.name} (error: {exc})"

    timings = [value for value in (easy_time, paddle_time) if value is not None]
    if timings and not allow_slow and max(timings) > timeout:
        return None, f"{image_path.name} (> {timeout:.0f}s)"

    if easy_conf is None and paddle_conf is None:
        return None, f"{image_path.name} (no engines active)"

    result = BenchmarkResult(
        image=image_path.name,
        easyocr_conf=easy_conf,
        paddle_conf=paddle_conf,
        easyocr_time=easy_time,
        paddle_time=paddle_time,
    )
    return result, None


def main(argv: Optional[Sequence[str]] = None) -> int:
    settings = parse_args(argv)

    if not settings.image_dir.is_dir():
        print(f"Image directory not found -> {settings.image_dir}")
        return 1

    images = collect_images(
        settings.image_dir, settings.recursive, settings.pattern, settings.limit
    )
    if not images:
        print("No PNG/JPG images matched the provided criteria.")
        return 0

    easy_reader, paddle_reader = build_readers(settings.engines)
    results: List[BenchmarkResult] = []
    skipped: List[str] = []

    for image_path in images:
        record, reason = process_image(
            image_path,
            easy_reader,
            paddle_reader,
            settings.timeout,
            settings.allow_slow,
        )
        if record is not None:
            results.append(record)
        elif reason:
            skipped.append(reason)

    if not results:
        print("No benchmark data collected.")
        if skipped and settings.show_skipped:
            print("Skipped images -> " + ", ".join(skipped))
        return 0

    persist_results(results, settings.output_path)

    if not settings.quiet:
        print(summarise(results, settings.engines, settings.output_path))
        if skipped and settings.show_skipped:
            print("Skipped images -> " + ", ".join(skipped))

    return 0


if __name__ == "__main__":
    sys.exit(main())
