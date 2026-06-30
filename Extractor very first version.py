"""
Structure of Output:

figures
images
pages
tables
Document
    document_name: "outputSPEC2",
    metadata
    sections
    requirements
    figures
    tables
    notes
    acronyms
    cross_references
    semantic_chunks
    pages

"""




import os
import re
import json
import fitz
import pandas as pd
import pypdfium2 as pdfium

# ==========================================================
# CONFIGURATION
# ==========================================================
FILE_NAME = "AXI_SPEC"
PDF_PATH = r"/home/eng-6899/Downloads/IHI0022L_amba_axi_protocol_spec.pdf"

OUTPUT_DIR = "AXI_SPEC_OUTPUT"

PAGE_FOLDER = os.path.join(OUTPUT_DIR, "pages")
IMAGE_FOLDER = os.path.join(OUTPUT_DIR, "images")
TABLE_FOLDER = os.path.join(OUTPUT_DIR, "tables")
FIGURE_FOLDER = os.path.join(OUTPUT_DIR, "figures")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PAGE_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(TABLE_FOLDER, exist_ok=True)
os.makedirs(FIGURE_FOLDER, exist_ok=True)

# ==========================================================
# REGEX PATTERNS
# ==========================================================

# ==========================================================
# REGEX PATTERNS
# ==========================================================

SECTION_REGEX = re.compile(
    # r'^(\d+(?:\.\d+)*)\s+(.+)$'
    r'^(A\d+(?:\.\d+)*|B\d+(?:\.\d+)*|C\d+(?:\.\d+)*)\s+(.+)$'
)

FIGURE_REGEX = re.compile(
    r'(Figure|Fig\.?)\s+([A-Za-z]?\d+(?:[-.]\d+)*)',
    re.IGNORECASE
)

TABLE_REGEX = re.compile(
    r'(Table)\s+([A-Za-z]?\d+(?:[-.]\d+)*)',
    re.IGNORECASE
)

REQ_ID_REGEX = re.compile(
    r'([A-Z_]*REQ[-_]?\d+)',
    re.IGNORECASE
)

REQUIREMENT_REGEX = re.compile(
    r'\b('
    r'shall|must|must not|will|should|'
    r'required to|may not|is prohibited|'
    r'remains asserted|remain asserted|'
    r'indicates that|can be sent|'
    r'must be ordered|'
    r'can only be|'
    r'is returned|'
    r'is issued|'
    r'is generated|'
    r'is valid only when'
    r')\b',
    re.IGNORECASE
)

NOTE_REGEX = re.compile(
    r'^(NOTE|WARNING|CAUTION|IMPORTANT|ASSUMPTION)\b',
    re.IGNORECASE
)

ACRONYM_REGEX = re.compile(
    r'\b([A-Z]{2,10})\b'
)

SECTION_REF_REGEX = re.compile(
    r'Section\s+\d+(\.\d+)*',
    re.IGNORECASE
)

FIGURE_REF_REGEX = re.compile(
    r'Figure\s+[A-Za-z]?\d+(?:[-.]\d+)*',
    re.IGNORECASE
)

TABLE_REF_REGEX = re.compile(
    r'Table\s+[A-Za-z]?\d+(?:[-.]\d+)*',
    re.IGNORECASE
)


def extract_document_metadata(pdf):

    metadata = pdf.metadata or {}

    return {
        "title": metadata.get("title"),
        "author": metadata.get("author"),
        "subject": metadata.get("subject"),
        "keywords": metadata.get("keywords"),
        "creator": metadata.get("creator"),
        "producer": metadata.get("producer"),
        "creation_date": metadata.get("creationDate"),
        "modification_date": metadata.get("modDate")
    }

# ==========================================================
# PAGE SCREENSHOTS
# ==========================================================

def save_page_screenshots(pdf_path, output_folder, scale=3):

    pdf = pdfium.PdfDocument(pdf_path)

    print("\nSaving page screenshots...")

    for i in range(len(pdf)):

        page = pdf[i]

        bitmap = page.render(scale=scale)

        image = bitmap.to_pil()

        output_path = os.path.join(
            output_folder,
            f"page_{i+1:03}.png"
        )

        image.save(output_path)

        print("Saved:", output_path)

# ==========================================================
# IMAGE EXTRACTION
# ==========================================================

