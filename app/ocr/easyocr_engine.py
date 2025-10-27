from typing import Any, Dict
from PIL import Image, ImageEnhance, ImageOps
import easyocr
import re
import unicodedata

# Initialize EasyOCR reader once (English only for speed)
reader = easyocr.Reader(["en"], gpu=False)


def clean_text(text: str) -> str:
    """
    Clean OCR output by removing unwanted symbols, emojis, and noise.
    Keeps standard punctuation, currency symbols, parentheses, and dashes.
    """
    # Normalize Unicode (convert fancy quotes, accents, etc.)
    text = unicodedata.normalize("NFKD", text)

    # Remove emojis and non-ASCII symbols
    text = re.sub(r"[^\x00-\x7F]+", "", text)

    # Remove stray OCR artifacts, keep only allowed characters
    text = re.sub(r"[^a-zA-Z0-9$.,%()\- ]", "", text)

    # Collapse extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def preprocess_image(image_path: str, scale_factor: float = 2.5) -> str:
    """Resize, enhance contrast and sharpness for better OCR."""
    img = Image.open(image_path).convert("L")
    w, h = img.size
    img = img.resize((int(w * scale_factor), int(h * scale_factor)))

    # Apply adaptive threshold to remove gray noise
    img = img.point(lambda x: 255 if x > 180 else 0, mode="1")
    img = img.convert("L")  # convert back to grayscale for autocontrast

    # Boost contrast & sharpness
    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = ImageEnhance.Sharpness(img).enhance(3.0)

    processed_path = image_path.replace(".png", "_processed.png")
    img.save(processed_path)
    return processed_path


def extract_text_and_conf(results):
    texts, conf_values = [], []
    for res in results:
        if len(res) != 3:
            continue
        _, text, conf = res
        texts.append(str(text))
        try:
            conf_values.append(float(conf))
        except Exception:
            pass
    avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.0
    return {"text": " ".join(texts).strip(), "confidence": avg_conf}


def run_easyocr(image_path: str) -> Dict[str, Any]:
    """Run EasyOCR with preprocessing, tuning, and text cleanup."""
    processed_path = preprocess_image(image_path)
    results = reader.readtext(
        processed_path,
        detail=1,
        paragraph=False,
        contrast_ths=0.3,
        adjust_contrast=0.7,
        text_threshold=0.3,
    )

    if not results:
        return {"text": "", "fields": {}, "confidence": 0.0}

    parsed = extract_text_and_conf(results)
    full_text = clean_text(parsed["text"])

    return {"text": full_text, "fields": {}, "confidence": parsed["confidence"]}
