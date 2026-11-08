"""Run a trained model.pt locally (greedy by default, same as the phone app)."""
import torch
from .model import GPT
from .config import Config
from .tokenizer import encode_chat, decode, EOS, BOS, USR, BOT

# max_new is a SAFETY VALVE, not a target length. Real "the model decides when to stop" comes from it
# emitting EOS on its own (stop=EOS below) — that only works once it's trained on data where replies
# actually end with EOS, i.e. this is a training-data property, not a decoding trick. 20000 is just a
# very high ceiling so a bug (or a genuinely undertrained model that never learned to stop) can't loop
# forever; it is not meant to be hit in normal use. Input length is bounded by `block` (stages.py) —
# that one CANNOT be made literally infinite: attention cost grows with block^2, so doubling it roughly
# quadruples memory+compute. 4096 (current s220m_desktop) is already the "as large as practical" choice,
# not an arbitrary cap — raise it further only if you also have the training compute/RAM to match.
DEFAULT_MAX_NEW = 20000


class Engine:
    def __init__(self, path="model.pt"):
        ck = torch.load(path, map_location="cpu"); self.m = GPT(Config(**ck["cfg"])); self.m.load_state_dict(ck["state"]); self.m.eval()

    def reply(self, text, max_new=DEFAULT_MAX_NEW, temperature=0.0, **decode_kwargs):
        """decode_kwargs: repetition_penalty, no_repeat_ngram, min_confidence, unsure_token — see model.GPT.generate."""
        ids = torch.tensor([encode_chat(text)[-self.m.c.block + 1:]])
        out = self.m.generate(ids, max_new=max_new, temperature=temperature, stop=EOS, **decode_kwargs)[0].tolist()
        return decode(out[ids.shape[1]:])

    def reply_with_image(self, text, image_path, max_new=DEFAULT_MAX_NEW, image_size=16, **decode_kwargs):
        """Crude, low-quality image input — see vision.py for exactly what this does and doesn't do.
        Meaningless until the model is trained on image+caption pairs built the same way (vision.image_to_tokens)."""
        from .vision import image_to_tokens
        img_tokens = image_to_tokens(image_path, size=image_size)
        ids = [BOS, USR] + img_tokens + list(text.encode("utf-8")) + [BOT]
        ids = torch.tensor([ids[-self.m.c.block + 1:]])
        out = self.m.generate(ids, max_new=max_new, temperature=0.0, stop=EOS, **decode_kwargs)[0].tolist()
        return decode(out[ids.shape[1]:])
