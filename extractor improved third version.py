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
    figures        <-- now includes "file" path to clipped PNG in /figures/
    tables
    notes
    acronyms
    cross_references
    semantic_chunks  <-- now section-level, not page-level
    pages
"""
from email.mime import text
import random as rand
import os
from random import random
import re
import json
import fitz
import pandas as pd
import pypdfium2 as pdfium
import pytesseract
from PIL import Image
# ==========================================================
# CONFIGURATION
# ==========================================================
FILE_NAME = "amba_axi_protocol_spec.pdf"
PDF_PATH = r"/home/eng-6899/Downloads/IHI0022L_amba_axi_protocol_spec.pdf"

OUTPUT_DIR = "AXI_SPEC_OUTPUT"

PAGE_FOLDER   = os.path.join(OUTPUT_DIR, "pages")
IMAGE_FOLDER  = os.path.join(OUTPUT_DIR, "images")
TABLE_FOLDER  = os.path.join(OUTPUT_DIR, "tables")
FIGURE_FOLDER = os.path.join(OUTPUT_DIR, "figures")   # was created but never written to — now used

os.makedirs(OUTPUT_DIR,   exist_ok=True)
os.makedirs(PAGE_FOLDER,  exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(TABLE_FOLDER, exist_ok=True)
os.makedirs(FIGURE_FOLDER,exist_ok=True)

# ==========================================================
# REGEX PATTERNS
# ==========================================================

# FIX 1 — SECTION_REGEX
# ORIGINAL only matched appendix-style IDs: A1, B2.3, C4.1.2
#   r'^(A\d+(?:\.\d+)*|B\d+(?:\.\d+)*|C\d+(?:\.\d+)*)\s+(.+)$'
# The AXI spec body uses numeric sections like 1, 2.3, 4.1.2.
# Appendix sections use A4, B1.2 etc.
# FIX: accept leading digits OR a single A/B/C letter followed by digits,
#      covering both body sections and appendices in one pattern.
SECTION_REGEX = re.compile(
    r'^((?:\d+(?:\.\d+)*|[A-C]\d+(?:\.\d+)*))\s+(.+)$'
)

FIGURE_CAPTION_REGEX = re.compile(
    r'^Figure\s+[A-Za-z]?\d+(?:\.\d+)*\s*:',
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

FEATURE_REGEX = re.compile(
    r'\b('
    r'to transfer|'
    r'permits|'
    r'supports|'
    r'provides|'
    r'contains|'
    r'uses|'
    r'can either|'
    r'can pass|'
    r'requires that|'
    r'perform'
    r')\b',
    re.IGNORECASE
)

REQUIREMENT_REGEX = re.compile(
    r'\b('
    #strong obligations / prohubitions
    r'shall|shall not|'
    r'must|must not|'
    r'must have|must not have|must be|must not be|'
    r'must issue|must not issue|'
    r'length can be|'
    r'can discard|'
    r'must complete|must not complete|'
    r'must be consistent|'
    r'must not cross|'
    r'should|should not|'
    r'cannot|can not|'
    r'can omit|'
    r'is required to|are required to|required to|'
    r'is prohibited|are prohibited|prohibited to|'
    r'is not allowed to|are not allowed to|not allowed to|'
    r'is not permitted to|are not permitted to|not permitted to|'
    r'are non-modifiable| is non-modifiable|'
    r'are nonmodifiable| is nonmodifiable|'
    r'is not present|are not present|'
    r'must be able to|must be given|'
    r'is issued|are issued|'
    r'is sent|are sent|'
    r'is determined|are determined|'
    r'is returned|are returned|'
    r'returns|'

    #Timing / protocol behaviour
    r'must remain|shall remain|remain asserted|remains asserted|'
    r'must be held|must be stable|'
    r'must be stable|shall be stable|remain stable|'
    r'shall be asserted|must be asserted|'
    r'shall be deasserted|must be deasserted|'

    #Validity / legality constraints
    r'is valid only when|are valid only when|'
    r'is only valid|are only valid|'
    r'can only be|may only be|'
    r'is not satisfied|are not satisfied|'
    r'is satisfied|are satisfied|'

    #Optional / supported behaviour 
    r'is not supported|are not supported|'
    r'is supported|are supported|'
    r'is optional|are optional|'

    #Legal values / bounds
    r'can be lower than|can be higher than|'
    r'can be up to|may be up to|'
    r'can range from|may range from|'
    r'can be obtained|'

    #Spec-specific but common protocol phrasing
    r'early termination of .* not supported|' # .* means anything in between.
    r'is half that specified by|'
    r'is determined from|'

    #extra keywords
    r'permitted to|is permitted to|are permitted to|'
    r'is permitted|are permitted|'
    r'allowed to|is allowed to|are allowed to|'
    r'can be asserted|can be deasserted|'
    r'may be asserted|may be deasserted|'
    r'may not'
    
    
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

# FIX 2 — SECTION_REF_REGEX capturing group
# ORIGINAL had a capturing group (\.\d+)* inside the pattern:
#   r'Section\s+\d+(\.\d+)*'
# re.findall() returns the CONTENTS of capturing groups, not the full match.
# So "Section 2.3" would return [".3"] instead of ["Section 2.3"].
# FIX: make the repeated group non-capturing with (?:...) so findall
#      returns the whole match string.
SECTION_REF_REGEX = re.compile(
    r'Section\s+\d+(?:\.\d+)*',
    re.IGNORECASE
)

# These two were already correct (no capturing groups), left unchanged.
FIGURE_REF_REGEX = re.compile(
    r'Figure\s+[A-Za-z]?\d+(?:[-.]\d+)*',
    re.IGNORECASE
)

TABLE_REF_REGEX = re.compile(
    r'Table\s+[A-Za-z]?\d+(?:[-.]\d+)*',
    re.IGNORECASE
)

pattern = re.compile(
    r'(0b[01]+)\s+'
    r'([A-Za-z][A-Za-z0-9_-]*)\s+'
    r'(.*?)'
    r'(?='
        r'\s+0b[01]+\s+[A-Za-z][A-Za-z0-9_-]*\s+'
        r'|'
        r'\s+(?:\d+(?:\.\d+)*|[A-C]\d+(?:\.\d+)*)\s+'
        r'|'
        r'\s+Table\s+[A-Za-z]?\d+'
        r'|$'
    r')',
    re.DOTALL
)


# ==========================================================
# ACRONYM STOPLIST
# FIX 3 — Acronym noise
# ORIGINAL had no stoplist, so common English uppercase words
# (AND, THE, FOR, WITH…) and single-letter abbreviations were
# included as "acronyms". Added a stoplist of common false positives.
# ==========================================================
ACRONYM_STOPLIST = {
    "THE", "AND", "FOR", "WITH", "FROM", "THIS", "THAT",
    "ARE", "NOT", "BUT", "ITS", "ALL", "ANY", "CAN",
    "HAS", "HAVE", "BEEN", "WILL", "MAY", "SHALL", "MUST",
    "WHEN", "THEN", "EACH", "SUCH", "BOTH", "ALSO", "INTO",
    "OVER", "UPON", "USED", "ONLY", "MORE", "THAN", "BEEN",
    "WHICH", "THERE", "THEIR", "THESE", "THOSE", "WHAT",
    "PAGE", "NOTE", "TYPE", "DATA", "BASE", "TRUE", "FALSE"
}

# ==========================================================
# METADATA
# ==========================================================

def extract_document_metadata(pdf):
    metadata = pdf.metadata or {}
    return {
        "title":             metadata.get("title"),
        "author":            metadata.get("author"),
        "subject":           metadata.get("subject"),
        "keywords":          metadata.get("keywords"),
        "creator":           metadata.get("creator"),
        "producer":          metadata.get("producer"),
        "creation_date":     metadata.get("creationDate"),
        "modification_date": metadata.get("modDate")
    }


# ==========================================================
# PAGE SCREENSHOTS  (unchanged, still optional)
# ==========================================================

def save_page_screenshots(pdf_path, output_folder, scale=3):
    pdf = pdfium.PdfDocument(pdf_path)
    print("\nSaving page screenshots...")
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        output_path = os.path.join(output_folder, f"page_{i+1:03}.png")
        image.save(output_path)
        print("Saved:", output_path)

# ==========================================================
# HEADING EXTRACTION
# ==========================================================

def remove_detected_headings(text, headings):
    clean_text = text

    for h in headings:
        title = h.get("title", "").strip()
        section_id = h.get("section_id", "").strip()

        if section_id:
            clean_text = re.sub(
                rf'^\s*{re.escape(section_id)}\s+.*$',
                '',
                clean_text,
                flags=re.MULTILINE
            )

        if title:
            clean_text = re.sub(
                rf'^\s*{re.escape(title)}\s*$',
                '',
                clean_text,
                flags=re.MULTILINE
            )

    return clean_text

# ==========================================================
# IMAGE EXTRACTION  (raster/embedded images — unchanged)
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
                filename = f"image_{image_counter:04}.{ext}"
                filepath = os.path.join(IMAGE_FOLDER, filename)
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
# FIGURE REGION EXTRACTION
# FIX 4 — Vector figures were completely ignored.
# The AXI spec draws timing diagrams and channel diagrams using
# PDF vector commands, not embedded image xrefs, so extract_images()
# misses them entirely.  FIGURE_FOLDER was also created but never
# written to.
#
# This function searches each page for the caption text we already
# found, locates its bounding box, then renders and saves the page
# region directly above the caption (where the figure sits).
# The saved PNG path is stored back into the caption dict as "file"
# so the JSON has a complete figure record.
#
# clip_height_pt controls how many PDF points above the caption
# baseline are captured (default 220 ≈ ~3 inches at 72dpi, enough
# for most AXI diagrams).  Increase if tall figures are clipped.
# ==========================================================

def extract_figure_regions(
    pdf_page,
    page_num,
    captions,
    output_folder,
    scale=4,
    clip_height_pt=120,
    margin=12
):
    """
    For each caption dict in `captions`, search the page for that
    caption string, clip the region above it, render at `scale`x,
    and save to `output_folder`.  The dict is updated in-place with
    a "file" key containing the saved PNG path.
    """
    full_rect = pdf_page.rect
    drawings = pdf_page.get_drawings()

    for idx, cap in enumerate(captions):
        caption_text = cap.get("caption", "")

        # search_for returns a list of fitz.Rect hit boxes
        hits = pdf_page.search_for(caption_text)
        if not hits:
            # Caption text not found verbatim on page — skip clipping
            # but still record that no file was produced
            cap["file"] = None
            continue

        cap_rect = hits[0]   # use first (topmost) hit

        # Build clip rect: full page width, from `clip_height_pt`
        # above the caption top down to the caption top.
        # Clamped to the page top so we never go negative.
        clip_rect = fitz.Rect(
            full_rect.x0,
            max(full_rect.y0, cap_rect.y0 - clip_height_pt),
            full_rect.x1,
            cap_rect.y0
        )

        search_rect = fitz.Rect(
            full_rect.x0,
            max(full_rect.y0, cap_rect.y0 - clip_height_pt),
            full_rect.x1,
            cap_rect.y0
        )

        visual_rects = []
        for drawing in drawings:
            r = drawing.get("rect")
            if r and r.intersects(search_rect):
                visual_rects.append(r & search_rect)

        if visual_rects:
            clip_rect = search_rect

        mat = fitz.Matrix(scale, scale)
        pixmap = pdf_page.get_pixmap(matrix=mat, clip=clip_rect)

        # Build a safe filename from the caption
        safe_caption = re.sub(r'[^\w\-]', '_', caption_text)[:40]
        filename = f"figure_p{page_num+1}_{idx+1}_{safe_caption}.png"
        filepath = os.path.join(output_folder, filename)

        pixmap.save(filepath)
        cap["file"] = filepath    # link caption record → image file

    return captions   # list updated in-place, returned for clarity


# ==========================================================
# OCR FUNCTIONS
# ==========================================================

def ocr_image_file(image_path):

    if not image_path or not os.path.exists(image_path):
        return ""

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()

    except Exception as e:
        print("OCR error:", e)
        return ""


# ==========================================================
# TABLE EXTRACTION  (unchanged)
# ==========================================================

def extract_tables(page, page_num, section_id=None):
    tables_found = []
    table_requirements = []
    try:
        tables = page.find_tables()
        for idx, table in enumerate(tables.tables):
            try:
                extracted = table.extract()
                if not extracted:
                    continue

                df = pd.DataFrame(extracted)
                csv_name = f"table_p{page_num+1}_{idx+1}.csv"
                csv_path = os.path.join(TABLE_FOLDER, csv_name)
                df.to_csv(csv_path, index=False)
                tables_found.append({
                    "page":     page_num + 1,
                    "csv_file": csv_path
                })
                
                for row in extracted:
                    cells = [
                        str(cell).replace("\n", " ").strip()
                        for cell in row
                        if cell and str(cell).strip()
                    ]

                    if len(cells) < 2:
                        continue

                    row_text = " ".join(cells)
    
                    if REQUIREMENT_REGEX.search(row_text) or FEATURE_REGEX.search(row_text):
                        table_requirements.append(
                            make_requirement(
                                None,
                                row_text,
                                section_id,
                                "table_requirement"
                            )
                        )

            except Exception as e:
                print(f"Table extraction error page {page_num+1}:", e)
    except Exception:
        pass
    return tables_found, table_requirements


def extract_encoding_table_requirements(text, section_id=None):
    requirements = []

    pattern = re.compile(
    r'(0b[01]+)\s+'
    r'([A-Za-z][A-Za-z0-9_-]*)\s+'
    r'(.*?)'
    r'(?='
        r'\s+0b[01]+\s+[A-Za-z][A-Za-z0-9_-]*\s+'
        # r'|\s+(?:\d+(?:\.\d+)*|[A-C]\d+(?:\.\d+)*)\s+'
        r'|\s+Table\s+[A-Za-z]?\d+(?:\.\d+)*'
        r'|\s+ARM IHI'
        r'|$'
    r')',
    re.DOTALL
    )

    for code, operation, meaning in pattern.findall(text):
        # meaning = " ".join(meaning.split())

        meaning = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', meaning)
        meaning = re.sub(r'\s+', ' ', meaning).strip()

        if REQUIREMENT_REGEX.search(meaning) or FEATURE_REGEX.search(meaning):
 
            section = str(section_id).replace(".", "_")
            req_id = f"REQ_{section}_{len(requirements)+1:03}"

            requirements.append(
                make_requirement(
                    req_id,
                    f"{code} | {operation} | {meaning}",
                    section_id,
                    "encoding_rule"
                )
            )
    return requirements

# ==========================================================
# TEXT ANALYSIS
# ==========================================================

def is_chapter_cover_page(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    if lines and re.match(r'^Chapter\s+[A-Z]\d+', lines[0]):
        if len(lines) > 1 and not lines[1].startswith("A"):
            if sum(
                bool(re.match(r'^•?\s*A\d+\.\d+', l))
                for l in lines
            ) >= 3:
                return True
    return False


def extract_headings_from_layout(layout):
    """
    Walk every text span in the page layout dict.
    A line is a heading if it matches SECTION_REGEX (now fixed to
    catch numeric sections like "2.3 Channel Signals").
    Font-size guard removed — the regex is specific enough that
    false positives are unlikely, and some AXI headings use body-
    size fonts in the appendix.
    """
    headings = []
    for block in layout.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(span["text"] for span in spans).strip()
            if re.search(r'\.{3,}\s*\d+$', text):
                continue
            
            if re.fullmatch(r'\d+', text):
                continue

            if not text:
                continue
            match = SECTION_REGEX.match(text)
            if match:
                sid = match.group(1)

                if not re.match(r'^[A-C]\d+(?:\.\d+)*$', sid):
                    continue

                headings.append({
                    "section_id": sid,
                    "title": match.group(2),
                    "font_size": max(span["size"] for span in spans)
                })
    return headings


def classify_requirement(text):
    lower = text.lower()
    if any(x in lower for x in ["latency", "throughput", "timing",
                                  "frequency", "bandwidth"]):
        return "Performance"
    if any(x in lower for x in ["voltage", "current", "power"]):
        return "Electrical"
    if any(x in lower for x in ["temperature", "humidity"]):
        return "Environmental"
    if any(x in lower for x in ["safety", "hazard", "fault"]):
        return "Safety"
    if any(x in lower for x in ["interface", "spi", "uart", "i2c", "can"]):
        return "Interface"
    return "Functional"



def extract_signals(text):
    return sorted(set(re.findall(r'\b[A-Z][A-Z0-9_]{2,}\b', text)))


def make_requirement(req_id, text, section_id, category):
    return {
        "id": req_id,
        "text": text,
        "source_section": section_id,
        "signals": extract_signals(text),
        "type": category
    }

def extract_requirements(text, section_id=None):
    requirements = []

    lines = [
        line for line in text.splitlines()
        if not re.match(r'^\s*(Figure|Table)\s+', line, re.IGNORECASE)
    ]

    text = "\n".join(lines)

    clean_text = " ".join(text.split())

    clean_text = re.sub(
        r'Figure\s+[A-Za-z]?\d+(?:\.\d+)*:\s*[^\n.]*',
        '',
        clean_text,
        flags=re.IGNORECASE
    )

    clean_text = re.sub(
        r'(?:\b\d+\s+){3,}[A-Z][A-Z\s]{10,}',
        '',
        clean_text
    )

    sentences = re.split(r'(?=•)|(?<=[.!?])\s+', clean_text)

    for line in sentences:
        line = line.strip()

        line = re.sub(
            r'^(?:[A-C]\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z ]{2,40}\s+(?=(It|If|For|When|The|A|An)\b)',
            '',
            line
        ).strip()

        line = re.sub(r'^•\s*', '', line)

        line = re.sub(
            r'^.*?The required behavior .*?:\s*',
            '',
            line,
            flags=re.IGNORECASE
        )

        if not line:
            continue
        
        if re.match(r'^[A-Z][A-Za-z ]+\s+[A-C]\d+(?:\.\d+)*\.?$', line):
            continue

        if re.match(r'^Chapter\s+[A-Z]\d+\.?$', line):
            continue

        if line.startswith("ARM IHI"):
            continue

        if "Copyright" in line:
            continue

        if line == "All rights reserved.":
            continue

        if re.match(r'^Non-confidential\s+\d+$', line):
            continue

        if line.startswith("See "):
            continue

        if line.lower().startswith("however,"):
            continue

        if REQUIREMENT_REGEX.search(line) or FEATURE_REGEX.search(line):
            req_match = REQ_ID_REGEX.search(line)
            # req_id = req_match.group(1) if req_match else None

            section = str(section_id).replace(".", "_")
            req_id = f"REQ_{section}_{len(requirements)+1:03}"

            requirements.append(
                make_requirement(
                    req_id,
                    line,
                    section_id,
                    "protocol_rule"
                )
            )

    return requirements

def extract_notes(text):
    notes = []
    for line in text.splitlines():
        line = line.strip()
        if NOTE_REGEX.match(line):
            kind = line.split(":")[0].upper()
            notes.append({"type": kind, "text": line})
    return notes


def extract_acronyms(text):
    """
    FIX 3 applied here: after collecting uppercase tokens we filter
    against ACRONYM_STOPLIST to remove common English words that
    happen to be all-caps (THE, AND, FOR, etc.).
    """
    found = set()
    for match in ACRONYM_REGEX.finditer(text):
        word = match.group(1)
        # len > 1 was the original guard; we strengthen it to > 1
        # AND not in the stoplist.
        if len(word) > 1 and word not in ACRONYM_STOPLIST:
            found.add(word)
    return sorted(found)


def extract_cross_references(text):
    """
    FIX 2 applied here.
    ORIGINAL used SECTION_REF_REGEX with a capturing group, so
    findall returned partial strings like ".3" instead of
    "Section 2.3".  Now that the regex is non-capturing, findall
    correctly returns the full matched strings.
    """
    refs = []
    refs.extend(SECTION_REF_REGEX.findall(text))   # now returns full match
    refs.extend(FIGURE_REF_REGEX.findall(text))
    refs.extend(TABLE_REF_REGEX.findall(text))
    return refs


def build_section_tree(headings):
    sections = []
    for h in headings:
        sid = h["section_id"]
        parent = sid.rsplit(".", 1)[0] if "." in sid else None
        sections.append({
            "id":     sid,
            "title":  h["title"],
            "parent": parent
        })
    return sections


# ==========================================================
# SEMANTIC CHUNKS — rebuilt as section-level, not page-level
# FIX 5 — ORIGINAL appended one chunk per page using
#   create_semantic_chunk(page_num, current_section, text)
# This means a single section spanning 4 pages created 4 separate
# chunks, fragmenting the content.  The improved version below
# groups text by section across all pages so each chunk represents
# a complete section's prose, which is far more useful for RAG /
# embedding pipelines.
#
# Called once after all pages are processed (see parse_pdf).
# ==========================================================

def build_semantic_chunks(pages):
    """
    Walk the already-processed page list and merge text by section.
    When the section changes (a new heading was detected), flush the
    current buffer as a completed chunk and start a new one.
    Pages with no heading inherit the most recent section (same
    behaviour as before, just accumulated rather than emitted).
    """
    chunks = []
    current_section = None
    buffer = []

    for page in pages:
        # If this page introduced new headings, flush the current buffer
        if page["headings"]:
            if buffer and current_section is not None:
                chunks.append({
                    "section": current_section,
                    "text":    "\n".join(buffer).strip()
                })
            buffer = []
            current_section = page["headings"][-1]["section_id"]

        buffer.append(page["text"])

    # Flush the last section
    if buffer and current_section is not None:
        chunks.append({
            "section": current_section,
            "text":    "\n".join(buffer).strip()
        })

    return chunks


# ==========================================================
# CAPTION EXTRACTORS
# ==========================================================
VALID_VPLAN_SECTION_REGEX = re.compile(
    r'^(?:[A-C]\d+(?:\.\d+)*)$'
)

def is_valid_vplan_section(section):
    if section is None:
        return False
    return VALID_VPLAN_SECTION_REGEX.match(str(section)) is not None

def extract_figure_captions(text):
    """
    Collect lines that begin with 'Figure …' or 'Fig. …'.
    Note: extract_figure_regions() is called separately in parse_pdf
    to add the "file" key to each caption dict.
    """
    figures = []
    for line in text.splitlines():
        line = line.strip()
        if FIGURE_CAPTION_REGEX.match(line):
            figures.append({"caption": line, "file": None})
    return figures

def extract_table_captions(text):
    tables = []
    for line in text.splitlines():
        line = line.strip()
        if TABLE_REGEX.match(line):
            tables.append({"caption": line})
    return tables


def extract_visual_requirement_hints(figure):
    hints = []

    caption = figure.get("caption", "")
    ocr_text = figure.get("ocr_text", "")
    combined = f"{caption}\n{ocr_text}".lower()

    keywords = [
        "valid", "ready", "reset", "aresetn", "aclk",
        "handshake", "transfer", "asserted", "deasserted",
        "stable", "high", "low", "write", "read",
        "response", "address", "data"
    ]

    for keyword in keywords:
        if keyword in combined:
            hints.append(keyword.upper())

    return sorted(set(hints))

def extract_heading_from_text(text):
    for line in text.splitlines()[:80]:
        line = line.strip()

        if not line:
            continue

        if line.lower().startswith("chapter"):
            continue

        if re.search(r'\.{3,}\s*\d+$', line):
            continue

        if re.fullmatch(r'\d+', line):
            continue

        match = SECTION_REGEX.match(line)

        if match:
            sid = match.group(1)
            title = match.group(2).strip()

            if not re.match(r'^[A-C]\d+(?:\.\d+)*$', sid):
                continue

            if len(title) < 3:
                continue

            return {
                "section_id": sid,
                "title": title,
                "font_size": None
            }

    return None

def normalize(text):
    return re.sub(r'[\W_]+', '', text).lower()
# ==========================================================
# MAIN PARSER
# ==========================================================

def parse_pdf(pdf_path):

    pdf = fitz.open(pdf_path)

    # Uncomment to also render full-page PNGs:
    # save_page_screenshots(pdf_path, PAGE_FOLDER)

    image_records = extract_images(pdf)

    document = {
        "document_name":    os.path.basename(pdf_path),
        "metadata":         extract_document_metadata(pdf),
        "total_pages":      len(pdf),
        "sections":         [],
        "requirements":     [],
        "figures":          [],
        "tables":           [],
        "notes":            [],
        "acronyms":         [],
        "cross_references": [],
        "semantic_chunks":  [],
        "pages":            []
    }

    print("\nProcessing pages...")

    current_section = None

    for page_num in range(20, len(pdf)):

        page   = pdf[page_num]
        layout = page.get_text("dict")
        text   = page.get_text("text")

        headings = extract_headings_from_layout(layout)

        text_heading = extract_heading_from_text(text)

        if text_heading:
            headings = [text_heading]

        # Fallback: detect section heading directly from page text
        if not headings:
            for line in text.splitlines()[:20]:
                line = line.strip()

                # skip chapter/page headers
                if line.lower().startswith("chapter"):
                    continue

                match = SECTION_REGEX.match(line)
                if match:
                    sid = match.group(1)

                    if not re.match(r'^[A-C]\d+(?:\.\d+)*$', sid):
                        continue

                    headings = [{
                        "section_id": sid,
                        "title": match.group(2),
                        "font_size": None
                    }]
                    break

        if headings:
            current_section = headings[-1]["section_id"]
        elif current_section is None:
            current_section = "Unknown"

        is_cover = is_chapter_cover_page(text)

        if is_cover:
            requirements = []
            table_reqs = []
        else:
            # requirements = extract_requirements(text, current_section)
            clean_text = remove_detected_headings(text, headings)
            requirements = extract_requirements(clean_text, current_section)
            table_reqs = extract_encoding_table_requirements(clean_text, current_section)

        if table_reqs:
            requirements = [
                r for r in requirements
                if not (
                    "as shown in Table" in r["text"]
                    or "Operation Meaning" in r["text"]
                    or re.match(r'^0b[01]+', r["text"])
                    or any(
                        normalize(r["text"]) in normalize(tr["text"])
                        or normalize(tr["text"]) in normalize(r["text"])
                        for tr in table_reqs
                    )
                )
            ]

        requirements.extend(table_reqs)


        notes         = extract_notes(text)
        acronyms      = extract_acronyms(text)
        cross_refs    = extract_cross_references(text)
        table_captions = extract_table_captions(text)
        extracted_tables, table_requirements = extract_tables(page, page_num, current_section)

        requirements.extend(table_requirements)

        # --- Figure captions + region clipping (FIX 4) ---
        # Step 1: find caption lines in the text
        figures = extract_figure_captions(text)

        # Step 2: for each caption, clip and save the page region
        #         above it to FIGURE_FOLDER and store the path in
        #         the caption dict under "file".
        if figures:
            extract_figure_regions(
                pdf_page=page,
                page_num=page_num,
                captions=figures,
                output_folder=FIGURE_FOLDER,
                scale=4,
                clip_height_pt=120
            )
        # --------------------------------------------------
        for fig in figures:
            fig["section"] = current_section
            fig["page"] = page_num + 1
            fig["ocr_text"] = ocr_image_file(fig.get("file"))
            fig["visual_requirement_hints"] = extract_visual_requirement_hints(fig)

        page_images = [
            img for img in image_records
            if img["page"] == page_num + 1
        ]

        page_json = {
            "page_number":   page_num + 1,
            "text":          text,
            "headings":      headings,
            "requirements":  requirements,
            "figures":       figures,          # now includes "file" key
            "table_captions": table_captions,
            "tables":        extracted_tables,
            "images":        page_images
        }

        document["requirements"].extend(requirements)
        document["notes"].extend(notes)
        document["acronyms"].extend(acronyms)
        document["cross_references"].extend(cross_refs)
        document["figures"].extend(figures)
        document["tables"].extend(extracted_tables)
        document["pages"].append(page_json)

        print(f"Processed page {page_num+1}/{len(pdf)}")

    # ----------------------------------------------------------
    # Post-processing: build section tree and semantic chunks
    # ----------------------------------------------------------

    all_headings = []
    for p in document["pages"]:
        all_headings.extend(p["headings"])
    document["sections"] = build_section_tree(all_headings)

    # FIX 5: section-level chunks built from all pages at once
    document["semantic_chunks"] = build_semantic_chunks(document["pages"])

    # Deduplicate acronyms (unchanged)
    document["acronyms"] = sorted(set(document["acronyms"]))
    

    # ----------------------------------------------------------
    # Random page checks for manual requirement validation
    # ----------------------------------------------------------

    NUM_RANDOM_CHECKS = 1

    print("\n===================================")
    print("RANDOM PAGE REQUIREMENT CHECKS")
    print("===================================")

    random_pages = rand.sample(
        document["pages"],
        min(NUM_RANDOM_CHECKS, len(document["pages"]))
    )

    for p in random_pages:
        print("\n" + "=" * 80)
        print(f"PAGE {p['page_number']}")
        print("=" * 80)

        print("\nRequirements:")
        if p["requirements"]:
            for r in p["requirements"]:
                print("-", r["text"])
        else:
            print("- None found")

        print("\nPage text preview:")
        print(p["text"][:1500])                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         

    # ----------------------------------------------------------
    # Write JSON
    # ----------------------------------------------------------

    json_path = os.path.join(OUTPUT_DIR, "document.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)

    print("\n===================================")
    print("PARSING COMPLETE")
    print("===================================")
    print("JSON:    ", json_path)
    print("Pages:   ", PAGE_FOLDER)
    print("Images:  ", IMAGE_FOLDER)
    print("Tables:  ", TABLE_FOLDER)
    print("Figures: ", FIGURE_FOLDER)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    parse_pdf(PDF_PATH)