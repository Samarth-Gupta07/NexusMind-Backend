def generate_evidence_chain(is_mrz_valid: bool, forensics_data: dict) -> str:
    # 1. Structure the exact prompt
    prompt = f"""
    You are an AI border security assistant. Analyze these document inspection results:
    - MRZ Math Trap Valid: {is_mrz_valid}
    - Pixel Trap Tamper Risk: {forensics_data['risk_level']}
    - ELA Anomaly Score: {forensics_data['ela_score']}
    - Forensic Reasons: {', '.join(forensics_data['reasons'])}

    Provide a concise, 1-2 sentence evidence chain explaining why this document passed or failed.
    """

    # 2. Call the LLM API (Simulated here for immediate testing)
    # TODO: Replace with real OpenAI/LLaVA API call: 
    # response = openai.ChatCompletion.create(model="gpt-4", messages=[...])

    # 3. Dynamic Mock Fallback for Prototype Demo
    if is_mrz_valid and forensics_data['risk_level'] == "LOW":
        return "Document passed all checks. MRZ checksums are mathematically valid and no pixel anomalies were detected."
    elif not is_mrz_valid:
        return "Math Trap triggered: MRZ checksum mismatch detected, indicating forged metadata."
    else:
        return f"Pixel Trap triggered: {forensics_data['reasons'][0]} detected via Multi-Spectral Analysis."