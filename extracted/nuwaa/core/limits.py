"""Hard phone limits. A stage that breaks any of them cannot be selected for the app, exported to the app, or accepted for the APK."""
from .layout import count_params, bin_size_bytes
PHONE_MAX_PARAMS = 100_000_000
PHONE_MAX_WEIGHTS_MB = 400.0   # fp32 file that ships inside the APK
PHONE_MAX_RAM_MB = 500.0       # the RAM budget: weights (streamed straight into float arrays, no second copy) + KV cache + app overhead

class PhoneLimitError(Exception): pass

def weights_mb(c): return bin_size_bytes(c) / 1e6
def kv_cache_mb(c): return 2 * c.n_layer * c.block * c.n_embd * 4 / 1e6
APP_OVERHEAD_MB = 60.0         # UI + knowledge base + Android runtime (Kotlin side checks the real heap before loading)
def estimate_phone_ram_mb(c): return weights_mb(c) + kv_cache_mb(c) + APP_OVERHEAD_MB

def phone_problems(c):
    p = []
    if count_params(c) > PHONE_MAX_PARAMS: p.append(f"params {count_params(c):,} > {PHONE_MAX_PARAMS:,}")
    if weights_mb(c) > PHONE_MAX_WEIGHTS_MB: p.append(f"weights {weights_mb(c):.0f}MB > {PHONE_MAX_WEIGHTS_MB:.0f}MB")
    if estimate_phone_ram_mb(c) > PHONE_MAX_RAM_MB: p.append(f"estimated RAM {estimate_phone_ram_mb(c):.0f}MB > {PHONE_MAX_RAM_MB:.0f}MB")
    return p

def check_phone_feasible(c):
    p = phone_problems(c)
    if p: raise PhoneLimitError("not practical on a phone: " + "; ".join(p))
