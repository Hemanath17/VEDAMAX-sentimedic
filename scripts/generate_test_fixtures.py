#!/usr/bin/env python3
# Run once from your project root: python scripts/generate_test_fixtures.py

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_fonts():
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    try:
        font_title = ImageFont.truetype(candidates[0], 28)
        font_header = ImageFont.truetype(candidates[0], 18)
        font_body = ImageFont.truetype(candidates[1], 16)
        return font_title, font_header, font_body
    except Exception:
        try:
            font_title = ImageFont.truetype(candidates[2], 28)
            font_header = ImageFont.truetype(candidates[2], 18)
            font_body = ImageFont.truetype(candidates[3], 16)
            return font_title, font_header, font_body
        except Exception:
            default = ImageFont.load_default()
            return default, default, default


def generate_lab_report():
    Path("tests/fixtures/images").mkdir(parents=True, exist_ok=True)
    width, height = 800, 1000
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    font_title, font_header, font_body = _load_fonts()

    y = 40
    draw.text((40, y), "QUEST DIAGNOSTICS", font=font_title, fill="black")
    y += 50
    draw.text((40, y), "LABORATORY REPORT", font=font_header, fill="black")
    y += 40
    draw.line([(40, y), (760, y)], fill="black", width=2)
    y += 30
    draw.text((40, y), "Patient Name: Jane Test-Doe", font=font_body, fill="black")
    y += 30
    draw.text((40, y), "Date of Birth: 01/15/1980", font=font_body, fill="black")
    y += 30
    draw.text((40, y), "Collection Date: 06/28/2026", font=font_body, fill="black")
    y += 30
    draw.text((40, y), "Ordering Physician: Dr. A. Smith", font=font_body, fill="black")
    y += 50
    draw.line([(40, y), (760, y)], fill="black", width=1)
    y += 30
    draw.text((40, y), "TEST", font=font_header, fill="black")
    draw.text((300, y), "RESULT", font=font_header, fill="black")
    draw.text((450, y), "REFERENCE RANGE", font=font_header, fill="black")
    draw.text((650, y), "FLAG", font=font_header, fill="black")
    y += 30
    draw.line([(40, y), (760, y)], fill="black", width=1)
    y += 20
    rows = [
        ("Glucose, Fasting", "180 mg/dL", "70-99 mg/dL", "HIGH"),
        ("Hemoglobin A1c", "7.2 %", "<5.7 %", "HIGH"),
        ("Total Cholesterol", "210 mg/dL", "<200 mg/dL", "HIGH"),
        ("LDL Cholesterol", "130 mg/dL", "<100 mg/dL", "HIGH"),
        ("HDL Cholesterol", "38 mg/dL", ">40 mg/dL", "LOW"),
        ("Triglycerides", "150 mg/dL", "<150 mg/dL", ""),
        ("Sodium", "140 mmol/L", "135-145 mmol/L", ""),
        ("Potassium", "4.1 mmol/L", "3.5-5.0 mmol/L", ""),
    ]
    for test, result, ref_range, flag in rows:
        draw.text((40, y), test, font=font_body, fill="black")
        draw.text((300, y), result, font=font_body, fill="black")
        draw.text((450, y), ref_range, font=font_body, fill="black")
        draw.text((650, y), flag, font=font_body, fill="red" if flag else "black")
        y += 35
    y += 20
    draw.line([(40, y), (760, y)], fill="black", width=2)
    y += 30
    draw.text(
        (40, y),
        "Comments: Patient advised to follow up with physician",
        font=font_body,
        fill="black",
    )
    y += 30
    draw.text(
        (40, y),
        "regarding elevated glucose and lipid panel results.",
        font=font_body,
        fill="black",
    )
    img.save("tests/fixtures/images/sample_lab_report.png")
    print("Generated: tests/fixtures/images/sample_lab_report.png")


def generate_non_document():
    Path("tests/fixtures/images").mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (600, 400), color=(180, 140, 130))
    draw = ImageDraw.Draw(img)
    draw.ellipse([200, 150, 380, 280], fill=(140, 30, 30))
    draw.ellipse([220, 170, 360, 260], fill=(170, 50, 50))
    img.save("tests/fixtures/images/sample_non_document.png")
    print("Generated: tests/fixtures/images/sample_non_document.png")


if __name__ == "__main__":
    generate_lab_report()
    generate_non_document()
    print("Done. Run: pytest tests/unit/test_ingestion/test_document_image_processor.py -v")
