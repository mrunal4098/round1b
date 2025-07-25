import sys, json, re, pathlib

def validate(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if "title" not in data or not isinstance(data["title"], str):
        return False, "Missing or invalid 'title'."
    if "outline" not in data or not isinstance(data["outline"], list):
        return False, "Missing or invalid 'outline' list."
    for i,item in enumerate(data["outline"]):
        if not isinstance(item, dict):
            return False, f"Outline item {i} not dict."
        if item.get("level") not in ("H1","H2","H3"):
            return False, f"Outline item {i} invalid level {item.get('level')}"
        if not isinstance(item.get("text"), str) or not item["text"].strip():
            return False, f"Outline item {i} empty text."
        if not isinstance(item.get("page"), int) or item["page"] < 1:
            return False, f"Outline item {i} invalid page."
    # Ensure only allowed top-level keys when debug disabled
    allowed = {"title","outline","_debug_candidates","_debug_first_lines"}
    extraneous = [k for k in data.keys() if k not in allowed]
    if extraneous:
        return False, f"Unexpected keys present: {extraneous}"
    return True, "OK"

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.validate_output <jsonfile>")
        sys.exit(2)
    p = pathlib.Path(sys.argv[1])
    ok,msg = validate(p)
    if ok:
        print(f"[VALID] {p.name}: {msg}")
        sys.exit(0)
    else:
        print(f"[INVALID] {p.name}: {msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
