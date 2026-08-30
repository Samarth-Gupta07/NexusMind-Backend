from pydantic import BaseModel, Field
from typing import Optional

# Defines the Math Trap results
class MRZValidationResult(BaseModel):
    document_number: str
    is_valid_checksum: bool
    calculated_checksum: str

class ExtractedDocumentData(BaseModel):
    full_name: Optional[str] = None
    document_type: str
    mrz_validation: MRZValidationResult

# Defines the Pixel Trap and Biometric results
class AnomalyDetectionResult(BaseModel):
    pixel_tamper_detected: bool
    ela_anomaly_score: float = Field(..., description="Error Level Analysis score")
    gradcam_heatmap_base64: str = Field(..., description="Base64 encoded Grad-CAM overlay")

class BiometricResult(BaseModel):
    is_live_match: bool
    confidence_score: float

# The final payload sent to the React Dashboard
class VerificationResponse(BaseModel):
    session_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    status: str
    extracted_data: ExtractedDocumentData
    forensics: AnomalyDetectionResult
    biometrics: BiometricResult
    evidence_chain: str = Field(..., description="LLM natural language explanation")
    audit_hash: str = Field(..., description="SHA-256 hash for Blockchain audit trail")