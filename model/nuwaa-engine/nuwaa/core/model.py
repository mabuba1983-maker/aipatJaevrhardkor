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
    def generate(self, idx, max_new=200, temperature=0.0, stop=None, repetition_penalty=1.3,
                 no_repeat_ngram=4, min_confidence=None, unsure_token=None):
        """Accuracy-first decoding (slower than plain greedy, on purpose):
        - repetition_penalty: pushes down logits of tokens already produced, so the model doesn't loop
          instead of admitting it ran out of a real answer (a common cause of 'confident nonsense').
        - no_repeat_ngram: bans repeating a whole n-gram verbatim, same reason, for longer loops.
        - min_confidence + unsure_token: if the model's own top probability is below this, emit
          unsure_token instead of guessing. This does NOT make the model know more; it only makes it
          say 'not sure' instead of inventing an answer when its own distribution is flat. Leave
          min_confidence=None to disable (matches the previous, plain-greedy behaviour exactly).
        """
        start = idx.shape[1]
        for _ in range(max_new):
            logits, _ = self(idx[:, -self.c.block:])
            logits = logits[:, -1].clone()
            if repetition_penalty and repetition_penalty != 1.0:
                seen = idx[0, start:].tolist()
                for t in set(seen):
                    logits[:, t] = logits[:, t] / repetition_penalty if logits[:, t] > 0 else logits[:, t] * repetition_penalty
            if no_repeat_ngram and no_repeat_ngram > 1:
                seq = idx[0, start:].tolist()
                n = no_repeat_ngram
                if len(seq) >= n - 1:
                    prefix = seq[-(n - 1):]
                    banned = {seq[i + n - 1] for i in range(len(seq) - n + 1) if seq[i:i + n - 1] == prefix}
                    for t in banned: logits[:, t] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            if temperature <= 0:  # greedy: most accurate token-by-token choice, and identical to the phone app
                nxt = probs.argmax(-1, keepdim=True)
            else:
                nxt = torch.multinomial(F.softmax(logits / temperature, dim=-1), 1)
            if min_confidence is not None and unsure_token is not None and probs.max().item() < min_confidence:
                nxt = torch.tensor([[unsure_token]], device=idx.device)
            idx = torch.cat([idx, nxt], 1)
            if stop is not None and nxt.item() == stop: break
        return idx
