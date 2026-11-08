"""Byte-level tokenizer: no external vocab, no license, handles Arabic + code."""
PAD, BOS, EOS, USR, BOT = 256, 257, 258, 259, 260
IMG_START, IMG_END = 261, 262   # wrap a sequence of raw pixel bytes (0-255 = grayscale intensity) — see vision.py
VOCAB_SIZE = 263

def encode(text: str) -> list[int]:
    return list(text.encode("utf-8"))

def decode(ids) -> str:
    return bytes(i for i in ids if i < 256).decode("utf-8", errors="ignore")

def encode_chat(user: str, bot: str | None = None) -> list[int]:
    ids = [BOS, USR] + encode(user) + [BOT]
    if bot is not None:
        ids += encode(bot) + [EOS]
    return ids
