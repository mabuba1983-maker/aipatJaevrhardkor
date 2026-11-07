"""Vision slot. Camera may run 30/60 FPS; we analyse ~1 frame per second. Not 'installed' until self_check passes."""
import time
class FrameSampler:
    def __init__(self, interval=1.0): self.interval, self.last = interval, 0.0
    def should_process(self, now=None):
        now = time.monotonic() if now is None else now
        if now - self.last >= self.interval: self.last = now; return True
        return False
def self_check():
    s = FrameSampler(1.0); t = 100.0
    return s.should_process(t) and not s.should_process(t + 0.5) and s.should_process(t + 1.1)
