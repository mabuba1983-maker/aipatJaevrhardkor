# -*- coding: utf-8 -*-
"""What machine am I on? CPU cores, RAM, graphics card(s) and their memory, and what model size that machine can reasonably train.
Run:  python -m nuwaa.lm.hw      (also printed at the start of pretrain_gru, train_gru_torch and scale_up)"""
import os, platform, re, shutil, subprocess, sys

def _run(cmd, t=8):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=t, shell=isinstance(cmd, str)).stdout.strip()
    except Exception: return ""

def ram_gb():
    try:
        if sys.platform.startswith("linux"):
            for l in open("/proc/meminfo"):
                if l.startswith("MemTotal"): return int(l.split()[1]) / 1e6
        if sys.platform == "win32":
            import ctypes
            class MS(ctypes.Structure): _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ex1", ctypes.c_ulonglong), ("ex2", ctypes.c_ulonglong), ("ex3", ctypes.c_ulonglong)]
            ms = MS(); ms.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)); return ms.tp / 1e9
        if sys.platform == "darwin": return int(_run("sysctl -n hw.memsize")) / 1e9
    except Exception: pass
    return 0.0

def gpus():
    """[(name, memory_GB or 0, how it was found)] for every graphics card that can be seen."""
    out = []
    if shutil.which("nvidia-smi"):
        for l in _run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits").splitlines():
            p = [x.strip() for x in l.split(",")]
            if len(p) == 2 and p[1].replace(".", "").isdigit(): out.append((p[0], float(p[1]) / 1024, "nvidia-smi"))
    if not out:
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    pr = torch.cuda.get_device_properties(i); out.append((pr.name, pr.total_memory / 1e9, "torch"))
        except Exception: pass
    if not out and sys.platform == "win32":
        for l in _run("wmic path win32_VideoController get name").splitlines()[1:]:
            if l.strip(): out.append((l.strip(), 0.0, "wmic"))
    if not out and sys.platform.startswith("linux"):
        for l in _run("lspci").splitlines():
            if re.search(r"VGA|3D|Display", l): out.append((l.split(": ", 1)[-1].strip(), 0.0, "lspci"))
    if not out and sys.platform == "darwin":
        for l in _run("system_profiler SPDisplaysDataType").splitlines():
            if "Chipset Model" in l or "Chip" in l.split(":")[0]: out.append((l.split(":", 1)[-1].strip(), 0.0, "system_profiler"))
    return out

def advice(d):
    """A plain recommendation: the largest size worth training here (weights + gradients + Adam need ~16 bytes per weight, plus activations)."""
    g = [x for x in d["gpus"] if x[1] > 0]
    if g:
        vram = max(x[1] for x in g)
        if vram >= 14: return "كرت قوي: حتى 100 مليون وزن مريح (python tools/scale_up.py --target 100000000 ثم tools/train_gru_torch.py --amp)."
        if vram >= 7: return "كرت متوسط: حتى 40 مليون وزن (target 40000000)."
        if vram >= 3.5: return "كرت صغير: حتى 10-25 مليون وزن."
        return "ذاكرة الكرت قليلة: 10 مليون كحد أقصى."
    if d["gpus"]: return "فيه كرت شاشة لكن لا أعرف ذاكرته (ثبّت تعريف NVIDIA/torch ليظهر). بدون CUDA التدريب يمشي على المعالج: 10 مليون كحد أقصى عمليا."
    return "ما وجدت كرت شاشة: التدريب على المعالج فقط. الأفضل 1.5 إلى 10 مليون وزن، والأحجام الأكبر على Colab (T4 مجاني)."

def info():
    return {"os": platform.platform(), "cpu": platform.processor() or platform.machine(), "cores": os.cpu_count(), "ram_gb": ram_gb(), "gpus": gpus()}

def report():
    d = info(); lines = [f"النظام: {d['os']}", f"المعالج: {d['cpu']} ({d['cores']} نواة)", f"الذاكرة: {d['ram_gb']:.1f} GB" if d["ram_gb"] else "الذاكرة: ؟"]
    if d["gpus"]:
        for n, m, how in d["gpus"]: lines.append(f"كرت الشاشة: {n}" + (f" ({m:.1f} GB)" if m else " (الذاكرة غير معروفة)") + f" [{how}]")
    else: lines.append("كرت الشاشة: غير موجود")
    lines.append("التوصية: " + advice(d)); return "\n".join(lines)

if __name__ == "__main__": print(report())
