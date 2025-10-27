import json


def clean_refined(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both list or dict with "listings"
    if isinstance(data, dict) and "listings" in data:
        data = data["listings"]

    seen = set()
    cleaned = []

    for item in data:
        if not isinstance(item, dict):
            continue
        key = (item.get("title"), item.get("price"))
        if key in seen:
            continue
        seen.add(key)
        if item.get("confidence", 0) >= 0.6:
            cleaned.append(item)

    cleaned.sort(key=lambda x: (-x.get("confidence", 0), x.get("price", 0)))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)

    print(f"✅ Cleaned {len(cleaned)} listings → {output_path}")


if __name__ == "__main__":
    clean_refined("data/output/ocr_refined.json", "data/output/cleaned.json")
