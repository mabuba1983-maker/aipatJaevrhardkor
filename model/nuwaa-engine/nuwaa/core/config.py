from .tokenizer import VOCAB_SIZE

class Config:
    def __init__(self, n_layer=4, n_head=4, n_embd=192, block=256, vocab=VOCAB_SIZE):
        self.n_layer, self.n_head, self.n_embd, self.block, self.vocab = n_layer, n_head, n_embd, block, vocab
    def to_dict(self): return dict(self.__dict__)
