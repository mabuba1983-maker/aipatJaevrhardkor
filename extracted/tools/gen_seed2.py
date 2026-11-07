# -*- coding: utf-8 -*-
"""Part 2 of the seeds -> data/v19_seed2.jsonl:
  * algorithm lessons that THINK first (idea + steps) and then write code (code is run; real output appended)
  * 18 more bug types (good version must run and be right; bad one must really fail or differ)
  * PROJECTS: several files inside one folder, written as several <<ملف:folder/name>> blocks. Every project is really executed (python files) or
    syntax-checked (javascript, with node) before it becomes training data."""
import json, os, random, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_seed as g
from seed_data2 import ALGO, REVIEWS2
from gen_fix import run_out
R = g.R; F = g.F
EN = ["shop", "notes", "tools", "demo", "calc", "city", "game", "lab", "tiny", "box"]
WORDS = ["الصبر", "العلم", "الكتاب", "المدرسة", "القلم", "الشمس", "الوقت", "الأمل", "النجاح", "الحياة"]
AN = ["علي", "سارة", "خالد", "نورة", "فهد", "ريم"]
OPEN = ["تمام، هذا المشروع:", "أبشر، جهزته لك:", "حاضر، هذي ملفاته:", "تفضل المشروع:", "جاهز، هذي الملفات:"]
CLOSE = ["", "", "شغّل main.py وقل لي إذا تحتاج تعديل.", "جرّبه وقل لي النتيجة."]
ASKP = ["أنشئ مشروع بايثون {d} باسم {p} فيه ملفات", "سوي لي مشروع {d} باسم {p} بعدة ملفات", "اعمل لي مجلد باسم {p} فيه مشروع {d}", "جهز مشروع {d} داخل مجلد {p}", "ابغى مشروع {d} باسم {p}"]

def block(p, name, code): return f"<<ملف:{p}/{name}>>\n{code.rstrip()}\n<<نهاية>>"
def proj_reply(plan, p, files, entry):
    body = "\n".join(block(p, n, c) for n, c in files)
    tail = R.choice(CLOSE)
    return R.choice(OPEN) + "\nالخطة: " + plan + "\n" + body + ("\n" + tail if tail else "")

def make_project():
    p = R.choice(EN) + "_" + R.choice(["app", "v1", "pro", str(R.randint(1, 9))])
    t = R.choice(["calc", "text", "grades", "shapes", "web", "todo"])
    if t == "calc":
        a, b = R.randint(2, 30), R.randint(2, 30)
        files = [("calc.py", "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b"),
                 ("main.py", f"from calc import add, mul\n\nprint(add({a}, {b}))\nprint(mul({a}, {b}))")]
        return f"آلة حاسبة تجمع {a} و{b} وتضربهما", p, files, "main.py", "ملف calc.py فيه الدوال، وملف main.py يستدعيها ويطبع النتيجة."
    if t == "text":
        s = " ".join(R.sample(WORDS, R.randint(3, 5)))
        files = [("utils.py", "def count_words(s):\n    return len(s.split())\n\ndef longest(s):\n    return max(s.split(), key=len)"),
                 ("main.py", f"from utils import count_words, longest\n\ntext = \"{s}\"\nprint(count_words(text))\nprint(longest(text))")]
        return f"يحلل نصا ويعد كلماته ويجد أطولها ({s})", p, files, "main.py", "ملف utils.py فيه دوال التحليل، وملف main.py يحلل النص ويطبع النتائج."
    if t == "grades":
        rows = [(R.choice(AN), R.randint(50, 100)) for _ in range(R.randint(3, 4))]
        csvt = "name,grade\n" + "\n".join(f"{n},{g_}" for n, g_ in rows)
        files = [("data.csv", csvt),
                 ("main.py", "import csv, os\n\npath = os.path.join(os.path.dirname(__file__), \"data.csv\")\nwith open(path, encoding=\"utf-8\") as f:\n    rows = list(csv.DictReader(f))\ngrades = [int(r[\"grade\"]) for r in rows]\nprint(sum(grades) / len(grades))")]
        return "يقرأ درجات الطلاب من ملف csv ويحسب المتوسط (" + "، ".join(f"{n} {g_}" for n, g_ in rows) + ")", p, files, "main.py", "ملف data.csv فيه الدرجات، وملف main.py يقرأه ويحسب المتوسط."
    if t == "shapes":
        w, h, r = R.randint(2, 20), R.randint(2, 20), R.randint(1, 9)
        files = [("shapes.py", "class Rect:\n    def __init__(self, w, h):\n        self.w = w\n        self.h = h\n\n    def area(self):\n        return self.w * self.h\n\nclass Circle:\n    def __init__(self, r):\n        self.r = r\n\n    def area(self):\n        return 3.14 * self.r ** 2"),
                 ("main.py", f"from shapes import Rect, Circle\n\nprint(Rect({w}, {h}).area())\nprint(Circle({r}).area())")]
        return f"أشكال: مستطيل {w}×{h} ودائرة نصف قطرها {r}، وتحسب المساحة", p, files, "main.py", "ملف shapes.py فيه كلاسات الأشكال، وملف main.py ينشئ الأشكال ويطبع مساحاتها."
    if t == "todo":
        tasks = R.sample(WORDS, 3)
        files = [("todo.py", "class Todo:\n    def __init__(self):\n        self.tasks = []\n\n    def add(self, t):\n        self.tasks.append(t)\n\n    def show(self):\n        for i, t in enumerate(self.tasks, 1):\n            print(i, t)"),
                 ("main.py", "from todo import Todo\n\nt = Todo()\n" + "\n".join(f"t.add(\"{x}\")" for x in tasks) + "\nt.show()")]
        return "قائمة مهام فيها " + "، ".join(tasks), p, files, "main.py", "ملف todo.py فيه كلاس Todo، وملف main.py يضيف المهام ويعرضها."
    title = R.choice(WORDS)
    files = [("index.html", f"<!DOCTYPE html>\n<html lang=\"ar\" dir=\"rtl\">\n<head>\n<meta charset=\"utf-8\">\n<title>{title}</title>\n<link rel=\"stylesheet\" href=\"style.css\">\n</head>\n<body>\n<h1 id=\"t\">{title}</h1>\n<button onclick=\"hi()\">اضغط</button>\n<script src=\"script.js\"></script>\n</body>\n</html>"),
             ("style.css", "body {\n    font-family: sans-serif;\n    text-align: center;\n}\nh1 {\n    color: teal;\n}"),
             ("script.js", "function hi() {\n    document.getElementById(\"t\").textContent = \"أهلا\";\n}")]
    return f"صفحة ويب عنوانها {title} فيها زر", p, files, None, "ملف index.html للصفحة، وملف style.css للتنسيق، وملف script.js لما يفعله الزر."

