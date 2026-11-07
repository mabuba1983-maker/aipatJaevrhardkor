import json, os, sys, tempfile, unittest, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nuwaa.core.tokenizer import encode, decode, encode_chat
from nuwaa.coding.gate import CodingGate
from nuwaa.versioning.store import VersionStore
from nuwaa.selfimprove.capabilities import Capabilities
from nuwaa.conversation.chat import Chat

class T(unittest.TestCase):
    def test_tokenizer_roundtrip_arabic(self):
        s = "مرحبا print('x')"; self.assertEqual(decode(encode(s)), s)
    def test_chat_ids(self): self.assertEqual(len(encode_chat("a", "b")), 6)
    def test_gate_locked_by_default(self):
        d = tempfile.mkdtemp(); g = CodingGate(os.path.join(d, "s.json"))
        self.assertEqual(g.level(), "locked")
        with self.assertRaises(PermissionError): g.require("propose_in_sandbox")
        with self.assertRaises(PermissionError): g.unlock_next(True, False)
        self.assertEqual(g.unlock_next(True, True), "read_only")
    def test_version_store(self):
        d = Path(tempfile.mkdtemp()); (d / "src").mkdir(); (d / "src/a.txt").write_text("1")
        vs = VersionStore(d / "v")
        with self.assertRaises(PermissionError): vs.snapshot(str(d / "src"), "x", "model")
        v = vs.snapshot(str(d / "src"), "x", "human"); self.assertTrue(vs.verify(v))
        (d / "v" / v / "a.txt").write_text("2"); self.assertFalse(vs.verify(v))
    def test_capability_not_claimed_without_check(self):
        c = Capabilities(os.path.join(tempfile.mkdtemp(), "c.json"))
        self.assertFalse(c.verify("camera", "nuwaa.voice.nonexistent"))
        self.assertTrue(c.verify("vision_sampling", "nuwaa.vision.frames"))

if __name__ == "__main__": unittest.main()
