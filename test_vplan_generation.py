import json

with open("AXI_SPEC_OUTPUT/document.json", "r") as f:
    doc = json.load(f)

print("\n===== VPLAN CANDIDATES =====\n")

for fig in doc["figures"]:
    hints = fig.get("visual_requirement_hints", [])

    if len(hints) == 0:
        continue

    print("Feature:")
    print(" ", fig["caption"])

    print("Section:")
    print(" ", fig["section"])

    print("Coverage keywords:")
    print(" ", hints)

    print("Verification idea:")

    if "HANDSHAKE" in hints:
        print(" Verify protocol handshake timing.")

    if "RESET" in hints:
        print(" Verify reset behaviour.")

    if "READ" in hints:
        print(" Verify read transaction.")

    if "WRITE" in hints:
        print(" Verify write transaction.")

    if "TRANSFER" in hints:
        print(" Verify transfer ordering.")

    print("-" * 60)
