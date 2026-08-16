import os, json
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeOutputOption

ENDPOINT = ""  # os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
KEY = ""  # os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]
PDF_PATH = Path(r"500322.pdf")

OUTPUT_DIR = Path("azure_output")
OUTPUT_DIR.mkdir(exist_ok=True)


client = DocumentIntelligenceClient(
    endpoint=ENDPOINT, credential=AzureKeyCredential(KEY)
)


print(f"Processing: {PDF_PATH.name}")
with open(PDF_PATH, "rb") as f:
    poller = client.begin_analyze_document("prebuilt-read", body=f)
    result = poller.result()


print("OCR completed.")


text_path = OUTPUT_DIR / f"{PDF_PATH.stem}_ocr.txt"
with open(text_path, "w", encoding="utf-8") as f:
    for page in result.pages:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"PAGE {page.page_number}\n")
        f.write(f"{'=' * 80}\n\n")

        for line in page.lines:
            f.write(line.content + "\n")


print(f"OCR text saved: {text_path}")

ocr_data = {"pages": []}
for page in result.pages:
    page_data = {
        "page_number": page.page_number,
        "width": page.width,
        "height": page.height,
        "unit": page.unit,
        "lines": [],
        "words": [],
    }

    for line in page.lines:
        page_data["lines"].append({"text": line.content, "polygon": line.polygon})

    for word in page.words:
        page_data["words"].append(
            {
                "text": word.content,
                "confidence": word.confidence,
                "polygon": word.polygon,
            }
        )

    ocr_data["pages"].append(page_data)


json_path = OUTPUT_DIR / f"{PDF_PATH.stem}_ocr.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(ocr_data, f, indent=2)


print(f"OCR JSON saved: {json_path}")


# =========================
# CREATE SEARCHABLE PDF
# =========================

print("Creating searchable PDF...")

with open(PDF_PATH, "rb") as f:
    pdf_poller = client.begin_analyze_document(
        "prebuilt-read",
        body=f,
        output=[AnalyzeOutputOption.PDF],
    )

    pdf_result = pdf_poller.result()


# Get operation ID
operation_id = pdf_poller.details["operation_id"]
print(f"Operation ID: {operation_id}")

# Download generated searchable PDF
pdf_response = client.get_analyze_result_pdf(
    model_id=pdf_result.model_id,
    result_id=operation_id,
)
searchable_pdf_path = OUTPUT_DIR / f"{PDF_PATH.stem}_searchable.pdf"
with open(searchable_pdf_path, "wb") as writer:
    writer.writelines(pdf_response)

print(f"Searchable PDF saved: {searchable_pdf_path}")
