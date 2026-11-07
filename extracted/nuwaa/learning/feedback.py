"""Learn from the user: store corrections as new training pairs in data/user_feedback.jsonl (used on next training run)."""
import json
from pathlib import Path
def add_correction(user_text: str, good_answer: str, path="data/user_feedback.jsonl"):
    Path(path).parent.mkdir(exist_ok=True)
    with open(path, "a", encoding="utf-8") as f: f.write(json.dumps({"user": user_text, "bot": good_answer}, ensure_ascii=False) + "\n")
