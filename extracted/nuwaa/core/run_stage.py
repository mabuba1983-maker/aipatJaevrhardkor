"""Train one stage from scratch and run EVERY check, then write stage_reports/<stage>.json. Needs PyTorch.
python -m nuwaa.core.run_stage --stage s2m --steps 3000"""
import argparse, gc, json, time
from pathlib import Path
import numpy as np, torch
from .config import Config
from .layout import count_params, bin_size_bytes
from .limits import phone_problems, estimate_phone_ram_mb, check_phone_feasible
from .model import GPT
from .stages import stage_config, ORDER
from .train import train
from .export_bin import export_state
from .ref_infer import load_bin, logits as ref_logits
from .engine import Engine
from .benchmark import run_benchmark

def rss_mb():
    for l in open("/proc/self/status"):
        if l.startswith("VmRSS"): return int(l.split()[1]) / 1024
    return 0.0

def run_stage(stage, steps=3000, bs=16, root="."):
    root = Path(root); cfg = stage_config(stage); art = root / "stage_artifacts" / stage; art.mkdir(parents=True, exist_ok=True)
    pt, binf = art / "model.pt", art / "model.bin"
    rep = {"stage": stage, "checks": {}, "metrics": {}, "notes": []}; ck = rep["checks"]; m = rep["metrics"]
    t = train(stage, steps, bs, str(pt), data_dir=str(root / "data")); m["training"] = t
    ck["training_ok"] = bool(t["finite"] and t["loss_last"] < t["loss_first"])
    model = GPT(cfg); n = sum(p.numel() for p in model.parameters())
    m["params"] = n; ck["param_formula_matches"] = (n == count_params(cfg))
    # save -> reload must give identical outputs
    saved = torch.load(pt, map_location="cpu"); a, b = GPT(cfg).eval(), GPT(Config(**saved["cfg"])).eval(); b.load_state_dict(saved["state"])
    ids = torch.randint(0, 256, (1, min(32, cfg.block)))
    a.load_state_dict(saved["state"]); ck["save_reload_ok"] = bool(torch.equal(a(ids)[0], b(ids)[0]))
    # inference through the same path the product uses
    gc.collect(); r0 = rss_mb(); eng = Engine(str(pt)); t0 = time.perf_counter(); out = eng.reply("مرحبا", max_new=32); dt = time.perf_counter() - t0
    m["ram_inference_mb"] = round(rss_mb() - r0, 1); m["latency_s_for_32_tokens_desktop"] = round(dt, 3)
    m["latency_ms_per_token_desktop"] = round(1000 * dt / 32, 1); ck["inference_ok"] = isinstance(out, str)
    # phone side
    m["weights_mb"] = round(bin_size_bytes(cfg) / 1e6, 2); m["phone_ram_estimate_mb"] = round(estimate_phone_ram_mb(cfg), 1)
    pp = phone_problems(cfg); ck["phone_limits_ok"] = not pp
    if pp: rep["notes"].append("blocked for phone: " + "; ".join(pp))
    else:
        export_state(saved["state"], cfg, str(binf)); m["apk_model_mb"] = round(binf.stat().st_size / 1e6, 2)
        c2, w = load_bin(str(binf)); ids_l = ids[0].tolist()
        diff = float(np.abs(ref_logits(c2, w, ids_l) - a(ids)[0][0].detach().numpy()).max()); m["app_parity_max_abs_diff"] = diff
        ck["app_format_parity_ok"] = diff < 1e-3
    m["benchmark"] = run_benchmark(lambda q: eng.reply(q, max_new=150), str(root / "data" / "eval"))
    rep["apk_built"] = None; rep["notes"].append("APK size/build are filled in by CI (stage_cli apk). Latency/RAM here are desktop numbers, not phone numbers.")
    rep["all_ok"] = all(ck.values()); (root / "stage_reports").mkdir(exist_ok=True)
    (root / "stage_reports" / f"{stage}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False)); return rep

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default=ORDER[0]); ap.add_argument("--steps", type=int, default=3000); ap.add_argument("--bs", type=int, default=16)
    a = ap.parse_args(); print(json.dumps(run_stage(a.stage, a.steps, a.bs), indent=2, ensure_ascii=False))
