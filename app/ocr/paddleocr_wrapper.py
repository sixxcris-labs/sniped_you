from paddleocr import PaddleOCR


def run_paddleocr(image_path: str) -> dict:
    """
    Simple PaddleOCR wrapper for unified OCR pipeline.
    Returns text and basic metadata.
    """
    ocr = PaddleOCR(use_angle_cls=True, lang="en")
    result = ocr.ocr(image_path, cls=True)
    text_blocks = []
    for block in result:
        for line in block:
            text_blocks.append(line[1][0])
    text = " ".join(text_blocks)
    return {
        "text": text,
        "fields": {},
        "confidence": 1.0,
    }
