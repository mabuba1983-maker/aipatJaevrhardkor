"""Train from scratch, or continue training an existing model.pt. Usage:
python -m nuwaa.core.train --stage s2m --steps 3000
python -m nuwaa.core.train --stage s220m_desktop --resume model.pt --steps 3000   # continue, don't restart

Ready for GB-scale data: jsonl files are INDEXED (file + byte offset per line), not loaded into RAM --
so a 5 GB training file costs ~bytes-per-line of index memory, not 5 GB. .txt files are still read whole
(they're normally small corpora; say if you need streaming for huge .txt too, that's a bigger change).
"""
import argparse, glob, json, math, os, random
from .stages import stage_config, selected_stage
from .tokenizer import encode, encode_chat, EOS, BOS, PAD, BOT


def _index_jsonl(data_dir="data"):
    """[(filepath, byte_offset), ...] -- one entry per non-empty line, across every matching file.
    Building this costs one sequential pass (to find line boundaries) but holds none of the text."""
    index = []
    for f in sorted(glob.glob(f"{data_dir}/*.jsonl") + glob.glob(f"{data_dir}/train_only/*.jsonl")):
        with open(f, "rb") as fh:
            offset = 0
            for raw in fh:
                if raw.strip():
                    index.append((f, offset))
                offset += len(raw)
    return index


def _read_jsonl_example(filepath, offset):
    with open(filepath, "rb") as fh:
        fh.seek(offset)
        line = fh.readline().decode("utf-8")
    d = json.loads(line)
    ids = encode_chat(d["user"], d["bot"])
    return ids, ids.index(BOT) + 1   # learn the ANSWER, not the question


def load_txt_examples(data_dir="data"):
    """Still fully in RAM -- fine for normal-sized .txt corpora. See module docstring if this needs
    to scale to GB-sized .txt too."""
    ex = []
    for f in sorted(glob.glob(f"{data_dir}/*.txt")):
        for chunk in open(f, encoding="utf-8").read().split("\n\n"):
            if chunk.strip():
                ex.append(([BOS] + encode(chunk.strip()) + [EOS], 1))
    return ex


def load_examples(data_dir="data"):
    """Back-compat convenience: everything fully materialized. Fine for small/medium data (what the
    tests and small stages use). For GB-scale jsonl, use _index_jsonl + _read_jsonl_example instead
    (train() below does this automatically) so you don't load gigabytes into RAM at once."""
    ex = [_read_jsonl_example(f, o) for f, o in _index_jsonl(data_dir)]
    ex += load_txt_examples(data_dir)
    return ex


def make_xy(example, block):
    """Pure-python (testable): inputs and targets for one example. Targets before `start` (the question) are ignored."""
    ids, start = example
    s = ids[: block + 1]; s = s + [PAD] * (block + 1 - len(s))
    x = s[:-1]; y = [t if (t != PAD and j + 1 >= start) else -100 for j, t in enumerate(s[1:])]
    return x, y


def batch_from_index(jsonl_index, txt_examples, bs, block, device="cpu"):
    """Samples bs examples total: reads jsonl examples lazily from disk by offset (no RAM blowup even
    at GB scale), mixed with the (already small) in-memory .txt examples."""
    import torch
    pairs = []
    for _ in range(bs):
        if txt_examples and (not jsonl_index or random.random() < 0.1):
            ex = random.choice(txt_examples)
        else:
            f, o = random.choice(jsonl_index)
            ex = _read_jsonl_example(f, o)
        pairs.append(make_xy(ex, block))
    return torch.tensor([p[0] for p in pairs], device=device), torch.tensor([p[1] for p in pairs], device=device)


def batch(ex, bs, block, device="cpu"):
    """Old in-memory-list API -- kept so existing callers/tests still work unchanged."""
    import torch
    pairs = [make_xy(random.choice(ex), block) for _ in range(bs)]
    return torch.tensor([p[0] for p in pairs], device=device), torch.tensor([p[1] for p in pairs], device=device)


def train(stage, steps=3000, bs=16, out="model.pt", data_dir="data", seed=0, log=print, resume=None):
    """resume: path to an existing model.pt to CONTINUE training (same architecture only -- you can't
    resume into a different stage's shapes). None = start from random weights, as before.
    This is what makes "lots of training over time, in gigabytes, across many separate runs" actually
    work: each run picks up where the last one left off instead of re-learning from zero every time."""
    import torch
    from .model import GPT
    random.seed(seed); torch.manual_seed(seed)
    cfg = stage_config(stage)
    jsonl_index = _index_jsonl(data_dir)
    txt_examples = load_txt_examples(data_dir)
    assert jsonl_index or txt_examples, "no training data"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"device: {device}, jsonl examples (indexed, not loaded): {len(jsonl_index)}, txt examples: {len(txt_examples)}")

    model = GPT(cfg).to(device)
    start_step_note = "from random weights"
    if resume and os.path.exists(resume):
        ck = torch.load(resume, map_location=device)
        if ck["cfg"] != cfg.to_dict():
            raise ValueError(f"--resume {resume} was trained with a different config {ck['cfg']} != {cfg.to_dict()} "
                              f"-- you can only resume into the SAME stage, not a bigger/smaller one.")
        model.load_state_dict(ck["state"])
        start_step_note = f"resumed from {resume}"
    log(f"training {stage} ({sum(p.numel() for p in model.parameters()):,} params), {start_step_note}")

    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    losses = []
    for step in range(steps):
        lr = 3e-4 * min(1.0, (step + 1) / 50) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / max(1, steps))))
        for g in opt.param_groups: g["lr"] = lr
        x, y = batch_from_index(jsonl_index, txt_examples, bs, cfg.block, device)
        _, loss = model(x, y); opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
        v = loss.item(); losses.append(v)
        if step % 100 == 0: log(f"{stage} step {step} loss {v:.4f}")
    torch.save({"cfg": cfg.to_dict(), "stage": stage, "state": {k: v.detach().cpu() for k, v in model.state_dict().items()}}, out)   # always saved on CPU so the phone exporter and tests load it anywhere
    first, last = sum(losses[:10]) / len(losses[:10]), sum(losses[-10:]) / len(losses[-10:])
    return {"loss_first": first, "loss_last": last, "steps": steps, "finite": math.isfinite(last)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=selected_stage()); ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--bs", type=int, default=16); ap.add_argument("--out", default="model.pt")
    ap.add_argument("--data-dir", default="data", help="folder of *.jsonl/*.txt to train on, e.g. a code-only subset")
    ap.add_argument("--resume", default=None, help="an existing model.pt of the SAME stage to continue training")
    a = ap.parse_args()
    print(train(a.stage, a.steps, a.bs, a.out, data_dir=a.data_dir, resume=a.resume))
    print("saved", a.out)
if __name__ == "__main__": main()