def extract_images(pdf):

    image_records = []

    image_counter = 1

    print("\nExtracting embedded images...")

    for page_num in range(len(pdf)):

        page = pdf[page_num]

        images = page.get_images(full=True)

        for img in images:

            xref = img[0]

            try:

                base_image = pdf.extract_image(xref)

                image_bytes = base_image["image"]

                ext = base_image["ext"]

                filename = (
                    f"image_{image_counter:04}.{ext}"
                )

                filepath = os.path.join(
                    IMAGE_FOLDER,
                    filename
                )

                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                image_records.append({
                    "page": page_num + 1,
                    "file": filepath
                })

                image_counter += 1

            except Exception as e:
                print("Image extraction error:", e)

    return image_records

# ==========================================================
# TABLE EXTRACTION
# ==========================================================

def extract_tables(page, page_num):

    tables_found = []

    try:

        tables = page.find_tables()

        for idx, table in enumerate(tables.tables):

            try:

                extracted = table.extract()

                if not extracted:
                    continue

                df = pd.DataFrame(extracted)

                csv_name = (
                    f"table_p{page_num+1}_{idx+1}.csv"
                )

                csv_path = os.path.join(
                    TABLE_FOLDER,
                    csv_name
                )

                df.to_csv(csv_path, index=False)

                tables_found.append({
                    "page": page_num + 1,
                    "csv_file": csv_path
                })

            except Exception as e:
                print(
                    f"Table extraction error page {page_num+1}:",
                    e
                )

    except Exception:
        pass

    return tables_found

# ==========================================================
# TEXT ANALYSIS
# ==========================================================

# def extract_headings_from_layout(layout):

#     headings = []

#     for block in layout.get("blocks", []):

#         if block.get("type") != 0:
#             continue

#         for line in block.get("lines", []):

#             spans = line.get("spans", [])

#             if not spans:
#                 continue

#             text = "".join(
#                 span["text"]
#                 for span in spans
#             ).strip()

#             if not text:
#                 continue

#             max_font = max(
#                 span["size"]
#                 for span in spans
#             )

#             if max_font >= 14:

#                 match = SECTION_REGEX.match(text)

#                 if match:

#                     headings.append({
#                         "section_id": match.group(1),
#                         "title": match.group(2),
#                         "font_size": max_font
#                     })

#     return headings

def extract_headings_from_layout(layout):

    headings = []

    for block in layout.get("blocks", []):

        if block.get("type") != 0:
            continue
        
        for line in block.get("lines", []):
            spans = line.get("spans", [])

            if not spans:
                continue
            text = "".join(
                span["text"]
                for span in spans
            ).strip()

            if not text:
                continue

            match = SECTION_REGEX.match(text)

            if match:
                headings.append({
                    "section_id": match.group(1),
                    "title": match.group(2),
                    "font_size": max(span["size"] for span in spans)
                })
    return headings


def classify_requirement(text):

    lower = text.lower()

    if any(x in lower for x in [
        "latency",
        "throughput",
        "timing",
        "frequency",
        "bandwidth"
    ]):
        return "Performance"

    if any(x in lower for x in [
        "voltage",
        "current",
        "power"
    ]):
        return "Electrical"

    if any(x in lower for x in [
        "temperature",
        "humidity"
    ]):
        return "Environmental"

    if any(x in lower for x in [
        "safety",
        "hazard",
        "fault"
    ]):
        return "Safety"

    if any(x in lower for x in [
        "interface",
        "spi",
        "uart",
        "i2c",
        "can"
    ]):
        return "Interface"

    return "Functional"


def extract_requirements(text, section_id=None):

    requirements = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if REQUIREMENT_REGEX.search(line):

            req_match = REQ_ID_REGEX.search(line)

            req_id = (
                req_match.group(1)
                if req_match
                else None
            )

            requirements.append({

                "id": req_id,

                "section": section_id,

                "category":
                    classify_requirement(line),

                "text": line
            })

    return requirements

def extract_notes(text):

    notes = []

    for line in text.splitlines():

        line = line.strip()

        if NOTE_REGEX.match(line):

            kind = line.split(":")[0].upper()

            notes.append({
                "type": kind,
                "text": line
            })

    return notes


