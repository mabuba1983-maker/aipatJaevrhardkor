"""Run a trained model.pt locally (greedy by default, same as the phone app)."""
import torch
from .model import GPT
from .config import Config
from .tokenizer import encode_chat, decode, EOS
class Engine:
    def __init__(self, path="model.pt"):
        ck = torch.load(path, map_location="cpu"); self.m = GPT(Config(**ck["cfg"])); self.m.load_state_dict(ck["state"]); self.m.eval()
    def reply(self, text, max_new=200, temperature=0.0):
        ids = torch.tensor([encode_chat(text)[-self.m.c.block + 1:]])
        out = self.m.generate(ids, max_new=max_new, temperature=temperature, stop=EOS)[0].tolist()
        return decode(out[ids.shape[1]:])
