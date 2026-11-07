# -*- coding: utf-8 -*-
"""Verifies, via a faithful numpy transcription, that android Nlm.grow() (Kotlin) preserves the model's exact behaviour on old vocabulary — the
same guarantee nuwaa.lm.gru.GRULM.widened() already has (tests/test_scale.py), checked with an actual forward pass (not raw-array equality, since
Kotlin's grow() deliberately leaves new capacity at zero rather than python's random init — both are correct; only a real forward pass proves it)."""
import re, sys, unittest
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.lm.gru import GRULM

def kotlin_grow(old, newE, newH):
    """Direct numpy transcription of android/.../Nlm.kt's companion fun grow(): every untouched cell is zero (Kotlin FloatArray default); only the
    specific old-value slices are copied, index-for-index as written in the .kt file."""
    oe, oh, v = old.E, old.H, old.nv
    E = np.zeros((v, newE), np.float32); E[:, :oe] = old.P["E"][:v]
    def gated(src, oldRows, newRows, oldH, newH_):
        dst = np.zeros((newRows, 3 * newH_), np.float32)
        for row in range(oldRows):
            for g in range(3): dst[row, g * newH_:g * newH_ + oldH] = src[row, g * oldH:(g + 1) * oldH]
        return dst
    Wx1 = gated(old.P["Wx1"], oe, newE, oh, newH); Wh1 = gated(old.P["Wh1"], oh, newH, oh, newH)
    Wx2 = gated(old.P["Wx2"], oh, newH, oh, newH); Wh2 = gated(old.P["Wh2"], oh, newH, oh, newH)
    b1 = np.zeros(3 * newH, np.float32); b2 = np.zeros(3 * newH, np.float32)
    for g in range(3): b1[g * newH:g * newH + oh] = old.P["b1"][g * oh:(g + 1) * oh]; b2[g * newH:g * newH + oh] = old.P["b2"][g * oh:(g + 1) * oh]
    Wo = np.zeros((newH, v), np.float32); Wo[:oh] = old.P["Wo"][:oh, :v]; bo = old.P["bo"][:v].copy()
    return dict(E=E, Wx1=Wx1, Wh1=Wh1, b1=b1, Wx2=Wx2, Wh2=Wh2, b2=b2, Wo=Wo, bo=bo)

def sig(x): return 1 / (1 + np.exp(-x))
def forward_bpc(P, ids, H):
    h1 = np.zeros(H); h2 = np.zeros(H); tot = 0.0
    def cell(gx, h, Wh):
        rz = sig(gx[:2 * H] + h @ Wh[:, :2 * H]); r, z = rz[:H], rz[H:]; n = np.tanh(gx[2 * H:] + (r * h) @ Wh[:, 2 * H:]); return (1 - z) * h + z * n
    for i in range(len(ids) - 1):
        h1 = cell(P["E"][ids[i]] @ P["Wx1"] + P["b1"], h1, P["Wh1"]); h2 = cell(h1 @ P["Wx2"] + P["b2"], h2, P["Wh2"])
        lg = h2 @ P["Wo"] + P["bo"]; lg = lg - lg.max(); p = np.exp(lg) / np.exp(lg).sum(); tot += -np.log(p[ids[i + 1]] + 1e-9)
    return tot / (len(ids) - 1) / np.log(2)

class KotlinGrowParity(unittest.TestCase):
    def test_grow_source_matches_this_transcription(self):
        src = (ROOT / "android/app/src/main/java/ai/nuwaa/Nlm.kt").read_text(encoding="utf-8")
        self.assertIn("fun grow(old: Nlm, newE: Int, newH: Int): Nlm", src)
        for must in ("n.P[0][row * newE + col] = old.P[0][row * oe + col]", "copyGated(n.P[1], old.P[1], oe, nh3, oh3)", "n.P[7][row * v + col] = old.P[7][row * v + col]"):
            self.assertIn(must, src)
    def test_old_behaviour_exactly_preserved_after_growth(self):
        m = GRULM(24, 32, seed=3); m.encode("س:مرحبا\nج:أهلا بك\nس:ما اسمك\nج:نواة\n")
        for text in ("س:مرحبا\nج:أهلا\n", "س:ما اسمك\nج:نواة\n", "اكتب كود بايثون"):
            ids = m.encode(text, grow=False)
            official = m.bpc(ids)
            for newE, newH in ((40, 56), (64, 96)):
                grown = forward_bpc(kotlin_grow(m, newE, newH), ids, newH)
                self.assertAlmostEqual(official, grown, places=4, msg=f"grow({newE},{newH}) changed old-model behaviour")

if __name__ == "__main__": unittest.main()
