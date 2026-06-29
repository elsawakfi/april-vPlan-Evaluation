import json
import csv

with open("AXI_SPEC_OUTPUT/document.json", "r", encoding="utf-8") as f:
    doc = json.load(f)

rows = []

import re

def clean_spacing(text):
    if not isinstance(text, str):
        return text

    fixes = {
        "toit": "to it",
        "RVALIDto": "RVALID to",
        "VerifyVALID": "Verify VALID",
        "withREADY": "with READY",
        "creditavailable": "credit available",
        "andcheck": "and check",
        "theextracted": "the extracted",
        "extractedAXI": "extracted AXI",
        "therequired": "the required",
        "checkrequired": "check required",
        "andcheck": "and check"
    }

    for bad, good in fixes.items():
        text = text.replace(bad, good)

    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def make_vplan_row(req):
    text = clean_spacing(req["text"])
    lower = text.lower()

    if "valid" in lower and "ready" in lower:
        feature = "VALID/READY handshake"
        objective = "Verify VALID/READY handshake ordering and transfer completion."
        test_idea = "Drive VALID and READY in different orderings and check transfer only completes when both are asserted."
        coverage = "VALID before READY, READY before VALID, VALID with READY"

    elif "reset" in lower:
        feature = "Reset behaviour"
        objective = "Verify required signals are correctly deasserted during and after reset."
        test_idea = "Apply reset and check required signals remain deasserted until the required ACLK edge."
        coverage = "Reset asserted, reset deassertion, post-reset signal state"

    elif "credit" in lower:
        feature = "Credited transport"
        objective = "Verify transfers obey credit availability."
        test_idea = "Run transactions with zero, one, and multiple credits and check VALID behaviour."
        coverage = "Zero credits, credit available, credit consumed"

    elif "write" in lower:
        feature = "Write transaction"
        objective = "Verify write-channel protocol requirements."
        test_idea = "Run directed write transfers and check AW/W/B channel ordering."
        coverage = "AWVALID, WVALID, BVALID, BREADY"

    elif "read" in lower:
        feature = "Read transaction"
        objective = "Verify read-channel protocol requirements."
        test_idea = "Run directed read transfers and check AR/R channel ordering."
        coverage = "ARVALID, ARREADY, RVALID, RREADY"

    else:
        feature = "General AXI protocol rule"
        objective = "Verify the extracted AXI requirement is satisfied."
        test_idea = "Create a directed protocol test based on the requirement text."
        coverage = "Requirement covered"

    return {
        "feature": clean_spacing(feature),
        "source_section": req["section"],
        "requirement_text": clean_spacing(text),
        "verification_objective": clean_spacing(objective),
        "test_idea": clean_spacing(test_idea),
        "coverage": clean_spacing(coverage),
        "priority": "Medium"
    }

# for req in doc.get("requirements", []):
#     rows.append(make_vplan_row(req))

important_keywords = [
    "valid", "ready", "reset", "write", "read",
    "credit", "transfer", "response", "address", "data"
]

for req in doc.get("requirements", []):
    text = req.get("text", "").lower()

    if any(k in text for k in important_keywords):
        rows.append(make_vplan_row(req))

for row in rows:
    for key in row:
        if isinstance(row[key], str):
            row[key] = clean_spacing(row[key])

# with open("vplan_from_requirements.csv", "w", newline="", encoding="utf-8") as f:
#     writer = csv.DictWriter(f, fieldnames=[
#         "feature",
#         "source_section",
#         "requirement_text",
#         "verification_objective",
#         "test_idea",
#         "coverage",
#         "priority"
#     ])

with open("vplan_from_requirements.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "feature",
        "source_section",
        "requirement_text",
        "verification_objective",
        "test_idea",
        "coverage",
        "priority"
    ])

    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} vPlan rows in vplan_from_requirements.csv")
