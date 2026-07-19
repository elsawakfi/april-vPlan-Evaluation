import json

with open("AXI_SPEC_OUTPUT/document.json", encoding="utf-8") as f:
    data = json.load(f)

page = int(input("Page: "))

for req in data["requirements"]:
    if req["source_page"] == page:
        print(req["id"], "-", req["text"])