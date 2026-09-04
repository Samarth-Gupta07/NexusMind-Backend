"""
mrz_validator.py
-----------------
Parses and validates the Machine Readable Zone (MRZ) of a passport,
following the ICAO Doc 9303 TD3 specification (2 lines x 44 chars,
used on passport photo pages).

This module is intentionally decoupled from OCR: it accepts already
-extracted MRZ text (two 44-char strings) and does not do any image
processing itself. `ocr_engine.py` is expected to produce that text;
this module tells you whether it is internally consistent (checksums)
and well-formed.

TD3 layout
==========
Line 1 (44 chars):
    P<CCCSURNAME<<GIVEN<NAMES<<<<<<<<<<<<<<<<<<<<<<<<<<
    [0]      document type ('P' = passport, may be 'P<')
    [1]      '<' filler (only present when type is exactly 1 char + filler)
    [2:5]    issuing country code (3 letters)
    [5:44]   name field: SURNAME<<GIVEN<NAMES..., '<' = space/separator

Line 2 (44 chars):
    L898902C<3UTO6908061F9406236ZE184226B<<<<<10
    [0:9]    passport number (9 chars, '<' padded)
    [9]      check digit for passport number
    [10:13]  nationality (3 letters)
    [13:19]  date of birth YYMMDD
    [19]     check digit for DOB
    [20]     sex (M/F/<)
    [21:27]  expiry date YYMMDD
    [27]     check digit for expiry date
    [28:42]  personal number (optional, '<' padded, 14 chars)
    [42]     check digit for personal number (may be '<' if field unused)
    [43]     composite check digit over specific fields

Checksum algorithm (ICAO 9303)
===============================
Each character is mapped to a numeric value:
    '0'-'9'  -> 0-9
    'A'-'Z'  -> 10-35
    '<'      -> 0
Then each character position is weighted cyclically 7, 3, 1, 7, 3, 1, ...
and the check digit is (sum of weighted values) mod 10.
"""

from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------
# Character -> numeric value mapping and checksum core
# --------------------------------------------------------------------------

_WEIGHTS = (7, 3, 1)


def _char_value(ch: str) -> int:
    if ch == "<":
        return 0
    if ch.isdigit():
        return int(ch)
    if ch.isalpha():
        return ord(ch.upper()) - ord("A") + 10
    raise ValueError(f"Invalid MRZ character: {ch!r}")


def compute_check_digit(data: str) -> int:
    """Compute the ICAO 9303 check digit for a given data string."""
    total = 0
    for i, ch in enumerate(data):
        total += _char_value(ch) * _WEIGHTS[i % 3]
    return total % 10


def _digit_at(line: str, idx: int) -> Optional[int]:
    ch = line[idx]
    return int(ch) if ch.isdigit() else None


# --------------------------------------------------------------------------
# Result containers
# --------------------------------------------------------------------------

@dataclass
class FieldCheck:
    name: str
    expected: Optional[int]
    computed: int
    valid: bool


@dataclass
class MRZResult:
    valid: bool
    document_type: str
    issuing_country: str
    surname: str
    given_names: str
    passport_number: str
    nationality: str
    date_of_birth: str  # YYMMDD
    sex: str
    expiry_date: str  # YYMMDD
    personal_number: str
    field_checks: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "valid": self.valid,
            "document_type": self.document_type,
            "issuing_country": self.issuing_country,
            "surname": self.surname,
            "given_names": self.given_names,
            "passport_number": self.passport_number,
            "nationality": self.nationality,
            "date_of_birth": self.date_of_birth,
            "sex": self.sex,
            "expiry_date": self.expiry_date,
            "personal_number": self.personal_number,
            "field_checks": [fc.__dict__ for fc in self.field_checks],
            "errors": self.errors,
        }


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def _clean_line(line: str) -> str:
    """Uppercase and strip stray whitespace OCR sometimes introduces."""
    return line.strip().upper().replace(" ", "")


def validate_mrz(line1: str, line2: str) -> MRZResult:
    """
    Validate a TD3 (passport) MRZ given its two raw text lines.
    Does not raise on malformed input -- malformations are reported
    in `errors` and `valid` will be False.
    """
    errors = []
    line1 = _clean_line(line1)
    line2 = _clean_line(line2)

    if len(line1) != 44:
        errors.append(f"Line 1 length is {len(line1)}, expected 44")
    if len(line2) != 44:
        errors.append(f"Line 2 length is {len(line2)}, expected 44")

    if errors:
        # Can't safely index fixed offsets on malformed lines.
        return MRZResult(
            valid=False,
            document_type="", issuing_country="", surname="", given_names="",
            passport_number="", nationality="", date_of_birth="", sex="",
            expiry_date="", personal_number="",
            field_checks=[], errors=errors,
        )

    # ---- Line 1 fields ----
    document_type = line1[0:2].replace("<", "")
    issuing_country = line1[2:5]
    name_field = line1[5:44]
    if "<<" in name_field:
        surname_raw, given_raw = name_field.split("<<", 1)
    else:
        surname_raw, given_raw = name_field, ""
    surname = surname_raw.replace("<", " ").strip()
    given_names = given_raw.replace("<", " ").strip()

    # ---- Line 2 fields ----
    passport_number = line2[0:9]
    passport_number_check = _digit_at(line2, 9)
    nationality = line2[10:13]
    dob = line2[13:19]
    dob_check = _digit_at(line2, 19)
    sex = line2[20]
    expiry = line2[21:27]
    expiry_check = _digit_at(line2, 27)
    personal_number = line2[28:42]
    personal_number_check_char = line2[42]
    composite_check = _digit_at(line2, 43)

    field_checks = []

    def check(name: str, data: str, expected: Optional[int]):
        computed = compute_check_digit(data)
        valid = (expected is not None) and (computed == expected)
        field_checks.append(FieldCheck(name, expected, computed, valid))
        if expected is None:
            errors.append(f"{name}: check digit position was not a digit")
        elif not valid:
            errors.append(
                f"{name}: check digit mismatch (expected {expected}, computed {computed})"
            )
        return valid

    check("passport_number", passport_number, passport_number_check)
    check("date_of_birth", dob, dob_check)
    check("expiry_date", expiry, expiry_check)

    # Personal number check digit is only meaningful if the field is used
    # (issuing states often leave it '<' padded and unchecked).
    personal_number_used = personal_number_check_char.isdigit()
    if personal_number_used:
        check("personal_number", personal_number, int(personal_number_check_char))

    # Composite check digit covers: passport number block, DOB block,
    # expiry block, and personal number block (each including their own
    # check digit), concatenated in that order.
    composite_data = (
        line2[0:10] + line2[13:20] + line2[21:28] + line2[28:43]
    )
    check("composite", composite_data, composite_check)

    valid = all(fc.valid for fc in field_checks)

    return MRZResult(
        valid=valid,
        document_type=document_type,
        issuing_country=issuing_country,
        surname=surname,
        given_names=given_names,
        passport_number=passport_number.replace("<", ""),
        nationality=nationality,
        date_of_birth=dob,
        sex=sex,
        expiry_date=expiry,
        personal_number=personal_number.replace("<", ""),
        field_checks=field_checks,
        errors=errors,
    )


# --------------------------------------------------------------------------
# Quick manual test
# --------------------------------------------------------------------------

if __name__ == "__main__":
    # Standard ICAO 9303 worked example (this is a textbook sample, not a
    # real person's data).
    sample_line1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
    sample_line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"

    result = validate_mrz(sample_line1, sample_line2)
    import json
    print(json.dumps(result.summary(), indent=2))
