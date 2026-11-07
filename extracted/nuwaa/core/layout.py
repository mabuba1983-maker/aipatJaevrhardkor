"""Single source of truth for tensor order/shapes. Used by the exporter, the numpy reference, the Kotlin app format and the tests."""
HEADER_BYTES = 20  # 5 little-endian int32: n_layer, n_head, n_embd, block, vocab

def tensor_shapes(c):
    C, V, T = c.n_embd, c.vocab, c.block
    out = [("tok.weight", (V, C)), ("pos.weight", (T, C))]
    for i in range(c.n_layer):
        p = f"blocks.{i}."
        out += [(p + "ln1.weight", (C,)), (p + "ln1.bias", (C,)), (p + "qkv.weight", (3 * C, C)), (p + "qkv.bias", (3 * C,)),
                (p + "proj.weight", (C, C)), (p + "proj.bias", (C,)), (p + "ln2.weight", (C,)), (p + "ln2.bias", (C,)),
                (p + "fc.weight", (4 * C, C)), (p + "fc.bias", (4 * C,)), (p + "out.weight", (C, 4 * C)), (p + "out.bias", (C,))]
    return out + [("ln.weight", (C,)), ("ln.bias", (C,))]

def count_params(c) -> int:
    n = 0
    for _, s in tensor_shapes(c):
        k = 1
        for d in s: k *= d
        n += k
    return n  # output head is tied to tok.weight, so it adds nothing

def bin_size_bytes(c) -> int:
    return HEADER_BYTES + 4 * count_params(c)