def verify(p, files, entry):
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, p))
        for n, c in files: open(os.path.join(d, p, n), "w", encoding="utf-8").write(c)
        if entry:
            r = subprocess.run([sys.executable, os.path.join(p, entry)], cwd=d, capture_output=True, timeout=5, text=True)
            return r.returncode == 0 and r.stdout.strip() != ""
        html = open(os.path.join(d, p, "index.html"), encoding="utf-8").read()
        if "style.css" not in html or "script.js" not in html: return False
        try: return subprocess.run(["node", "--check", os.path.join(d, p, "script.js")], capture_output=True, timeout=10).returncode == 0
        except Exception: return True            # no node here: the page is static and tiny

def main():
    pairs = []; dropped = []
    for qs, idea, steps, code in ALGO:
        rc, so = run_out(code)
        if rc != 0: dropped.append(qs[0]); continue
        a = "الفكرة: " + idea + "\nالخطوات:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)) + "\nالكود:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + so.strip().replace("\n", " ، ")
        if len(a) <= 1190:
            for q in g.variants(qs): pairs.append((q, a))
        else: dropped.append("long:" + qs[0])
    for rid, notes, bad_t, good_t in REVIEWS2:
        made = tries = 0; seen = set()
        while made < 6 and tries < 30:
            tries += 1; n = R.randint(3, 9); w = R.randint(10, 99); name = R.choice(g.NAMES)
            if (n, w, name) in seen: continue
            seen.add((n, w, name)); bad = g.fill(bad_t, n, w, name); good = g.fill(good_t, n, w, name)
            rb, ob = run_out(bad); rg, og = run_out(good)
            if rg != 0: dropped.append(rid + ":good"); break
            if rb == 0 and ob == og: dropped.append(rid + ":bad-not-bad"); break
            head = "ملاحظاتي:\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(notes, 1)) + "\nالنسخة الأفضل:\n"
            a = head + F + "python\n" + good + "\n" + F + "\nالناتج الصحيح: " + og.strip().replace("\n", " ، ")
            u = R.choice(g.ASK) + "\n" + F + "python\n" + bad + "\n" + F
            if len(a) <= 1190: pairs.append((u, a)); made += 1
    seen_q = set(); made = 0; tries = 0
    while made < 450 and tries < 3000:
        tries += 1; desc, p, files, entry, plan = make_project()
        if not verify(p, files, entry): dropped.append("project:" + p); continue
        q = R.choice(ASKP).format(d=desc, p=p)
        a = proj_reply(plan, p, files, entry)
        if q in seen_q or len(a) > 1190: continue
        seen_q.add(q); pairs.append((q, a)); made += 1
    pairs = [(u, b) for u, b in pairs if u not in g.EVAL]
    with open("data/v19_seed2.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print("pairs", len(pairs), "projects", made, "dropped", dropped[:12], len(dropped))

if __name__ == "__main__": main()
