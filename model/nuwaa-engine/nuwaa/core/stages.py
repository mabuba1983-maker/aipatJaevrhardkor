"""THE one place that defines model size. To change size: edit stage.json ("stage": "s5m") - never rewrite the architecture.
To add a new size: add one line to STAGES."""
import json, os
from pathlib import Path
from .config import Config
from .limits import phone_problems

#           layers heads embd  block
STAGES = {
    "s2m":  dict(n_layer=4,  n_head=4, n_embd=192, block=256),   # ~1.9M  start
    "s5m":  dict(n_layer=6,  n_head=4, n_embd=256, block=256),   # ~4.9M
    "s10m": dict(n_layer=8,  n_head=5, n_embd=320, block=384),   # ~10M
    "s20m": dict(n_layer=10, n_head=8, n_embd=416, block=384),   # ~21M
    "s30m": dict(n_layer=12, n_head=8, n_embd=448, block=512),   # ~29M
    "s45m": dict(n_layer=14, n_head=8, n_embd=512, block=512),   # ~44M
    "s80m": dict(n_layer=16, n_head=10, n_embd=640, block=512),  # ~79M  the 500 MB-RAM class: last stage allowed on phone
    "s110m_desktop": dict(n_layer=18, n_head=11, n_embd=704, block=512),  # ~107M: exceeds the 500 MB budget on purpose
    "s220m_desktop": dict(n_layer=22, n_head=12, n_embd=960, block=4096),   # ~248M params (name is historical, kept so old configs/scripts still match), 4096-byte context.
    # NOT free capacity: a stage this size needs proportionally MUCH more training data and steps than s2m..s80m,
    # or it ends up WORSE than a smaller well-trained stage (more random, untrained parameters = more noise, not more understanding).
    # Pair this stage with --steps in the tens of thousands and a data/ dir that is mostly code, or do not use it.
    # block=4096 (was 768): attention cost grows with the SQUARE of block, so 4096 is ~28x slower per step than 768 —
    # that is fine for "slow but accurate, no rush", which is what you asked for, but know that's where the slowdown comes from.

    # --- Future headroom, for when you're training on real GPU compute (not free GitHub CPU runners) ---
    # The ARCHITECTURE itself has no size ceiling baked in -- it's the same attention+MLP block whether
    # it's 2M or 200B params, just bigger numbers below. The real ceiling was always compute, not code.
    # These two exist so "later, with gigabytes of data" has somewhere to go without editing this file
    # again. CPU training these is NOT realistic (days-to-weeks per useful run); use Colab/Kaggle/rented
    # GPU for these, same train.py/--resume, nothing else changes.
    "s800m_gpu": dict(n_layer=28, n_head=16, n_embd=1536, block=4096),   # ~800M params (verified via count_params, not a guess). GPU only.
    "s1_8b_gpu": dict(n_layer=36, n_head=20, n_embd=2048, block=4096),   # ~1.82B params (verified via count_params). GPU only, real dataset only.
}
ORDER = list(STAGES)

def stage_config(name: str) -> Config:
    if name not in STAGES: raise KeyError(f"unknown stage {name}; choose from {ORDER}")
    return Config(**STAGES[name])

def stage_file(root=".") -> Path: return Path(root) / "stage.json"

def selected_stage(root=".") -> str:
    if os.environ.get("NUWAA_STAGE"): return os.environ["NUWAA_STAGE"]
    f = stage_file(root)
    return json.loads(f.read_text())["stage"] if f.exists() else ORDER[0]

def set_stage(name: str, root=".", for_phone=True):
    c = stage_config(name)
    if for_phone and phone_problems(c): raise ValueError(f"{name} is blocked for phone: " + "; ".join(phone_problems(c)))
    stage_file(root).write_text(json.dumps({"stage": name}))
