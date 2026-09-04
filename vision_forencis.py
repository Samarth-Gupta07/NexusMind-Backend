import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import io
import argparse
import json
import os


# ---------------------------------------------------------
# LOAD IMAGE
# ---------------------------------------------------------

def load_image(image_path):
    """
    OpenCV ki help se document image load karta hai.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Unable to load image: {image_path}")

    return image


# ---------------------------------------------------------
# 1. IMAGE SHARPNESS / BLUR CHECK
# ---------------------------------------------------------

def calculate_blur_score(image):
    """
    Laplacian variance se image sharpness estimate karta hai.

    Higher score  -> sharper image
    Lower score   -> blurred image
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    score = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    return round(float(score), 2)


# ---------------------------------------------------------
# 2. IMAGE BRIGHTNESS
# ---------------------------------------------------------

def calculate_brightness(image):
    """
    Average grayscale intensity calculate karta hai.

    0   -> completely dark
    255 -> completely bright
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    brightness = np.mean(gray)

    return round(float(brightness), 2)


# ---------------------------------------------------------
# 3. NOISE / PIXEL INCONSISTENCY
# ---------------------------------------------------------

def calculate_noise_inconsistency(image, block_size=100):
    """
    Document ko multiple blocks mein divide karke har block
    ka high-frequency noise compare karta hai.

    Large variation possible editing / local manipulation
    ka indicator ho sakta hai.
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    height, width = gray.shape

    noise_scores = []

    for y in range(0, height - block_size + 1, block_size):

        for x in range(0, width - block_size + 1, block_size):

            block = gray[
                y:y + block_size,
                x:x + block_size
            ]

            if block.size == 0:
                continue

            laplacian = cv2.Laplacian(
                block,
                cv2.CV_64F
            )

            block_noise = np.std(laplacian)

            noise_scores.append(block_noise)

    if len(noise_scores) < 2:
        return 0.0

    mean_noise = np.mean(noise_scores)

    if mean_noise == 0:
        return 0.0

    inconsistency = (
        np.std(noise_scores) /
        mean_noise
    )

    return round(float(inconsistency), 3)


# ---------------------------------------------------------
# 4. ERROR LEVEL ANALYSIS (ELA)
# ---------------------------------------------------------

def calculate_ela(image_path, jpeg_quality=90):
    """
    Original image ko JPEG mein recompress karta hai aur
    original vs recompressed version ka difference measure karta hai.

    Unusual difference possible editing/compression inconsistency
    indicate kar sakta hai.
    """

    original = Image.open(image_path).convert("RGB")

    buffer = io.BytesIO()

    original.save(
        buffer,
        format="JPEG",
        quality=jpeg_quality
    )

    buffer.seek(0)

    recompressed = Image.open(buffer).convert("RGB")

    difference = ImageChops.difference(
        original,
        recompressed
    )

    difference_np = np.array(
        difference
    ).astype(np.float32)

    mean_difference = np.mean(
        difference_np
    )

    max_difference = np.max(
        difference_np
    )

    # Bright regions ka percentage
    gray_diff = cv2.cvtColor(
        difference_np.astype(np.uint8),
        cv2.COLOR_RGB2GRAY
    )

    hotspot_pixels = np.sum(
        gray_diff > 20
    )

    total_pixels = gray_diff.size

    hotspot_ratio = (
        hotspot_pixels /
        total_pixels
    ) * 100

    return {
        "ela_score": round(
            float(mean_difference),
            3
        ),

        "ela_max_difference": round(
            float(max_difference),
            2
        ),

        "ela_hotspot_ratio": round(
            float(hotspot_ratio),
            2
        )
    }


# ---------------------------------------------------------
# OPTIONAL ELA IMAGE
# ---------------------------------------------------------

def save_ela_visualization(
    image_path,
    output_path="ela_output.jpg",
    jpeg_quality=90
):
    """
    ELA difference ko enhance karke image ke form mein save karta hai.
    Demo ke time suspicious regions visually dikhane ke kaam aa sakta hai.
    """

    original = Image.open(
        image_path
    ).convert("RGB")

    buffer = io.BytesIO()

    original.save(
        buffer,
        format="JPEG",
        quality=jpeg_quality
    )

    buffer.seek(0)

    recompressed = Image.open(
        buffer
    ).convert("RGB")

    difference = ImageChops.difference(
        original,
        recompressed
    )

    extrema = difference.getextrema()

    max_diff = max(
        value[1] for value in extrema
    )

    if max_diff == 0:
        max_diff = 1

    scale = 255.0 / max_diff

    enhanced = ImageEnhance.Brightness(
        difference
    ).enhance(scale)

    enhanced.save(output_path)

    return output_path


# ---------------------------------------------------------
# 5. IMAGE QUALITY ASSESSMENT
# ---------------------------------------------------------

