# -*- coding: utf-8 -*-
"""Minimal local interface for the engine only (no weights, no memory/mind layer -- just the model).
Run: python local_chat.py --model model.pt
`model.pt` is NOT included here on purpose (you asked for no weights in this package).
Train one with: python -m nuwaa.core.train --stage s220m_desktop --steps 30000 --data-dir data
or download one produced by .github/workflows/train-accuracy.yml as a GitHub Actions artifact.
"""
import argparse
from nuwaa.core.engine import Engine
from nuwaa.core.tokenizer import encode

UNSURE_PHRASE = "...ما عندي جواب واثق منه"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="model.pt")
    ap.add_argument("--max-new", type=int, default=20000)  # safety valve, not a target -- see engine.py
    ap.add_argument("--repetition-penalty", type=float, default=1.3,
                     help="1.0 disables it (plain greedy, identical to before)")
    ap.add_argument("--no-repeat-ngram", type=int, default=4, help="0 disables it")
    ap.add_argument("--min-confidence", type=float, default=None,
                     help="0..1; below this the engine says it's not sure instead of guessing. Off by default.")
    a = ap.parse_args()

    try:
        eng = Engine(a.model)
    except FileNotFoundError:
        print(f"لا يوجد ملف أوزان هنا: {a.model}")
        print("درّب نموذج أولا (شوف التعليقات أعلى هذا الملف) ثم شغّل هذا السكربت على model.pt الناتج.")
        return

    unsure_id = encode(UNSURE_PHRASE)[0] if a.min_confidence is not None else None
    print("اكتب رسالتك. اكتب 'خروج' للإنهاء.")
    while True:
        q = input("> ").strip()
        if q in ("خروج", "exit", "quit"):
            break
        if not q:
            continue
        print(eng.reply(
            q, max_new=a.max_new,
            repetition_penalty=a.repetition_penalty,
            no_repeat_ngram=a.no_repeat_ngram,
            min_confidence=a.min_confidence,
            unsure_token=unsure_id,
        ))


if __name__ == "__main__":
    main()
