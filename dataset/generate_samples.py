"""
generate_samples.py
--------------------
Generates SYNTHETIC passport data-page images for testing the pipeline:
  - sample_passport_valid.jpg     : a clean, internally-consistent MRZ
  - sample_passport_tampered.jpg  : same document with the MRZ altered
                                     but a mismatched checksum (simulates
                                     tampering for vision_forensics.py /
                                     mrz_validator.py to catch)

No real identity data is used -- names/numbers are fictional, and check
digits are computed with the same ICAO 9303 algorithm as mrz_validator.py
so "valid" really does validate cleanly.

Run:
    python3 generate_samples.py
Outputs into this directory:
    sample_passport_valid.jpg
    sample_passport_tampered.jpg
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

# Reuse the exact same checksum logic the validator uses, so the
# "valid" sample is guaranteed to pass validate_mrz().
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mrz_validator import compute_check_digit, validate_mrz  # noqa: E402

WIDTH, HEIGHT = 1000, 650
MRZ_FONT_SIZE = 28
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def build_mrz_lines(surname, given, doc_no, nationality, dob, sex, expiry, personal_no="", country="UTO"):
    """Build a valid TD3 MRZ pair for fictional data, computing real check digits."""
    name_field = f"{surname}<<{given}".replace(" ", "<")
    line1 = f"P<{country}{name_field}"
    line1 = (line1 + "<" * 44)[:44]

    doc_no_padded = (doc_no + "<" * 9)[:9]
    doc_check = compute_check_digit(doc_no_padded)
    dob_check = compute_check_digit(dob)
    expiry_check = compute_check_digit(expiry)
    personal_padded = (personal_no + "<" * 14)[:14]
    personal_check = compute_check_digit(personal_padded) if personal_no else "<"

    composite_data = (
        doc_no_padded + str(doc_check) + dob + str(dob_check) + expiry + str(expiry_check) + personal_padded
    )
    composite_check = compute_check_digit(composite_data)

    line2 = (
        f"{doc_no_padded}{doc_check}{nationality}{dob}{dob_check}{sex}"
        f"{expiry}{expiry_check}{personal_padded}{personal_check}{composite_check}"
    )
    line2 = (line2 + "<" * 44)[:44]
    return line1, line2


def render_passport(line1, line2, surname, given, doc_no, nationality, dob, sex, expiry, path):
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(235, 230, 215))
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_PATH_BOLD, 32)
    label_font = ImageFont.truetype(FONT_PATH, 18)
    value_font = ImageFont.truetype(FONT_PATH_BOLD, 20)
    mrz_font = ImageFont.truetype(FONT_PATH, MRZ_FONT_SIZE)

    draw.rectangle([0, 0, WIDTH, 90], fill=(30, 40, 70))
    draw.text((30, 25), "UTOPIA  •  PASSPORT  •  SYNTHETIC SAMPLE", font=title_font, fill=(255, 255, 255))

    draw.rectangle([650, 120, 930, 380], outline=(80, 80, 80), width=2)
    draw.text((700, 230), "PHOTO", font=label_font, fill=(150, 150, 150))

    fields = [
        ("Surname", surname),
        ("Given Names", given),
        ("Passport No.", doc_no),
        ("Nationality", nationality),
        ("Date of Birth", dob),
        ("Sex", sex),
        ("Date of Expiry", expiry),
    ]
    y = 130
    for label, value in fields:
        draw.text((40, y), label.upper(), font=label_font, fill=(90, 90, 90))
        draw.text((40, y + 22), value, font=value_font, fill=(20, 20, 20))
        y += 60

    draw.rectangle([0, 520, WIDTH, 650], fill=(210, 210, 220))
    draw.text((40, 545), line1, font=mrz_font, fill=(0, 0, 0))
    draw.text((40, 585), line2, font=mrz_font, fill=(0, 0, 0))

    img.save(path, quality=92)
    print(f"Wrote {path}")


def main():
    out_dir = os.path.dirname(__file__)

    # ---- Valid sample ----
    l1, l2 = build_mrz_lines(
        surname="SHARMA", given="ROHIT KUMAR", doc_no="X1234567",
        nationality="UTO", dob="960715", sex="M", expiry="300101",
    )
    assert validate_mrz(l1, l2).valid, "Generated 'valid' sample failed its own checksum!"
    render_passport(l1, l2, "SHARMA", "ROHIT KUMAR", "X1234567", "UTO",
                     "960715", "M", "300101", os.path.join(out_dir, "sample_passport_valid.jpg"))

    # ---- Tampered sample: same layout, but the printed expiry date on the
    # visual data page is changed to "300101" -> "351231" WITHOUT
    # recomputing the MRZ line, so the MRZ still says the old date and/or
    # the check digit no longer matches -- this is the classic tamper
    # signature: visual field vs MRZ field mismatch + bad checksum.
    tampered_l2 = l2[:21] + "351231" + l2[27:]  # corrupt expiry block, leave old check digit
    result = validate_mrz(l1, tampered_l2)
    assert not result.valid, "Tampered sample unexpectedly validated -- fix the corruption offset."
    render_passport(l1, tampered_l2, "SHARMA", "ROHIT KUMAR", "X1234567", "UTO",
                     "960715", "M", "351231", os.path.join(out_dir, "sample_passport_tampered.jpg"))


if __name__ == "__main__":
    main()
