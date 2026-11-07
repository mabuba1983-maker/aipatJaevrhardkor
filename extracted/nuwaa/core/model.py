"""Small GPT written from scratch (PyTorch). Weights start random: knowledge comes from training on data/."""
import torch, torch.nn as nn, torch.nn.functional as F
from .config import Config  # torch-free, so sizes can be planned without PyTorch

class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(c.n_embd), nn.LayerNorm(c.n_embd)
        self.qkv = nn.Linear(c.n_embd, 3 * c.n_embd)
        self.proj = nn.Linear(c.n_embd, c.n_embd)
        self.fc = nn.Linear(c.n_embd, 4 * c.n_embd)
        self.out = nn.Linear(4 * c.n_embd, c.n_embd)
        self.h = c.n_head
    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.qkv(self.ln1(x)).split(C, dim=2)
        q, k, v = (t.view(B, T, self.h, C // self.h).transpose(1, 2) for t in (q, k, v))
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(a.transpose(1, 2).reshape(B, T, C))
        return x + self.out(F.gelu(self.fc(self.ln2(x))))

class GPT(nn.Module):
    def __init__(self, c: Config):
        super().__init__()
        self.c = c
        self.tok = nn.Embedding(c.vocab, c.n_embd)
        self.pos = nn.Embedding(c.block, c.n_embd)
        self.blocks = nn.ModuleList(Block(c) for _ in range(c.n_layer))
        self.ln = nn.LayerNorm(c.n_embd)
        self.head = nn.Linear(c.n_embd, c.vocab, bias=False)
        self.head.weight = self.tok.weight  # weight tying keeps the model small
        self.apply(self._init)
    def _init(self, m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, 0, 0.02)
            if getattr(m, "bias", None) is not None: nn.init.zeros_(m.bias)
    def forward(self, idx, targets=None):
        B, T = idx.shape
        x = self.tok(idx) + self.pos(torch.arange(T, device=idx.device))
        for b in self.blocks: x = b(x)
        logits = self.head(self.ln(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=-100)
        return logits, loss
    @torch.no_grad()
    def generate(self, idx, max_new=200, temperature=0.0, stop=None):
        for _ in range(max_new):
            logits, _ = self(idx[:, -self.c.block:])
            if temperature <= 0:  # greedy: most accurate, and identical to the phone app
                nxt = logits[:, -1].argmax(-1, keepdim=True)
            else:
                nxt = torch.multinomial(F.softmax(logits[:, -1] / temperature, dim=-1), 1)
            idx = torch.cat([idx, nxt], 1)
            if stop is not None and nxt.item() == stop: break
        return idx
