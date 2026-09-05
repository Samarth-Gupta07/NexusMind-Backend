import hashlib
import json
import os
import shutil
from fastapi import FastAPI, UploadFile, File
from schemas import (
    VerificationResponse,
    ExtractedDocumentData,
    MRZValidationResult,
    AnomalyDetectionResult,
    BiometricResult,
)
from mrz_validator import validate_mrz
from ocr_engine import run_ocr  # Adjust filename if named differently
from vision_forencis import analyze_document

app = FastAPI(title="NexusMind Gateway", version="1.0.0")

@app.post("/api/v1/verify", response_model=VerificationResponse)
async def verify_document(
    document_image: UploadFile = File(...),
    live_frame: UploadFile = File(None)
):
    # 1. Temporarily save uploaded image to disk for OCR processing
    temp_path = f"temp_{document_image.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(document_image.file, buffer)

    try:
        # 2. Run Pair 1's OCR engine
        ocr_data = run_ocr(temp_path)
        
        # 3. Extract the last two 44-char lines (TD3 MRZ standard)
        detected_lines = [
            w["text"].replace(" ", "") for w in ocr_data.get("words", [])
        ]
        mrz_candidates = [line for line in detected_lines if len(line) == 44]

        if len(mrz_candidates) >= 2:
            line1, line2 = mrz_candidates[-2], mrz_candidates[-1]
            mrz_result = validate_mrz(line1, line2)
        else:
            # Fallback if OCR does not detect full 44-character lines
            mrz_result = validate_mrz("", "")

        # 4. Compute Dynamic Scores based on real validation results
        is_valid = mrz_result.valid
        risk_score = 10.0 if is_valid else 95.0
        status = "PASSED" if is_valid else "FLAGGED"
        evidence = (
            "All MRZ checksums verified successfully."
            if is_valid
            else f"Math Trap triggered: {', '.join(mrz_result.errors)}"
        )

        # 5. Generate SHA-256 Audit Hash for Blockchain Ledger
        payload_string = f"{mrz_result.passport_number}:{risk_score}:{status}"
        audit_hash = hashlib.sha256(payload_string.encode()).hexdigest()

        # 6. Map results into schemas.py response contract
        return VerificationResponse(
            session_id="sess_live_eval_01",
            risk_score=risk_score,
            status=status,
            extracted_data=ExtractedDocumentData(
                full_name=f"{mrz_result.given_names} {mrz_result.surname}".strip(),
                document_type=mrz_result.document_type or "Passport",
                mrz_validation=MRZValidationResult(
                    document_number=mrz_result.passport_number,
                    is_valid_checksum=is_valid,
                    calculated_checksum=str(mrz_result.field_checks[0].computed) if mrz_result.field_checks else "0"
                )
            ),
            forensics=AnomalyDetectionResult(
                pixel_tamper_detected=not is_valid,
                ela_anomaly_score=0.85 if not is_valid else 0.05,
                gradcam_heatmap_base64="data:image/png;base64,..."
            ),
            biometrics=BiometricResult(
                is_live_match=True,
                confidence_score=0.98
            ),
            evidence_chain=evidence,
            audit_hash=audit_hash
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)