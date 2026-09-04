import sys
import json
from rapidocr_onnxruntime import RapidOCR


def run_ocr(image_path):
    engine = RapidOCR()
    result, _ = engine(image_path)

    words = []
    confidences = []

    if result:
        for bbox, text, conf in result:
            words.append(
                {
                    "text": text,
                    "confidence_percent": round(float(conf) * 100, 2),
                    "bounding_box": [[int(x), int(y)] for x, y in bbox],
                }
            )
            confidences.append(float(conf))

    full_text = " ".join(w["text"] for w in words)

    overall_conf = (
        round((sum(confidences) / len(confidences)) * 100, 2)
        if confidences
        else 0.0
    )

    return {
        "image": image_path,
        "full_text": full_text,
        "overall_confidence_percent": overall_conf,
        "words": words,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_engine.py <image_path> [output.json]")
        sys.exit(1)

    image_path = sys.argv[1]
    output = run_ocr(image_path)

    json_str = json.dumps(output, indent=2, ensure_ascii=False)
    print(json_str)

    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(json_str)