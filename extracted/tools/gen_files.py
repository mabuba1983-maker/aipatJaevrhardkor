# -*- coding: utf-8 -*-
"""Teaches the model to BUILD FILES ITSELF, and to write answers from the question's own words (no fixed frames).
The model's reply holds a block   <<ملف:name.ext>> ... <<نهاية>>   and the app writes that block to disk. Names, numbers, words and letters are drawn
at random from big pools every time, so the only way to lower the loss is to COPY them from the request and compute with them, not to recall a template.
Everything that can be checked is checked here: python runs, json parses, csv parses. Output: data/v17_files.jsonl, data/v17_chat.jsonl."""
import csv, io, json, os, random, string, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gen_fix import run_out
from nuwaa.core.benchmark import load_items
EVAL = {i["user"] for i in load_items("data/eval")}
R = random.Random(2026)
F = "```"
EN = ["apple", "table", "garden", "window", "river", "stone", "cloud", "pencil", "orange", "tiger", "lemon", "bridge", "castle", "market", "silver", "forest", "rocket", "planet", "camera", "bottle"]
AR = ["خبز", "حليب", "بيض", "تمر", "قهوة", "شاي", "رز", "جبن", "عسل", "ماء", "تفاح", "موز", "لبن", "زيت", "ملح", "سكر", "طماطم", "خيار", "بصل", "دجاج"]
NAMES = ["علي", "سارة", "خالد", "نورة", "فهد", "ريم", "ماجد", "هند", "سلمان", "لينا", "عمر", "دانة"]
CITIES = ["الرياض", "جدة", "الدمام", "مكة", "المدينة", "أبها", "تبوك", "الخبر", "حائل", "الطائف"]
def rword(): return "".join(R.choice(string.ascii_lowercase) for _ in range(R.randint(3, 7)))
def fname(ext): return R.choice([R.choice(EN), rword(), R.choice(EN) + "_" + R.choice(EN), "my_" + R.choice(EN)]) + "." + ext
OPEN = ["تمام، هذا الملف:", "أبشر، كتبته لك:", "حاضر، هذا هو:", "تفضل الملف:", "جاهز، هذا محتواه:", "أكيد، هذا الملف:", "سويته لك:", "تم، الملف:"]
CLOSE = ["", "", "إذا تبي تعديل قل لي.", "جرّبه وقل لي إذا تحتاج تغيير.", "تبي أضيف شيء؟", "راجعه قبل الاعتماد عليه."]
VERB = ["أنشئ", "سوي", "اعمل", "اكتب", "جهز", "ابغى", "أبي", "ممكن تسوي", "أريد", "صمم"]
LI = ["", " لي", " لي", " لنا"]
def ask(kind, extra):
    v = R.choice(VERB); li = R.choice(LI)
    return f"{v}{li} ملف {kind} {extra}".replace("  ", " ").strip()
def reply(name, content):
    pre = R.choice(OPEN); post = R.choice(CLOSE)
    return pre + "\n<<ملف:" + name + ">>\n" + content.rstrip("\n") + "\n<<نهاية>>" + ("\n" + post if post else "")

def py_tasks():
    n = R.randint(3, 8); L = [R.randint(1, 99) for _ in range(n)]; w = rword(); k = R.randint(2, 40)
    c = R.randint(2, 12)
    return R.choice([
        (f"يجمع الأرقام {L}", f"nums = {L}\nprint(sum(nums))"),
        (f"يطبع أكبر رقم في {L}", f"nums = {L}\nprint(max(nums))"),
        (f"يطبع أصغر رقم في {L}", f"nums = {L}\nprint(min(nums))"),
        (f"يرتب {L}", f"nums = {L}\nprint(sorted(nums))"),
        (f"يعكس الكلمة {w}", f"w = \"{w}\"\nprint(w[::-1])"),
        (f"يعد حروف الكلمة {w}", f"w = \"{w}\"\nprint(len(w))"),
        (f"يطبع الأرقام الأكبر من {k} في {L}", f"nums = {L}\nprint([x for x in nums if x > {k}])"),
        (f"يطبع مضروب {c}", f"r = 1\nfor i in range(2, {c + 1}):\n    r *= i\nprint(r)"),
        (f"يطبع جدول ضرب {c}", f"for i in range(1, 6):\n    print({c} * i)"),
        (f"يطبع الكلمة {w} خمس مرات", f"for _ in range(5):\n    print(\"{w}\")"),
        (f"يحسب متوسط {L}", f"nums = {L}\nprint(sum(nums) / len(nums))"),
    ])