def assess_image_quality(
    blur_score,
    brightness
):
    """
    Basic quality classification.
    """

    issues = []

    if blur_score < 60:
        issues.append(
            "Document appears blurred"
        )

    if brightness < 45:
        issues.append(
            "Document image is too dark"
        )

    elif brightness > 220:
        issues.append(
            "Document image is overexposed"
        )

    if issues:
        quality = "POOR"
    else:
        quality = "GOOD"

    return quality, issues


# ---------------------------------------------------------
# 6. FORENSIC RISK SCORING
# ---------------------------------------------------------

def calculate_forensic_risk(
    blur_score,
    noise_inconsistency,
    ela_score,
    ela_hotspot_ratio
):
    """
    Prototype-based weighted rule engine.

    NOTE:
    Ye scientifically universal thresholds nahi hain.
    Dataset testing ke according tune karna hoga.
    """

    suspicion_score = 0
    reasons = []


    # -------------------------
    # Blur
    # -------------------------

    if blur_score < 60:

        suspicion_score += 10

        reasons.append(
            "Low document sharpness"
        )


    # -------------------------
    # Noise inconsistency
    # -------------------------

    if noise_inconsistency > 0.75:

        suspicion_score += 35

        reasons.append(
            "Strong pixel/noise inconsistency detected"
        )

    elif noise_inconsistency > 0.50:

        suspicion_score += 20

        reasons.append(
            "Moderate pixel/noise inconsistency detected"
        )


    # -------------------------
    # ELA
    # -------------------------

    if ela_score > 10:

        suspicion_score += 30

        reasons.append(
            "High compression inconsistency detected"
        )

    elif ela_score > 6:

        suspicion_score += 15

        reasons.append(
            "Moderate compression inconsistency detected"
        )


    # -------------------------
    # ELA hotspot
    # -------------------------

    if ela_hotspot_ratio > 15:

        suspicion_score += 20

        reasons.append(
            "Unusual high-error regions detected"
        )

    elif ela_hotspot_ratio > 7:

        suspicion_score += 10

        reasons.append(
            "Localized compression anomalies detected"
        )


    suspicion_score = min(
        suspicion_score,
        100
    )


    # Risk classification

    if suspicion_score <= 20:

        risk_level = "LOW"

    elif suspicion_score <= 50:

        risk_level = "MEDIUM"

    else:

        risk_level = "HIGH"


    if not reasons:

        reasons.append(
            "No major visual anomalies detected"
        )


    return (
        suspicion_score,
        risk_level,
        reasons
    )


# ---------------------------------------------------------
# MAIN DOCUMENT FORENSICS FUNCTION
# ---------------------------------------------------------

def analyze_document(
    image_path,
    save_ela=False
):
    """
    Complete document forensic analysis.
    """

    image = load_image(
        image_path
    )

    blur_score = calculate_blur_score(
        image
    )

    brightness = calculate_brightness(
        image
    )

    noise_inconsistency = (
        calculate_noise_inconsistency(
            image
        )
    )

    ela_result = calculate_ela(
        image_path
    )

    quality, quality_issues = (
        assess_image_quality(
            blur_score,
            brightness
        )
    )

    (
        suspicion_score,
        risk_level,
        forensic_reasons
    ) = calculate_forensic_risk(

        blur_score,

        noise_inconsistency,

        ela_result["ela_score"],

        ela_result[
            "ela_hotspot_ratio"
        ]
    )

    reasons = (
        quality_issues +
        forensic_reasons
    )

    ela_output = None

    if save_ela:

        filename = os.path.basename(
            image_path
        )

        ela_output = (
            "ela_" + filename
        )

        save_ela_visualization(
            image_path,
            ela_output
        )


    return {

        "image_path":
            image_path,

        "image_quality":
            quality,

        "blur_score":
            blur_score,

        "brightness":
            brightness,

        "noise_inconsistency":
            noise_inconsistency,

        "ela_score":
            ela_result[
                "ela_score"
            ],

        "ela_hotspot_ratio":
            ela_result[
                "ela_hotspot_ratio"
            ],

        "suspicion_score":
            suspicion_score,

        "risk_level":
            risk_level,

        "reasons":
            reasons,

        "ela_visualization":
            ela_output
    }


# ---------------------------------------------------------
# RUN FILE DIRECTLY
# ---------------------------------------------------------

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=
        "AuthentiScan AI Document Vision Forensics"
    )

    parser.add_argument(
        "image",
        help="Path of document image"
    )

    parser.add_argument(
        "--save-ela",
        action="store_true",
        help="Save ELA visualization"
    )

    args = parser.parse_args()

    result = analyze_document(
        args.image,
        args.save_ela
    )


    print(
        "\n========== AUTHENTISCAN VISION FORENSICS ==========\n"
    )

    print(
        json.dumps(
            result,
            indent=4
        )
    )

    print(
        "\n===================================================\n"
    )