import os
import re
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional
from openai import OpenAI

# ------------------------------------------------------------
# Environment Setup
# ------------------------------------------------------------
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ------------------------------------------------------------
# Regex Helpers
# ------------------------------------------------------------
_price_s_as_dollar = re.compile(
    r"(?<!\w)[sS]\s?(?=\d{2,5}(?:[,\.\d])*\b)"
)  # S123 → $123
_inside_num_o = re.compile(r"(?<=\d)[oO](?=\d)")  # 7O0 → 700


# ------------------------------------------------------------
# Basic Utilities
# ------------------------------------------------------------
def basic_cleanup(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9$%.,:/()_+'\"&\[\]{}<>@!?=#\s-]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_title(text: str) -> str:
    t = basic_cleanup(text)
    t = _price_s_as_dollar.sub("$", t)
    t = _inside_num_o.sub("0", t)
    return t.strip()


# ------------------------------------------------------------
# Field Extraction
# ------------------------------------------------------------
def brand_fallback(fields: Dict[str, Any], text: str) -> Dict[str, Any]:
    if fields.get("brand"):
        return fields
    for b in [
        "Specialized",
        "Trek",
        "Giant",
        "Fuji",
        "Masi",
        "Ray-Ban",
        "Rayban",
        "Cannondale",
        "Triban",
        "Canyon",
        "Scott",
    ]:
        if b.lower() in text.lower():
            fields["brand"] = b
            break
    return fields


def extract_fields(text: str) -> Dict[str, Any]:
    """Extract brand, model, price, and category heuristically from OCR text."""
    clean = basic_cleanup(text)
    upper = clean.upper()
    fields = {"brand": None, "model": None, "price": None, "category": None}

    # ---------------- Brand Detection ----------------
    def detect_brand(upper_text: str) -> Optional[str]:
        brands = [
            "SPECIALIZED",
            "TREK",
            "GIANT",
            "RAYBAN",
            "RAY-BAN",
            "FUJI",
            "CANNONDALE",
            "MASI",
            "TRIBAN",
            "CANYON",
            "SCOTT",
        ]
        return next((b.title() for b in brands if b in upper_text), None)

    # ---------------- Price Helpers ------------------
    def normalize_price_text(upper_text: str) -> str:
        t = re.sub(r"[sS](?=\d)", "$", upper_text)
        return re.sub(r"\$\s*(\d{2,5})", r"$\1", t)

    def correct_common_price_errors(price: int, upper_text: str) -> int:
        """Fix typical OCR price misreads like 5450→450 or 5185→185."""
        if 5000 <= price <= 5999:
            price -= 5000
        elif price > 10000:
            price //= 10
        elif 1000 < price < 2000 and "S1," in upper_text:
            price = int(str(price)[1:])
        return price

    def detect_price(upper_text: str) -> Optional[int]:
        norm = normalize_price_text(upper_text)
        match = re.search(r"\$\s*(\d{2,5})", norm) or re.search(r"\b(\d{2,5})\b", norm)
        if not match:
            return None
        price = int(match.group(1))
        price = correct_common_price_errors(price, upper_text)
        return price if 10 <= price <= 10000 else None

    # ---------------- Category & Model ---------------
    def detect_category(upper_text: str) -> Optional[str]:
        categories = {
            "bike": any(word in upper_text for word in ("BIKE", "MTB")),
            "frame": "FRAME" in upper_text,
            "helmet": "HELMET" in upper_text,
            "other": "GLASS" in upper_text
            or ("META" in upper_text and "GLASS" in upper_text),
        }
        return next((cat for cat, cond in categories.items() if cond), None)

    def detect_model(brand: str, upper_text: str) -> Optional[str]:
        pattern = rf"{re.escape(brand.upper())}\s+([A-Z0-9][A-Z0-9 -]{{2,24}})"
        match = re.search(pattern, upper_text)
        return match.group(1).strip().title() if match else None

    # ---------------- Apply Detections ---------------
    brand = detect_brand(upper)
    price = detect_price(upper)
    category = detect_category(upper)
    model = detect_model(brand, upper) if brand else None

    fields.update(
        {"brand": brand, "model": model, "price": price, "category": category}
    )
    return brand_fallback(fields, clean)


# ------------------------------------------------------------
# Entry Parsing
# ------------------------------------------------------------
def heuristic_parse(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Safely parse one OCR entry."""
    text = entry.get("text", "")
    if not text or not isinstance(text, str):
        return {
            "brand": None,
            "model": None,
            "price": None,
            "category": None,
            "confidence": float(entry.get("confidence", 0.0)),
            "image": entry.get("image"),
            "timestamp": entry.get("timestamp"),
            "error": "missing_text",
        }

    fields = extract_fields(text)
    fields.update(
        {
            "confidence": float(entry.get("confidence", 0.0)),
            "image": entry.get("image"),
            "timestamp": entry.get("timestamp"),
        }
    )
    return fields


# ------------------------------------------------------------
# Listing Utilities
# ------------------------------------------------------------
def dedupe_listings(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, deduped = set(), []
    for x in listings:
        key = (x.get("brand"), x.get("price"), x.get("category"))
        if key not in seen:
            seen.add(key)
            deduped.append(x)
    return deduped


def score_listing(item: Dict[str, Any]) -> float:
    score = 0
    if item.get("price"):
        score += max(0, (1000 - item["price"]) / 1000)
    score += item.get("confidence", 0)
    return round(score, 2)


# ------------------------------------------------------------
# GPT Fallback
# ------------------------------------------------------------
def gpt_refine(client: OpenAI, text: str) -> Dict[str, Any]:
    prompt = (
        "Extract brand, model, price (number only), and category "
        "(bike, frame, helmet, other) from this text:\n"
        f"{text}\nRespond in JSON format with keys: brand, model, price, category."
    )
    try:
        resp = client.responses.create(
            model="gpt-4o-mini", input=prompt, temperature=0.1
        )
        parsed = json.loads(resp.output_text.strip())
        return parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        return {"error": str(e)}


def apply_gpt_fallback(
    client: Optional[OpenAI], entry: Dict[str, Any], parsed: Dict[str, Any]
) -> Dict[str, Any]:
    if not client or parsed.get("confidence", 0) >= 0.6:
        return parsed
    try:
        gpt_fields = gpt_refine(client, entry["text"])
        if isinstance(gpt_fields, dict) and not gpt_fields.get("error"):
            parsed.update({k: v or parsed.get(k) for k, v in gpt_fields.items()})
        else:
            parsed["gpt_fallback_error"] = (
                gpt_fields.get("error") or "empty_gpt_response"
            )
    except Exception as exc:
        parsed["gpt_fallback_error"] = str(exc)
    return parsed


# ------------------------------------------------------------
# Data Filters
# ------------------------------------------------------------
def filter_and_score(
    listings: List[Dict[str, Any]], args: argparse.Namespace
) -> List[Dict[str, Any]]:
    if args.dedupe:
        listings = dedupe_listings(listings)
    if args.score:
        for item in listings:
            item["score"] = score_listing(item)
    if args.min_conf > 0:
        listings = [x for x in listings if x.get("confidence", 0) >= args.min_conf]
    return listings


# ------------------------------------------------------------
# Core Processing
# ------------------------------------------------------------
def parse_entry(entry: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
    text = entry.get("text", "")
    if not text or not isinstance(text, str):
        print(f"[warn] Skipping entry #{idx}: missing or invalid text field.")
        return None
    try:
        parsed = heuristic_parse(entry)
    except Exception as e:
        print(f"[error] Failed to parse entry #{idx}: {e}")
        return None
    parsed["title"] = normalize_title(text)
    return parsed


def process_entries(
    data: List[Dict[str, Any]], client: Optional[OpenAI], args: argparse.Namespace
) -> List[Dict[str, Any]]:
    listings: List[Dict[str, Any]] = []
    for idx, entry in enumerate(data, 1):
        parsed = parse_entry(entry, idx)
        if not parsed:
            continue
        parsed = apply_gpt_fallback(client, entry, parsed)
        if parsed.get("price"):
            listings.append(parsed)
    return filter_and_score(listings, args)


# ------------------------------------------------------------
# I/O
# ------------------------------------------------------------
def load_client() -> Optional[OpenAI]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[warn] OPENAI_API_KEY not found. GPT fallback will be skipped.")
        return None
    return OpenAI(api_key=api_key)


def load_data(path_str: str) -> List[Dict[str, Any]]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list of OCR entries.")
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to read input file: {e}")


def save_output(listings: List[Dict[str, Any]], output_path: str) -> None:
    out_path = Path(output_path)
    avg_conf = (
        round(sum(x.get("confidence", 0) for x in listings) / len(listings), 2)
        if listings
        else 0
    )
    stats = {"count": len(listings), "avg_confidence": avg_conf}
    output_data = {"listings": listings, "stats": stats}
    try:
        out_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to write output file: {e}")
    print(f"[refiner] Refined {len(listings)} listings | avg_conf={avg_conf}")
    print(out_path.name)


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enhanced OCR JSON refiner for Sniped You"
    )
    parser.add_argument("--input", required=True, help="Path to OCR JSON file")
    parser.add_argument("--output", required=True, help="Output refined JSON path")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicates")
    parser.add_argument("--score", action="store_true", help="Add heuristic scores")
    parser.add_argument(
        "--min_conf", type=float, default=0.0, help="Minimum confidence filter"
    )
    return parser.parse_args()


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------
def main() -> None:
    args = parse_args()
    client = load_client()
    data = load_data(args.input)
    listings = process_entries(data, client, args)
    save_output(listings, args.output)


if __name__ == "__main__":
    main()
