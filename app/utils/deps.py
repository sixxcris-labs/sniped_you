from __future__ import annotations
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(slots=True)
class DependencyStatus:
    """Simple value object describing a dependency health check."""

    name: str
    ok: bool
    message: str
    details: Dict[str, str] | None = None


def resolve_tesseract_cmd() -> Optional[str]:
    """
    Locate the Tesseract executable.

    Precedence order:
    1. `TESSERACT_CMD` environment variable (if it points to an existing file)
    2. `PATH` lookup via `shutil.which`
    3. Common install paths on each platform
    """

    env_path = os.getenv("TESSERACT_CMD")
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return str(candidate)

    exe_name = "tesseract.exe" if os.name == "nt" else "tesseract"
    which_result = shutil.which(exe_name)
    if which_result:
        return which_result

    if os.name == "nt":
        fallback_paths = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]
    else:
        fallback_paths = [
            Path("/usr/bin/tesseract"),
            Path("/usr/local/bin/tesseract"),
        ]

    for candidate in fallback_paths:
        if candidate.is_file():
            return str(candidate)

    return None


def check_tesseract() -> DependencyStatus:
    """Return a status object describing whether Tesseract can be executed."""

    cmd = resolve_tesseract_cmd()
    if not cmd:
        return DependencyStatus(
            name="tesseract",
            ok=False,
            message="Tesseract executable not found. Install it or set TESSERACT_CMD.",
            details={
                "platform": platform.platform(),
                "hint": "https://github.com/tesseract-ocr/tesseract#installing-tesseract",
            },
        )

    try:
        result = subprocess.run(
            [cmd, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return DependencyStatus(
            name="tesseract",
            ok=False,
            message="Failed to execute Tesseract.",
            details={"error": str(exc), "cmd": cmd},
        )

    return DependencyStatus(
        name="tesseract",
        ok=True,
        message=f"Tesseract available: {result.stdout.splitlines()[0]}",
        details={"cmd": cmd},
    )


def check_playwright_launch() -> DependencyStatus:
    """
    Attempt to launch a headless Chromium browser via Playwright.

    This will fail fast if Playwright is missing or if browsers have not been
    installed, mirroring the runtime errors the scraper would encounter.
    """

    try:
        from playwright.sync_api import sync_playwright  # type: ignore import
    except ImportError as exc:  # pragma: no cover - import guard
        return DependencyStatus(
            name="playwright",
            ok=False,
            message="Playwright Python package is not installed.",
            details={"error": str(exc)},
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:
        return DependencyStatus(
            name="playwright",
            ok=False,
            message="Playwright failed to launch Chromium.",
            details={"error": str(exc)},
        )

    return DependencyStatus(
        name="playwright",
        ok=True,
        message="Playwright Chromium launch succeeded.",
        details=None,
    )


def status_to_line(status: DependencyStatus) -> str:
    """Render a one-line status summary suitable for CLI output."""

    emoji = "âœ…" if status.ok else "âŒ"
    return f"{emoji} {status.name}: {status.message}"
