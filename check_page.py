import json
import sys

with open("RISC_SPEC_OUTPUT/document.json", encoding="utf-8") as f:
    data = json.load(f)

page = int(sys.argv[1])

found = False

for req in data["requirements"]:
    if req.get("source_page") == page:
        found = True
        print("=" * 80)
        print(req["id"])
        print(req["text"])

if not found:
    print(f"No requirements found on page {page}")