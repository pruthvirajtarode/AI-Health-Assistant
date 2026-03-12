import json

with open("concepts.json", "r", encoding="utf-8") as f:
    data = json.load(f)  # load as normal JSON array

with open("concepts.jsonl", "w", encoding="utf-8") as f:
    for obj in data:
        f.write(json.dumps(obj) + "\n")
