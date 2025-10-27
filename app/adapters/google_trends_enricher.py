import json
import argparse
import os
from pathlib import Path
from app.adapters.google_trends_adapter import get_trend_score


def ensure_within_base(user_path: Path | str, base: Path) -> Path:
    """
    Safely resolve user_path and ensure it stays inside base.

    Rules:
    - If user_path is absolute: resolve it and require it's inside base.
    - If user_path is relative: reject if it contains parent (..) segments or
      any absolute anchors; otherwise join it to base and resolve.
    - Raises ValueError on any unsafe or invalid path.
    """
    # Normalize types
    path = Path(user_path) if not isinstance(user_path, Path) else user_path
    base = base.resolve(strict=False)

    # If absolute, resolve and ensure inside base
    if path.is_absolute():
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(base):
            raise ValueError(f"Unsafe absolute path (outside base): {resolved}")
        return resolved

    # At this point path is relative. Reject any parent traversal.
    # Example attack: '../../etc/passwd' -> parts contain '..'
    if any(part == ".." for part in path.parts):
        raise ValueError("Relative path contains parent traversal ('..') - rejected")

    # Reject paths that include an anchor in the middle (defense-in-depth)
    # e.g., path parts like ('some', 'C:\\something') -- unlikely, but check
    if any(Path(part).is_absolute() for part in path.parts):
        raise ValueError("Relative path contains an absolute anchor - rejected")

    # Safe to join (we joined only sanitized parts)
    candidate = base.joinpath(path)
    resolved = candidate.resolve(strict=False)

    if not resolved.is_relative_to(base):
        raise ValueError(f"Resolved path escapes base: {resolved}")

    return resolved


def enrich_listings(input_path: Path, output_path: Path):
    """Append Google Trends demand_factor to parsed listings."""
    data = json.loads(input_path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "items" in data:
        items = data["items"]
    else:
        print(f"[warn] Unexpected JSON structure in {input_path}")
        return

    for item in items:
        keyword = item.get("model") or item.get("title") or ""
        try:
            item["demand_factor"] = get_trend_score(keyword)
        except Exception as e:
            print(f"[warn] {keyword}: {e}")
            item["demand_factor"] = 0.0

    output_data = {"items": items} if isinstance(data, dict) else items
    output_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"[done] wrote enriched file → {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", required=True, help="Path to input JSON (must be inside base)"
    )
    parser.add_argument(
        "--output", required=True, help="Path for output JSON (must be inside base)"
    )
    parser.add_argument(
        "--base-dir",
        required=False,
        default=os.getcwd(),
        help="Base directory confinement (defaults to CWD).",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    try:
        safe_input = ensure_within_base(Path(args.input), base_dir)
        safe_output = ensure_within_base(Path(args.output), base_dir)
    except ValueError as e:
        print(f"[error] {e}")
        raise SystemExit(2)

    if not safe_input.exists() or not safe_input.is_file():
        print(f"[error] input file missing or invalid: {safe_input}")
        raise SystemExit(3)

    out_parent = safe_output.parent
    if not out_parent.exists():
        if str(out_parent).startswith(str(base_dir.resolve())):
            out_parent.mkdir(parents=True, exist_ok=True)
        else:
            print(f"[error] output parent outside base: {out_parent}")
            raise SystemExit(4)

    enrich_listings(safe_input, safe_output)