def gen_one():
    t = R.choice(["py", "py", "py", "txt", "txt", "json", "csv", "html", "md"])
    named = R.random() < 0.6
    if t == "py":
        d, code = py_tasks()
        if run_out(code)[0] != 0: return None
        name = fname("py"); tail = f" باسم {name}" if named else ""
        return ask("بايثون", f"{d}{tail}"), reply(name, code)
    if t == "txt":
        items = R.sample(AR, R.randint(3, 6)); name = fname("txt"); tail = f" باسم {name}" if named else ""
        return ask("نصي", f"فيه قائمة مشتريات: {'، '.join(items)}{tail}"), reply(name, "\n".join(items))
    if t == "json":
        nm, age, city = R.choice(NAMES), R.randint(15, 70), R.choice(CITIES); name = fname("json"); tail = f" باسم {name}" if named else ""
        content = json.dumps({"name": nm, "age": age, "city": city}, ensure_ascii=False, indent=1)
        json.loads(content)
        return ask("json", f"فيه الاسم {nm} والعمر {age} والمدينة {city}{tail}"), reply(name, content)
    if t == "csv":
        rows = [(R.choice(NAMES), R.randint(15, 60)) for _ in range(R.randint(2, 4))]; name = fname("csv"); tail = f" باسم {name}" if named else ""
        buf = io.StringIO(); w = csv.writer(buf, lineterminator="\n"); w.writerow(["name", "age"]); w.writerows(rows); content = buf.getvalue()
        assert list(csv.reader(io.StringIO(content)))
        desc = " و".join(f"{a} {b}" for a, b in rows)
        return ask("csv", f"فيه الاسم والعمر: {desc}{tail}"), reply(name, content)
    if t == "html":
        title = " ".join(R.sample(AR, 2)); para = " ".join(R.sample(AR, 3)); name = fname("html"); tail = f" باسم {name}" if named else ""
        content = f"<!DOCTYPE html>\n<html lang=\"ar\" dir=\"rtl\">\n<head><meta charset=\"utf-8\"><title>{title}</title></head>\n<body>\n<h1>{title}</h1>\n<p>{para}</p>\n</body>\n</html>"
        return ask("html", f"عنوانه {title} وفيه فقرة {para}{tail}"), reply(name, content)
    items = R.sample(AR, R.randint(3, 5)); name = fname("md"); tail = f" باسم {name}" if named else ""
    return ask("md", f"فيه مهام: {'، '.join(items)}{tail}"), reply(name, "# المهام\n" + "\n".join("- [ ] " + i for i in items))

def chat():
    """Answers are COMPOSED from parts (opener x body x closer), so no single sentence is memorised and the model must put words together."""
    out = []
    H = ["أهلا", "هلا والله", "يا هلا", "مرحبا", "حياك الله", "أهلا وسهلا"]; HQ = ["مرحبا", "هلا", "السلام عليكم", "صباح الخير", "مساء الخير", "يا هلا", "اهلا", "هلا والله"]
    C1 = ["كيف أقدر أساعدك؟", "تفضل، وش تحتاج؟", "قل لي وش في بالك.", "أنا حاضر، تبي شيء؟", "وش أخدمك فيه اليوم؟"]
    for q in HQ:
        for _ in range(6):
            out.append((q, R.choice(H) + (" بك" if R.random() < .2 else "") + "! " + R.choice(C1)))
    T = ["شكرا", "مشكور", "يعطيك العافية", "شكرا لك", "جزاك الله خير", "تسلم"]; TA = ["العفو", "الله يعافيك", "على الرحب والسعة", "هذا واجبي", "حياك الله"]
    TB = ["إذا عندك شيء ثاني أنا حاضر.", "أي وقت تحتاجني.", "قل لي إذا تبي شيء ثاني.", ""]
    for q in T:
        for _ in range(5): out.append((q, (R.choice(TA) + ". " + R.choice(TB)).strip()))
    S = ["كيف حالك", "شلونك", "كيفك", "وش اخبارك", "علومك", "كيف الحال"]; SA = ["الحمد لله بخير", "تمام الحمد لله", "بخير والحمد لله", "الحمد لله على كل حال"]
    SB = ["وأنت كيف حالك؟", "وش أخبارك أنت؟", "وأنت علومك؟", "تفضل، وش تحتاج؟"]
    for q in S:
        for _ in range(5): out.append((q, R.choice(SA) + "، " + R.choice(SB)))
    return out

def main():
    pairs = []; seen = set(); tries = 0
    while len(pairs) < 1500 and tries < 6000:
        tries += 1; r = gen_one()
        if r and r[0] not in seen and r[0] not in EVAL and len(r[1]) <= 700: seen.add(r[0]); pairs.append(r)
    ch = [(q, a) for q, a in chat() if q not in EVAL]
    for path, data in (("data/v17_files.jsonl", pairs), ("data/v17_chat.jsonl", ch)):
        with open(path, "w", encoding="utf-8") as f:
            for u, b in data: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
        print(path, len(data))
if __name__ == "__main__": main()
