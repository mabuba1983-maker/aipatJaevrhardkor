"""Pure-numpy reference of the phone's forward pass. Reads the exported .bin exactly like the Kotlin code does.
Comparing it with PyTorch proves the export format and the algorithm the app implements."""
import struct
import numpy as np
from .config import Config
from .layout import tensor_shapes, HEADER_BYTES

def load_bin(path):
    with open(path, "rb") as f: raw = f.read()
    nl, nh, ne, bl, vo = struct.unpack("<5i", raw[:HEADER_BYTES]); cfg = Config(nl, nh, ne, bl, vo)
    w, off = {}, HEADER_BYTES
    for name, shape in tensor_shapes(cfg):
        n = int(np.prod(shape)); w[name] = np.frombuffer(raw, "<f4", n, off).reshape(shape); off += 4 * n
    if off != len(raw): raise ValueError(f"file size mismatch: parsed {off}, file {len(raw)}")
    return cfg, w

def _ln(x, w, b):
    m = x.mean(-1, keepdims=True); v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / np.sqrt(v + 1e-5) * w + b

def _gelu(x): return 0.5 * x * (1 + np.tanh(0.7978845608 * (x + 0.044715 * x ** 3)))

def logits(cfg, w, ids):
    T, C, H = len(ids), cfg.n_embd, cfg.n_head; hs = C // H
    x = w["tok.weight"][ids] + w["pos.weight"][:T]
    mask = np.triu(np.full((T, T), -1e30, dtype=np.float32), 1)
    for i in range(cfg.n_layer):
        p = f"blocks.{i}."
        qkv = _ln(x, w[p + "ln1.weight"], w[p + "ln1.bias"]) @ w[p + "qkv.weight"].T + w[p + "qkv.bias"]
        q, k, v = (qkv[:, j * C:(j + 1) * C].reshape(T, H, hs).transpose(1, 0, 2) for j in range(3))
        a = q @ k.transpose(0, 2, 1) / np.sqrt(hs) + mask
        a = np.exp(a - a.max(-1, keepdims=True)); a /= a.sum(-1, keepdims=True)
        x = x + (a @ v).transpose(1, 0, 2).reshape(T, C) @ w[p + "proj.weight"].T + w[p + "proj.bias"]
        h = _gelu(_ln(x, w[p + "ln2.weight"], w[p + "ln2.bias"]) @ w[p + "fc.weight"].T + w[p + "fc.bias"])
        x = x + h @ w[p + "out.weight"].T + w[p + "out.bias"]
    return _ln(x, w["ln.weight"], w["ln.bias"]) @ w["tok.weight"].T
