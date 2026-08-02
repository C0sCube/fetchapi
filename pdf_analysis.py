from __future__ import annotations
import os
import time
import traceback
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any
from typing import ClassVar

import fitz
# from utils_app.logger import info, warning, error

@dataclass(slots=True)
class PageAnalysis:

    page_number: int

    page_width: float = 0.0
    page_height: float = 0.0
    character_count: int = 0
    word_count: int = 0
    line_count: int = 0
    block_count: int = 0
    font_count: int = 0
    average_font_size: float = 0.0
    image_count: int = 0
    image_area: float = 0.0
    image_coverage: float = 0.0

    drawing_count: int = 0

    has_hidden_text: bool = False
    has_text_layer: bool = False

    text_score: float = 0.0
    scan_score: float = 0.0
    ocr_score: float = 0.0

    page_type: str = "UNKNOWN"
    confidence: float = 0.0
    error: Optional[str] = None
    text_density: float = 0.0
    image_density: float = 0.0
    largest_image_area: float = 0.0
    unique_fonts: set = field(default_factory=set)
    rotation: int = 0
    is_blank: bool = False
    is_image_only: bool = False
    is_image_over_text: bool = False
    hidden_text_count: int = 0
    visible_text_count: int = 0
    page_complexity: float = 0.0


@dataclass(slots=True)
class PdfAnalysis:

    pdf_columns: ClassVar[list[str]] = [
        "pdf_type",
        "confidence",
        "total_pages",
        "text_pages",
        "scanned_pages",
        "mixed_pages",
        "ocr_pages",
        "ocr_enabled",
        "processing_time_sec",
        "extraction_engine",
        "requires_ocr",
        "requires_docling",
        "decision_reason",
    ]
    pdf_path: str
    pdf_type: str = "UNKNOWN"
    pdf_name: str = ""
    pdf_size:float = 0.0
    confidence: float = 0.0
    total_pages: int = 0
    text_pages: int = 0
    scanned_pages: int = 0
    mixed_pages: int = 0
    ocr_pages: int = 0

    average_image_coverage: float = 0.0
    average_text_density: float = 0.0

    enable_ocr: bool = False

    processing_time: float = 0.0

    pages: List[PageAnalysis] = field(default_factory=list)

    extraction_engine: str = ""
    requires_ocr: bool = False
    requires_docling: bool = False

    decision_reason: str = ""

    def summary(self) -> str:
        return (
            "\n========== PDF ANALYSIS ==========\n"
            f"PDF Type          : {self.pdf_type}\n"
            f"Confidence        : {self.confidence:.2f}%\n"
            f"Total Pages       : {self.total_pages}\n"
            f"Text Pages        : {self.text_pages}\n"
            f"Scanned Pages     : {self.scanned_pages}\n"
            f"Mixed Pages       : {self.mixed_pages}\n"
            f"OCR Pages         : {self.ocr_pages}\n"
            f"OCR Enabled       : {self.enable_ocr}\n"
            f"Processing Time   : {self.processing_time:.2f} sec\n"
            "\n"
            "========== EXTRACTION DECISION ==========\n"
            f"Engine            : {self.extraction_engine}\n"
            f"Requires OCR      : {self.requires_ocr}\n"
            f"Requires Docling  : {self.requires_docling}\n"
            f"Reason            : {self.decision_reason}\n"
        )
    def summary_dict(self) -> dict:
        return {
            "pdf_type": self.pdf_type,
            "pdf_name": self.pdf_name,
            "pdf_size":self.pdf_size,
            "size_to_page":(self.pdf_size/self.total_pages) if self.total_pages else 0,
            "confidence": self.confidence,
            "text_percent": (self.text_pages/ self.total_pages)* 100 if self.total_pages else 0,
            "total_pages": self.total_pages,
            "text_pages": self.text_pages,
            "scanned_pages": self.scanned_pages,
            "mixed_pages": self.mixed_pages,
            "ocr_pages": self.ocr_pages,
            "ocr_enabled": self.enable_ocr,
            "processing_time_sec": self.processing_time,
            "extraction_engine": self.extraction_engine,
            "requires_ocr": self.requires_ocr,
            "requires_docling": self.requires_docling,
            "decision_reason": self.decision_reason,
        }

    def _decide_extraction(self, analysis: PdfAnalysis):

        if analysis.pdf_type == "TEXT":

            analysis.extraction_engine = "PyMuPDF"
            analysis.requires_ocr = False
            analysis.requires_docling = False
            analysis.decision_reason = (
                f"{analysis.text_pages} of {analysis.total_pages} pages contain a text layer. "
                "OCR is not required. "
                "Use direct text and table extraction."
            )

        elif analysis.pdf_type == "SCANNED":

            analysis.extraction_engine = "DOCLING OCR"
            analysis.requires_ocr = True
            analysis.requires_docling = True
            analysis.decision_reason = (
                f"{analysis.scanned_pages} of {analysis.total_pages} pages are scanned. "
                "No reliable text layer detected. "
                "OCR is required."
            )

        else:

            text_ratio = analysis.text_pages / max(1, analysis.total_pages)

            if text_ratio >= 0.70:

                analysis.extraction_engine = "PyMuPDF"
                analysis.requires_ocr = False
                analysis.requires_docling = False
                analysis.decision_reason = (
                    f"{analysis.text_pages} of {analysis.total_pages} pages contain a reliable text layer. "
                    "Most content can be extracted directly. "
                    "Use PyMuPDF for extraction."
                )

            else:

                analysis.extraction_engine = "DOCLING OCR"
                analysis.requires_ocr = True
                analysis.requires_docling = True
                analysis.decision_reason = (
                    f"{analysis.text_pages} text pages and "
                    f"{analysis.mixed_pages + analysis.scanned_pages} non-text pages detected. "
                    "Docling OCR is recommended."
                )


