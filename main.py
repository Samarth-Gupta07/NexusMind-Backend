from fastapi import FastAPI
from schemas import (
    VerificationResponse, 
    ExtractedDocumentData, 
    MRZValidationResult, 
    AnomalyDetectionResult, 
    BiometricResult
)

# Initialize the FastAPI server
app = FastAPI(
    title="NexusMind API Gateway", 
    description="SIH 2026 Fake Identity & Document Screening System",
    version="1.0.0"
)

# Create a POST endpoint for document verification
@app.post("/api/v1/verify", response_model=VerificationResponse)
async def verify_document(
    document_image: UploadFile = File(..., description="High-res scan of the ID"),
    live_frame: UploadFile = File(..., description="Live webcam frame for DeepFace matching")
):
    """
    Accepts multipart/form-data file uploads.
    Currently returns mock JSON, but will soon pass these files to Pair 1's AI models.
    """
    # 1. Read the raw bytes of the uploaded files into memory
    doc_bytes = await document_image.read()
    live_bytes = await live_frame.read()

    # (Future Step: Pass doc_bytes and live_bytes to Pair 1's AI scripts here)

    # 2. Return the mock Pydantic response
    return VerificationResponse(
        session_id="nx_8839201",
        risk_score=92.5,
        status="FLAGGED",
        extracted_data=ExtractedDocumentData(
            full_name="JOHN DOE",
            document_type="Passport",
            mrz_validation=MRZValidationResult(
                document_number="A1234567",
                is_valid_checksum=False,
                calculated_checksum="8"
            )
        ),
        forensics=AnomalyDetectionResult(
            pixel_tamper_detected=True,
            ela_anomaly_score=0.89,
            gradcam_heatmap_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        ),
        biometrics=BiometricResult(
            is_live_match=True,
            confidence_score=0.98
        ),
        evidence_chain="Math Trap triggered: MRZ checksum mismatch detected. Pixel Trap triggered: High ELA anomaly score.",
        audit_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )