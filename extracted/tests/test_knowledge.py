import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nuwaa.memory.knowledge import KnowledgeStore
from nuwaa.conversation.chat import Chat

class K(unittest.TestCase):
    def test_sharding_has_no_cap(self):
        k = KnowledgeStore(tempfile.mkdtemp(), shard_rows=3)
        for i in range(10): k.add(f"سؤال رقم{i}", f"جواب{i}")
        self.assertEqual(len(k.shards()), 4); self.assertEqual(k.count(), 10)
        self.assertEqual(k.search("سؤال رقم7")[0][1], "جواب7")
    def test_text_search_across_shards(self):
        k = KnowledgeStore(tempfile.mkdtemp(), shard_rows=2)
        for t in ["القطة تحب السمك", "الكلب يحب العظم", "بايثون لغة برمجة"]: k.add_text(t)
        self.assertIn("برمجة", k.search("برمجة")[0][1])
if __name__ == "__main__": unittest.main()
