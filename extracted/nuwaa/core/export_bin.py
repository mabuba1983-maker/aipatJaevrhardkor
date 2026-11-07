"""Export to the flat float32 file the Android app reads. Refuses stages that are impractical on a phone.
Usage: python -m nuwaa.core.export_bin model.pt out.bin"""
import struct, sys
import numpy as np
from .config import Config
from .layout import tensor_shapes
from .limits import check_phone_feasible

def export_state(state: dict, cfg: Config, dst: str):
    check_phone_feasible(cfg)
    with open(dst, "wb") as f:
        f.write(struct.pack("<5i", cfg.n_layer, cfg.n_head, cfg.n_embd, cfg.block, cfg.vocab))
        for name, shape in tensor_shapes(cfg):
            a = np.ascontiguousarray(state[name].detach().cpu().float().numpy() if hasattr(state[name], "detach") else state[name], dtype="<f4")
            assert tuple(a.shape) == tuple(shape), f"{name}: {a.shape} != {shape}"
            f.write(a.tobytes())

def main(src, dst):
    import torch
    ck = torch.load(src, map_location="cpu"); export_state(ck["state"], Config(**ck["cfg"]), dst); print("exported", dst)
if __name__ == "__main__": main(*sys.argv[1:3])
