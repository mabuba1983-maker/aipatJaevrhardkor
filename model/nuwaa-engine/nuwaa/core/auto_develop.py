# -*- coding: utf-8 -*-
"""Automatic, unsupervised engine development — the honest version of "يطور نفسه بنفسه".

What this actually is (read this before trusting the name): the tiny model does NOT edit its own
code and does NOT judge its own improvements — it has nowhere near the reasoning capability for that
safely, and nobody has solved "a small model safely rewrites its own architecture" in general, for
anyone, at any lab. What CAN work, and does work here, is simpler and well-established: automatically
try several variations of the engine's OWN config (nuwaa/core/stages.py), train each one briefly, score
it on the held-out benchmark (data/eval/*.jsonl — never trained on), and mechanically keep whichever
config actually scored best. That is a real search over the engine's own architecture, run completely
unattended, with no human picking the winner — which is what "self development" can honestly mean here.

Run: python -m nuwaa.core.auto_develop --base s220m_desktop --steps 500 --generations 3
Writes discovered_stages.json (small, a few KB — NOT weights) with the full history + current champion.
The champion is auto-registered into stages.STAGES under the name "s_auto_best" for anything to use.
"""
import argparse, copy, json, random
from pathlib import Path

from .stages import STAGES
from .config import Config
from .layout import count_params
from .train import train
from .engine import Engine
from .benchmark import run_benchmark

STATE_FILE = Path("discovered_stages.json")

# How a candidate is allowed to differ from its parent in one generation — kept small and local
# on purpose: a random huge jump almost always just makes training worse with the same step budget.
MUTATIONS = [
    lambda c: {**c, "n_layer": max(4, c["n_layer"] + random.choice([-2, 2]))},
    lambda c: {**c, "n_embd": max(192, c["n_embd"] + random.choice([-64, 64]))},
    lambda c: {**c, "n_head": max(4, c["n_head"] + random.choice([-1, 1]))},
]


def _load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"champion": None, "champion_score": -1.0, "history": []}


def _save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _score_config(cfg_dict, steps, bs, data_dir, tag):
    """Train this exact config briefly and return (score, params). Never raises on a bad config —
    a config that fails to train just scores 0.0 and gets discarded, same as any failed experiment."""
    try:
        cfg = Config(**cfg_dict)
        n_params = count_params(cfg)
        out_path = f"/tmp/auto_develop_{tag}.pt"
        train_report = train(cfg_dict_to_stage_name(cfg_dict), steps, bs, out_path, data_dir=data_dir)
        if not train_report["finite"]:
            return 0.0, n_params, {"error": "training diverged (non-finite loss)"}
        eng = Engine(out_path)
        bench = run_benchmark(lambda q: eng.reply(q, max_new=150), eval_dir=f"{data_dir}/eval")
        return bench["total"], n_params, bench
    except Exception as e:
        return 0.0, 0, {"error": str(e)}


def cfg_dict_to_stage_name(cfg_dict):
    # train() takes a stage NAME and looks it up in STAGES; register this candidate under a temp name first.
    name = f"_candidate_{cfg_dict['n_layer']}_{cfg_dict['n_embd']}_{cfg_dict['n_head']}_{cfg_dict['block']}"
    STAGES[name] = {k: cfg_dict[k] for k in ("n_layer", "n_head", "n_embd", "block")}
    return name


def run(base_stage="s220m_desktop", steps=500, bs=16, generations=3, data_dir="data", log=print):
    state = _load_state()
    parent = state["champion"] or dict(STAGES[base_stage])
    parent_score = state["champion_score"]

    if parent_score < 0:
        log(f"[auto_develop] no champion yet — scoring the base stage '{base_stage}' first")
        parent_score, n, bench = _score_config(parent, steps, bs, data_dir, "base")
        state["champion"], state["champion_score"] = parent, parent_score
        state["history"].append({"gen": 0, "config": parent, "score": parent_score, "params": n, "bench": bench})
        log(f"[auto_develop] base score = {parent_score:.4f} ({n:,} params)")

    for gen in range(1, generations + 1):
        mutate = random.choice(MUTATIONS)
        candidate = mutate(dict(parent))
        log(f"[auto_develop] gen {gen}: trying {candidate}")
        score, n, bench = _score_config(candidate, steps, bs, data_dir, f"gen{gen}")
        state["history"].append({"gen": gen, "config": candidate, "score": score, "params": n, "bench": bench})
        log(f"[auto_develop] gen {gen}: score={score:.4f} (champion so far={state['champion_score']:.4f})")
        if score > state["champion_score"]:
            log(f"[auto_develop] NEW CHAMPION: {candidate} ({score:.4f} > {state['champion_score']:.4f})")
            state["champion"], state["champion_score"] = candidate, score
            parent = candidate
        _save_state(state)  # save after every generation, not just at the end, so a crash loses at most one gen

    STAGES["s_auto_best"] = dict(state["champion"])
    log(f"[auto_develop] done. champion registered as stage 's_auto_best': {state['champion']} "
        f"(score {state['champion_score']:.4f})")
    return state


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="s220m_desktop")
    ap.add_argument("--steps", type=int, default=500, help="training steps PER CANDIDATE, not total")
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--generations", type=int, default=3)
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    run(a.base, a.steps, a.bs, a.generations, a.data_dir)
