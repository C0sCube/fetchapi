import os
import fitz
import cv2

from google.cloud import documentai
from PIL import Image
import pytesseract
from pytesseract import Output
import numpy as np

from konstant import SECRET_KEY_GOOGLE, DOCUMENT_AI_PROJECT

# initalize the secret key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SECRET_KEY_GOOGLE


class PageWordExtractor:

    def __init__(self, pdf_path):
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor = DOCUMENT_AI_PROJECT
        self.pdf_path = pdf_path

        self.doc = fitz.open(self.pdf_path)

    def _extract_words(self, page, bbox):
        items = []
        words = page.get_text("words")  # KEY CHANGE
        for w in words:
            x0, y0, x1, y1, text = w[:5]

            text = text.strip()
            # print(text)

            if not text:
                continue

            if bbox:
                bx0, by0, bx1, by1 = bbox
                # legacy: take only text inside the bbox
                # if not (x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1):
                #     continue

                # latest: x-axis overlap allowed
                # further improvement - not x0,x1 or y0,y1 but x_center,y_center
                horizontal_overlap = not (x1 < bx0 or x0 > bx1)
                vertical_inside = y0 >= by0 and y1 <= by1

                if not (horizontal_overlap and vertical_inside):
                    continue

            items.append(
                {
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "text": text,
                    "x_center": (x0 + x1) / 2,
                    "y_center": (y0 + y1) / 2,
                    "height": y1 - y0,
                }
            )

        # print(f"FITZ SAMPLE ITEMS:{items[:5]}")
        return items

    def _scale_annotation(self, bbox, columns, source_size, target_size):
        """
        Convert coordinates between any two coordinate systems.
        source_size = (pdf_width, pdf_height)
        target_size = (docai_width, docai_height)
        """

        pdf_w, pdf_h = source_size
        doc_w, doc_h = target_size

        sx = doc_w / pdf_w
        sy = doc_h / pdf_h

        x0, y0, x1, y1 = bbox

        new_bbox = (
            x0 * sx,
            y0 * sy,
            x1 * sx,
            y1 * sy,
        )

        new_columns = [x * sx for x in columns]

        return new_bbox, new_columns

    # document ai

    def _extract_doc_words(self, page, document, scale_x, scale_y, bbox=None):

        def get_text(layout, document):
            text = ""

            for segment in layout.text_anchor.text_segments:
                start = int(segment.start_index)
                end = int(segment.end_index)
                text += document.text[start:end]

            return text

        items = []

        # for token in page.tokens[:5]:
        #     print(token.layout.bounding_poly)

        for token in page.tokens:

            text = get_text(token.layout, document).strip()

            if not text:
                continue

            verts = token.layout.bounding_poly.vertices

            xs = [v.x for v in verts]
            ys = [v.y for v in verts]

            x0 = min(xs)
            x1 = max(xs)
            y0 = min(ys)
            y1 = max(ys)

            x0 /= scale_x
            x1 /= scale_x
            y0 /= scale_y
            y1 /= scale_y

            # print(f"text={text} x0={x0} y0={y0} x1={x1} y1={y1}")

            if bbox:
                bx0, by0, bx1, by1 = bbox

                horizontal_overlap = not (x1 < bx0 or x0 > bx1)
                vertical_inside = y0 >= by0 and y1 <= by1

                if not (horizontal_overlap and vertical_inside):

                    # print(
                    #     "REJECTED",
                    #     text,
                    #     (x0, y0, x1, y1),
                    #     bbox,
                    # )

                    continue

            items.append(
                {
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "text": text,
                    "x_center": (x0 + x1) / 2,
                    "y_center": (y0 + y1) / 2,
                    "height": y1 - y0,
                }
            )

        print(f"DOCAI SAMPLE ITEMS: {items[:5]}")
        return items

    def _document_ai(self, path):

        with open(path, "rb") as f:
            document = {
                "content": f.read(),
                "mime_type": "application/pdf",
            }

        request = {
            "name": self.processor,
            "raw_document": document,
        }
        result = self.client.process_document(request=request)
        return result

    # pytesseract ai

    def _extract_pyt_words(self, image, scale_x, scale_y, bbox=None):

        data = pytesseract.image_to_data(
            image,
            output_type=Output.DICT,
            config="--psm 6",
        )

        items = []

        n = len(data["text"])

        for i in range(n):

            text = data["text"][i].strip()

            if not text:
                continue

            try:
                conf = float(data["conf"][i])
            except:
                conf = -1

            if conf < 0:
                continue

            x0 = data["left"][i]
            y0 = data["top"][i]
            x1 = x0 + data["width"][i]
            y1 = y0 + data["height"][i]

            x0 /= scale_x
            x1 /= scale_x
            y0 /= scale_y
            y1 /= scale_y

            if bbox:
                bx0, by0, bx1, by1 = bbox

                horizontal_overlap = not (x1 < bx0 or x0 > bx1)
                vertical_inside = y0 >= by0 and y1 <= by1

                if not (horizontal_overlap and vertical_inside):
                    continue

            items.append(
                {
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "text": text,
                    "x_center": (x0 + x1) / 2,
                    "y_center": (y0 + y1) / 2,
                    "height": y1 - y0,
                }
            )

        print(f"TESSERACT SAMPLE ITEMS: {items[:5]}")
        return items

    def _pytesseract_ai(self, path):

        pdf = fitz.open(path)

        pages = []

        for page in pdf:

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img.reshape(pix.height, pix.width, pix.n)

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

            pages.append(img)

        pdf.close()

        return pages

    def build_ocr_pdf(self, pdf_path, scanned_pages):

        if not scanned_pages:
            return None, {}

        scanned_pages = sorted(scanned_pages)

        ocr_pdf_path = pdf_path.replace(".pdf", "_ocr.pdf")

        src = fitz.open(pdf_path)
        dst = fitz.open()

        page_map = {}

        try:

            for new_page, original_page in enumerate(scanned_pages, start=1):

                dst.insert_pdf(
                    src,
                    from_page=original_page - 1,
                    to_page=original_page - 1,
                )

                page_map[original_page] = new_page

            dst.save(ocr_pdf_path)

        finally:

            src.close()
            dst.close()

        return ocr_pdf_path, page_map

    def _fitz_worker(self, pages):

        if not pages:
            return {}

        output = {}

        for page_number in pages:

            page = self.doc[page_number - 1]
            words = self._extract_words(page, bbox=None)

            output[page_number] = {
                "source": "fitz",
                "words": words,
                "scale_x": 1,
                "scale_y": 1,
            }

        return output

    def _docai_worker(self, ocr_pdf, page_map):

        result = self._document_ai(ocr_pdf)

        output = {}

        for original_page, ocr_page in page_map.items():

            page = result.document.pages[ocr_page - 1]

            fitz_page = self.doc[original_page - 1]

            scale_x = page.dimension.width / fitz_page.rect.width
            scale_y = page.dimension.height / fitz_page.rect.height

            output[original_page] = {
                "source": "docai",
                "words": self._extract_doc_words(
                    page,
                    result.document,
                    scale_x,
                    scale_y,
                    bbox=None,
                ),
                "scale_x": scale_x,
                "scale_y": scale_y,
            }

        return output

    def _pytesseract_worker(self, ocr_pdf, page_map):

        images = self._pytesseract_ai(ocr_pdf)

        output = {}

        for original_page, ocr_page in page_map.items():

            image = images[ocr_page - 1]
            fitz_page = self.doc[original_page - 1]

            h, w = image.shape[:2]

            scale_x = w / fitz_page.rect.width
            scale_y = h / fitz_page.rect.height

            output[original_page] = {
                "source": "pytesseract",
                "words": self._extract_pyt_words(
                    image,
                    scale_x,
                    scale_y,
                    bbox=None,
                ),
                "scale_x": scale_x,
                "scale_y": scale_y,
            }

        return output

    def handler(self, page_meta, mode="docai"):
        
        from concurrent.futures import ThreadPoolExecutor

        page_resources = {}

        # Run FITZ + OCR together
        with ThreadPoolExecutor(max_workers=2) as executor:

            fitz_future = executor.submit(
                self._fitz_worker,
                page_meta["text"],
            )

            if page_meta["scanned"]:

                ocr_pdf, page_map = self.build_ocr_pdf(
                    self.pdf_path,
                    page_meta["scanned"],
                )

                if mode == "docai":

                    ocr_future = executor.submit(
                        self._docai_worker,
                        ocr_pdf,
                        page_map,
                    )

                else:

                    ocr_future = executor.submit(
                        self._pytesseract_worker,
                        ocr_pdf,
                        page_map,
                    )

            else:
                ocr_future = None

            page_resources.update(fitz_future.result())

            if ocr_future:
                page_resources.update(ocr_future.result())

        return page_resources


    def pdf_handler(self, pdf_path):
        result = self._document_ai(pdf_path)
        output = {}
        doc = fitz.open(pdf_path)
        for page_n, fitz_page in enumerate(doc):

            page = result.document.pages[page_n]
            scale_x = page.dimension.width / fitz_page.rect.width
            scale_y = page.dimension.height / fitz_page.rect.height

            output[str(page_n)] = {
                "words": self._extract_doc_words(
                    page,
                    result.document,
                    scale_x,
                    scale_y,
                    bbox=None,
                ),
                "scale_x": scale_x,
                "scale_y": scale_y,
            }

        return output
    
    def raw_handler(self, pdf_path):
        result = self.document_ai(pdf_path)
        return result