class PdfDetector:

    def __init__(self, max_workers: Optional[int] = None):

        self.max_workers = max_workers or min(8, os.cpu_count() or 4)

    def detect(self, pdf_path: str) -> PdfAnalysis:
        start = time.perf_counter()
        analysis = PdfAnalysis(pdf_path=pdf_path)

        try:
            doc = fitz.open(pdf_path)
            analysis.pdf_name = doc.name
            analysis.pdf_size = os.path.getsize(doc.name)
        except Exception as exc:
            print(f"Unable to open PDF : {exc}")
            raise

        analysis.total_pages = len(doc)
        print(f"Analyzing {analysis.total_pages} pages using {self.max_workers} workers")

        page_results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._analyze_page, page): page.number for page in doc
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    page_results.append(result)
                except Exception:
                    traceback.print_exc()
        doc.close()

        page_results.sort(key=lambda x: x.page_number)
        analysis.pages = page_results
        self._summarize_document(analysis)
        analysis.processing_time = time.perf_counter() - start
        return analysis

    def _summarize_document(self, analysis: PdfAnalysis):

        if not analysis.pages:

            return

        total_density = 0.0

        total_image = 0.0

        for page in analysis.pages:

            total_density += page.character_count

            total_image += page.image_coverage

            if page.page_type == "TEXT":

                analysis.text_pages += 1

            elif page.page_type == "SCANNED":

                analysis.scanned_pages += 1

            elif page.page_type == "MIXED":

                analysis.mixed_pages += 1

            elif page.page_type == "OCR":

                analysis.ocr_pages += 1

        analysis.average_text_density = total_density / max(1, analysis.total_pages)

        analysis.average_image_coverage = total_image / max(1, analysis.total_pages)
        self._classify_document(analysis)

    def _analyze_page(self, page: fitz.Page) -> PageAnalysis:

        analysis = PageAnalysis(page_number=page.number + 1)

        try:
            analysis.page_width = page.rect.width
            analysis.page_height = page.rect.height

            raw = page.get_text("rawdict")
            images = page.get_images(full=True)
            drawings = page.get_drawings()

            self._analyze_text(raw, analysis)
            self._analyze_fonts(raw, analysis)
            self._analyze_images(page, images, analysis)
            self._analyze_vectors(drawings, analysis)

            self._detect_hidden_ocr(raw, analysis)
            self._detect_rotation(page, analysis)
            self._detect_blank_page(analysis)
            self._detect_image_only(analysis)
            self._detect_image_over_text(analysis)
            self._calculate_complexity(analysis)

            self._calculate_scores(analysis)
            self._classify_page(analysis)

        except Exception as e:
            analysis.error = str(e)
            print(f"\nPage {page.number + 1} ERROR")
            print(type(e).__name__)
            print(e)
            traceback.print_exc()

        return analysis

    def _span_text(self, span) -> str:

        if "text" in span:
            return span["text"]

        if "chars" in span:
            return "".join(char["c"] for char in span["chars"])

        return ""

    def _analyze_text(self, raw, analysis: PageAnalysis):

        chars = 0
        words = 0
        lines = 0
        blocks = 0

        font_sizes = []

        for block in raw["blocks"]:

            if block["type"] != 0:
                continue

            blocks += 1

            for line in block["lines"]:

                lines += 1

                for span in line["spans"]:

                    text = self._span_text(span)

                    chars += len(text)
                    words += len(text.split())

                    font_sizes.append(span["size"])

                    analysis.unique_fonts.add(span["font"])

        analysis.character_count = chars
        analysis.word_count = words
        analysis.line_count = lines
        analysis.block_count = blocks

        analysis.font_count = len(analysis.unique_fonts)

        if font_sizes:
            analysis.average_font_size = sum(font_sizes) / len(font_sizes)

        page_area = analysis.page_width * analysis.page_height

        if page_area > 0:
            analysis.text_density = chars / page_area

        analysis.has_text_layer = chars > 30

    def _analyze_images(self, page, images, analysis: PageAnalysis):

        page_area = analysis.page_width * analysis.page_height
        total_area = 0
        largest = 0

        for image in images:

            xref = image[0]

            try:
                rects = page.get_image_rects(xref)
            except Exception:
                continue

            for rect in rects:
                area = rect.width * rect.height

                total_area += area
                largest = max(largest, area)

        analysis.image_count = len(images)
        analysis.image_area = total_area
        analysis.largest_image_area = largest

        if page_area:
            analysis.image_coverage = total_area / page_area

    def _analyze_fonts(self, raw, analysis: PageAnalysis):

        fonts = set()

        for block in raw["blocks"]:

            if block["type"] != 0:
                continue

            for line in block["lines"]:

                for span in line["spans"]:
                    fonts.add(span["font"])

        analysis.font_count = len(fonts)

    def _analyze_vectors(self, drawings, analysis: PageAnalysis):
        analysis.drawing_count = len(drawings)

    def _detect_hidden_ocr(self, raw, analysis: PageAnalysis):
        hidden = 0
        visible = 0

        for block in raw["blocks"]:

            if block["type"] != 0:
                continue

            for line in block["lines"]:

                for span in line["spans"]:

                    text = self._span_text(span)

                    if not text:
                        continue

                    flags = span.get("flags", 0)

                    if flags & 2:
                        hidden += len(text)
                    else:
                        visible += len(text)

        analysis.hidden_text_count = hidden
        analysis.visible_text_count = visible
        analysis.has_hidden_text = hidden > visible

    def _detect_rotation(self, page, analysis: PageAnalysis):

        analysis.rotation = page.rotation

    def _detect_blank_page(self, analysis: PageAnalysis):

        analysis.is_blank = (
            analysis.character_count < 10
            and analysis.image_count == 0
            and analysis.drawing_count == 0
        )

    def _detect_image_only(self, analysis: PageAnalysis):

        analysis.is_image_only = (
            analysis.image_coverage > 0.90 and analysis.character_count < 20
        )

    def _detect_image_over_text(self, analysis: PageAnalysis):

        analysis.is_image_over_text = (
            analysis.image_coverage > 0.70 and analysis.character_count > 500
        )

    def _calculate_complexity(self, analysis: PageAnalysis):

        analysis.page_complexity = (
            analysis.block_count
            + analysis.image_count * 5
            + analysis.drawing_count
            + analysis.font_count * 2
        )

    def _calculate_scores(self, analysis: PageAnalysis):

        text_score = 0
        scan_score = 0
        ocr_score = 0

        # Text layer

        if analysis.character_count > 2000:
            text_score += 40
        elif analysis.character_count > 500:
            text_score += 25
        elif analysis.character_count > 100:
            text_score += 10
        else:
            scan_score += 20

        # Fonts

        if analysis.font_count > 5:
            text_score += 20

        elif analysis.font_count == 0:
            scan_score += 15

        # Images

        if analysis.image_coverage > 0.80:
            scan_score += 40

        elif analysis.image_coverage > 0.40:
            scan_score += 20

        # Drawings

        if analysis.drawing_count > 50:
            text_score += 15

        # Text layer

        if analysis.has_text_layer:
            text_score += 15
        else:
            scan_score += 25

        analysis.text_score = text_score
        analysis.scan_score = scan_score
        analysis.ocr_score = ocr_score

        if analysis.has_hidden_text:
            analysis.ocr_score += 35

        if analysis.is_image_only:
            analysis.scan_score += 35

        if analysis.is_image_over_text:
            analysis.ocr_score += 25

        if analysis.rotation != 0:
            analysis.scan_score += 10

        if analysis.is_blank:
            analysis.scan_score += 5

    def _classify_document(self, analysis: PdfAnalysis):

        if analysis.text_pages >= analysis.total_pages * 0.90:

            analysis.pdf_type = "TEXT"

            analysis.enable_ocr = False

        elif analysis.scanned_pages >= analysis.total_pages * 0.90:

            analysis.pdf_type = "SCANNED"

            analysis.enable_ocr = True

        else:

            analysis.pdf_type = "MIXED"

            analysis.enable_ocr = True

        if analysis.pages:
            analysis.confidence = sum(page.confidence for page in analysis.pages) / len(
                analysis.pages
            )

        analysis._decide_extraction(analysis)

    def _classify_page(self, analysis: PageAnalysis):

        if analysis.ocr_score >= 35:
            analysis.page_type = "OCR"

        elif analysis.text_score > analysis.scan_score + 20:
            analysis.page_type = "TEXT"

        elif analysis.scan_score > analysis.text_score + 20:
            analysis.page_type = "SCANNED"

        else:
            analysis.page_type = "MIXED"

        analysis.confidence = min(
            max(analysis.text_score, analysis.scan_score, analysis.ocr_score), 100
        )



