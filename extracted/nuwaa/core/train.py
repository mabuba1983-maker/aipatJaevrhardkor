"""Train from scratch (random weights, no external model). Usage: python -m nuwaa.core.train --stage s2m --steps 3000"""
import argparse, glob, json, math, random
from .stages import stage_config, selected_stage
from .tokenizer import encode, encode_chat, EOS, BOS, PAD, BOT

def load_examples(data_dir="data"):
    ex = []
    for f in sorted(glob.glob(f"{data_dir}/*.jsonl") + glob.glob(f"{data_dir}/train_only/*.jsonl")):   # data/eval/ is never trained on
        for line in open(f, encoding="utf-8"):
            if line.strip():
                d = json.loads(line); ids = encode_chat(d["user"], d["bot"]); ex.append((ids, ids.index(BOT) + 1))  # learn the ANSWER, not the question
    for f in sorted(glob.glob(f"{data_dir}/*.txt")):
        for chunk in open(f, encoding="utf-8").read().split("\n\n"):
            if chunk.strip(): ex.append(([BOS] + encode(chunk.strip()) + [EOS], 1))
    return ex

def make_xy(example, block):
    """Pure-python (testable): inputs and targets for one example. Targets before `start` (the question) are ignored."""
    ids, start = example
    s = ids[: block + 1]; s = s + [PAD] * (block + 1 - len(s))
    x = s[:-1]; y = [t if (t != PAD and j + 1 >= start) else -100 for j, t in enumerate(s[1:])]
    return x, y

def batch(ex, bs, block, device="cpu"):
    import torch
    pairs = [make_xy(random.choice(ex), block) for _ in range(bs)]
    return torch.tensor([p[0] for p in pairs], device=device), torch.tensor([p[1] for p in pairs], device=device)

def train(stage, steps=3000, bs=16, out="model.pt", data_dir="data", seed=0, log=print):
    import torch
    from .model import GPT
    random.seed(seed); torch.manual_seed(seed)
    cfg = stage_config(stage); ex = load_examples(data_dir); assert ex, "no training data"
    device = "cuda" if torch.cuda.is_available() else "cpu"; log(f"device: {device}, examples: {len(ex)}")   # GPU (Colab/Kaggle) is ~50x faster than CPU; results are the same math
    model = GPT(cfg).to(device); opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    losses = []
    for step in range(steps):
        lr = 3e-4 * min(1.0, (step + 1) / 50) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / max(1, steps))))
        for g in opt.param_groups: g["lr"] = lr
        x, y = batch(ex, bs, cfg.block, device)
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
    a = ap.parse_args(); print(train(a.stage, a.steps, a.bs, a.out)); print("saved", a.out)
if __name__ == "__main__": main()
