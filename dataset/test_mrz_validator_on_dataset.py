"""
test_mrz_validator_on_dataset.py
---------------------------------
Runs mrz_validator.validate_mrz() against every passport entry in
dataset/labels.json and checks the result matches the expected label.

This exists because ocr_engine.py isn't built yet -- normally OCR would
extract the MRZ text from the image, but until then labels.json gives us
the ground-truth text for each image directly, so mrz_validator.py can
still be tested and demoed end-to-end right now.

Run from the repo root:
    python3 dataset/test_mrz_validator_on_dataset.py
"""

import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))  # so `import mrz_validator` finds the repo-root file
from mrz_validator import validate_mrz  # noqa: E402


def main():
    with open(os.path.join(HERE, "labels.json")) as f:
        manifest = json.load(f)

    passed = 0
    failed = 0

    for entry in manifest:
        if entry["document_type"] != "passport":
            continue  # mrz_validator only handles MRZ (passport), not the ID card

        result = validate_mrz(entry["mrz_line1"], entry["mrz_line2"])
        expected_valid = entry["label"] == "valid"

        ok = result.valid == expected_valid
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {entry['file']:45s} expected={entry['label']:9s} got_valid={result.valid}")
        if not ok:
            print(f"         errors: {result.errors}")

        passed += ok
        failed += not ok

    print(f"\n{passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