def extract_acronyms(text):

    found = set()

    for match in ACRONYM_REGEX.finditer(text):

        word = match.group(1)

        if len(word) > 1:
            found.add(word)

    return sorted(found)


def extract_cross_references(text):

    refs = []

    refs.extend(
        SECTION_REF_REGEX.findall(text)
    )

    refs.extend(
        FIGURE_REF_REGEX.findall(text)
    )

    refs.extend(
        TABLE_REF_REGEX.findall(text)
    )

    return refs



def build_section_tree(headings):

    sections = []

    for h in headings:

        sid = h["section_id"]

        parent = None

        if "." in sid:
            parent = sid.rsplit(".", 1)[0]

        sections.append({

            "id": sid,

            "title": h["title"],

            "parent": parent
        })

    return sections


def create_semantic_chunk(
    page_num,
    section,
    text
):

    return {

        "page": page_num,

        "section": section,

        "text": text
    }




def extract_figure_captions(text):

    figures = []

    for line in text.splitlines():

        line = line.strip()

        if FIGURE_REGEX.match(line):

            figures.append({
                "caption": line
            })

    return figures


def extract_table_captions(text):

    tables = []

    for line in text.splitlines():

        line = line.strip()

        if TABLE_REGEX.match(line):

            tables.append({
                "caption": line
            })

    return tables

# ==========================================================
# MAIN PARSER
# ==========================================================

def parse_pdf(pdf_path):

    pdf = fitz.open(pdf_path)

    # save_page_screenshots(
    #     pdf_path,
    #     PAGE_FOLDER
    # )

    image_records = extract_images(pdf)

    document = {

    "document_name":
        os.path.basename(pdf_path),

    "metadata":
        extract_document_metadata(pdf),

    "total_pages":
        len(pdf),

    "sections": [],

    "requirements": [],

    "figures": [],

    "tables": [],

    "notes": [],

    "acronyms": [],

    "cross_references": [],

    "semantic_chunks": [],

    "pages": []
}

    print("\nProcessing pages...")

    current_section = None

    for page_num in range(len(pdf)):

        page = pdf[page_num]

        layout = page.get_text("dict")
        text = page.get_text("text")

        headings = extract_headings_from_layout(
            layout
        )

        # current_section = None

        if headings:
            current_section = (
                headings[-1]["section_id"]
            )

        requirements = extract_requirements(
            text,
            current_section
        )

        notes = extract_notes(text)

        acronyms = extract_acronyms(text)

        cross_refs = extract_cross_references(
            text
        )

        figures = extract_figure_captions(text)

        table_captions = extract_table_captions(text)

        extracted_tables = extract_tables(
            page,
            page_num
        )

        page_images = [
            img
            for img in image_records
            if img["page"] == page_num + 1
        ]

        page_json = {
            "page_number":
                page_num + 1,

            "text":
                text,

            "headings":
                headings,

            "requirements":
                requirements,

            "figures":
                figures,

            "table_captions":
                table_captions,

            "tables":
                extracted_tables,

            "images":
                page_images
        }
        document["requirements"].extend(
            requirements
        )

        document["notes"].extend(
            notes
        )

        document["acronyms"].extend(
            acronyms
        )

        document["cross_references"].extend(
            cross_refs
        )

        document["figures"].extend(
            figures
        )

        document["tables"].extend(
            extracted_tables
        )

        document["semantic_chunks"].append(
            create_semantic_chunk(
                page_num + 1,
                current_section,
                text
            )
        )
        document["pages"].append(
            page_json
        )

        print(
            f"Processed page {page_num+1}/{len(pdf)}"
        )

    json_path = os.path.join(
        OUTPUT_DIR,
        "document.json"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as f:
        all_headings = []

        for page in document["pages"]:

            all_headings.extend(
                page["headings"]
            )

        document["sections"] = (
            build_section_tree(
                all_headings
            )
        )

        document["acronyms"] = sorted(
            set(document["acronyms"])
        )
        json.dump(
            document,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\n===================================")
    print("PARSING COMPLETE")
    print("===================================")
    print("JSON:", json_path)
    print("Pages:", PAGE_FOLDER)
    print("Images:", IMAGE_FOLDER)
    print("Tables:", TABLE_FOLDER)

# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    parse_pdf(PDF_PATH)