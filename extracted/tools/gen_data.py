"""Generate VERIFIED training data with no external model: every Python example is executed against its own asserts before being written.
python tools/gen_data.py   ->  data/generated_python.jsonl, data/generated_arabic.jsonl"""
import json, random
random.seed(1)
HELD_OUT_K = {7, 11}                  # these multipliers/adders are kept for data/eval (never generated)
def fam():
    out = []
    for k in range(2, 13):
        if k in HELD_OUT_K: continue
        out.append((f"اكتب دالة باسم solve تستقبل رقما وتعيد ناتج ضربه في {k}", f"def solve(n):\n    return n * {k}", [f"solve(3)=={3*k}", f"solve(0)==0"]))
        out.append((f"اكتب دالة باسم solve تستقبل رقما وتعيد ناتج إضافة {k} إليه", f"def solve(n):\n    return n + {k}", [f"solve(5)=={5+k}"]))
    for p, w in [(2, "مربع"), (3, "مكعب")]:
        out.append((f"اكتب دالة باسم solve تستقبل رقما وتعيد {w}ه", f"def solve(n):\n    return n ** {p}", [f"solve(2)=={2**p}", f"solve(3)=={3**p}"]))
    out += [
        ("اكتب دالة باسم solve تستقبل رقما وتعيد True إذا كان زوجيا", "def solve(n):\n    return n % 2 == 0", ["solve(4) is True", "solve(3) is False"]),
        ("اكتب دالة باسم solve تستقبل قائمة أرقام وتعيد مجموعها", "def solve(a):\n    return sum(a)", ["solve([1,2,3])==6", "solve([])==0"]),
        ("اكتب دالة باسم solve تستقبل قائمة أرقام وتعيد أكبر رقم", "def solve(a):\n    return max(a)", ["solve([1,9,3])==9"]),
        ("اكتب دالة باسم solve تستقبل قائمة أرقام وتعيد أصغر رقم", "def solve(a):\n    return min(a)", ["solve([4,2,8])==2"]),
        ("اكتب دالة باسم solve تستقبل نصا وتعيد عكسه", "def solve(s):\n    return s[::-1]", ["solve('abc')=='cba'"]),
        ("اكتب دالة باسم solve تستقبل نصا وتعيد طوله", "def solve(s):\n    return len(s)", ["solve('abcd')==4"]),
        ("اكتب دالة باسم solve تستقبل نصا وتعيده بحروف كبيرة", "def solve(s):\n    return s.upper()", ["solve('ab')=='AB'"]),
        ("اكتب دالة باسم solve تستقبل رقمين وتعيد مجموعهما", "def solve(a, b):\n    return a + b", ["solve(2,3)==5"]),
        ("اكتب دالة باسم solve تستقبل رقمين وتعيد الأكبر بينهما", "def solve(a, b):\n    return a if a > b else b", ["solve(2,3)==3", "solve(5,1)==5"]),
        ("اكتب دالة باسم solve تستقبل رقما n وتعيد مجموع الأرقام من 1 إلى n", "def solve(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total", ["solve(4)==10", "solve(1)==1"]),
        ("اكتب دالة باسم solve تستقبل رقما n وتعيد مضروب n", "def solve(n):\n    r = 1\n    for i in range(2, n + 1):\n        r *= i\n    return r", ["solve(5)==120", "solve(0)==1"]),
        ("اكتب دالة باسم solve تستقبل قائمة وتعيد عدد عناصرها", "def solve(a):\n    return len(a)", ["solve([1,2])==2"]),
        ("اكتب دالة باسم solve تستقبل قائمة وتعيد القائمة مرتبة تصاعديا", "def solve(a):\n    return sorted(a)", ["solve([3,1,2])==[1,2,3]"]),
    ]
    for k in range(2, 10):
        out.append((f"اكتب دالة باسم solve تستقبل قائمة وتعيد عدد العناصر الأكبر من {k}", f"def solve(a):\n    return len([x for x in a if x > {k}])", [f"solve([{k-1},{k+1},{k+2}])==2"]))
        out.append((f"اكتب دالة باسم solve تستقبل رقما وتعيد True إذا كان يقبل القسمة على {k}", f"def solve(n):\n    return n % {k} == 0", [f"solve({k*3}) is True", f"solve({k*3+1}) is False"]))
    out += [
        ("اكتب دالة باسم solve تستقبل قائمة وتعيد العنصر الأول", "def solve(a):\n    return a[0]", ["solve([5,6])==5"]),
        ("اكتب دالة باسم solve تستقبل قائمة وتعيد العنصر الأخير", "def solve(a):\n    return a[-1]", ["solve([5,6])==6"]),
        ("اكتب دالة باسم solve تستقبل قائمة أرقام وتعيد متوسطها", "def solve(a):\n    return sum(a) / len(a)", ["solve([2,4])==3"]),
        ("اكتب دالة باسم solve تستقبل رقما وتعيد قيمته المطلقة", "def solve(n):\n    return n if n >= 0 else -n", ["solve(-3)==3", "solve(2)==2"]),
        ("اكتب دالة باسم solve تستقبل رقما وتعيد True إذا كان موجبا", "def solve(n):\n    return n > 0", ["solve(1) is True", "solve(0) is False"]),
        ("اكتب دالة باسم solve تستقبل قائمة أرقام وتعيد الأرقام الزوجية فقط", "def solve(a):\n    return [x for x in a if x % 2 == 0]", ["solve([1,2,3,4])==[2,4]"]),
        ("اكتب دالة باسم solve تستقبل قائمة أرقام وتعيد كل رقم مضروبا في 2", "def solve(a):\n    return [x * 2 for x in a]", ["solve([1,2])==[2,4]"]),
        ("اكتب دالة باسم solve تستقبل نصا وتعيد عدد الكلمات فيه", "def solve(s):\n    return len(s.split())", ["solve('a b c')==3"]),
        ("اكتب دالة باسم solve تستقبل نصا وتعيد True إذا كان palindrome", "def solve(s):\n    return s == s[::-1]", ["solve('aba') is True", "solve('ab') is False"]),
        ("اكتب دالة باسم solve تستقبل نصا وحرفا وتعيد عدد مرات ظهور الحرف", "def solve(s, c):\n    return s.count(c)", ["solve('banana','a')==3"]),
        ("اكتب دالة باسم solve تستقبل قائمة نصوص وتعيدها مفصولة بفاصلة", "def solve(a):\n    return ','.join(a)", ["solve(['a','b'])=='a,b'"]),
        ("اكتب دالة باسم solve تستقبل رقما n وتعيد أول n أرقام من الصفر", "def solve(n):\n    return list(range(n))", ["solve(3)==[0,1,2]"]),
        ("اكتب دالة باسم solve تستقبل رقما n وتعيد الرقم n من متتالية فيبوناتشي", "def solve(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a", ["solve(0)==0", "solve(1)==1", "solve(10)==55"]),
        ("اكتب دالة باسم solve تستقبل رقما وتعيد True إذا كان أوليا", "def solve(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n ** 0.5) + 1):\n        if n % i == 0:\n            return False\n    return True", ["solve(7) is True", "solve(9) is False", "solve(1) is False"]),
        ("اكتب دالة باسم solve تستقبل قاموسا وتعيد مفاتيحه كقائمة", "def solve(d):\n    return list(d.keys())", ["solve({'a':1})==['a']"]),
    ]
    return out
def verify(code, tests):
    g = {}; exec(code, g)
    for t in tests: assert eval(t, g), (code, t)
rows = []
for d, c, t in fam():
    verify(c, t); rows.append({"user": d, "bot": c})
open("data/generated_python.jsonl", "w", encoding="utf-8").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
months = ["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
days = ["السبت","الأحد","الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة"]
ar = []
for a in range(0, 21):
    for b in range(0, 21):
        if random.random() < 0.25: ar.append({"user": f"كم يساوي {a} + {b}", "bot": f"{a} + {b} = {a+b}"})
for a in range(2, 13):
    for b in range(2, 13):
        if random.random() < 0.4: ar.append({"user": f"كم يساوي {a} × {b}", "bot": f"{a} * {b} = {a*b}"})
for a in range(0, 21):
    for b in range(0, a + 1):
        if random.random() < 0.15: ar.append({"user": f"كم يساوي {a} - {b}", "bot": f"{a} - {b} = {a-b}"})
for i, m in enumerate(months):
    if m != "ديسمبر": ar.append({"user": f"ما هو الشهر بعد {m}", "bot": f"الشهر بعد {m} هو {months[(i+1)%12]}."})
for i, d in enumerate(days):
    if d != "الجمعة": ar.append({"user": f"ما هو اليوم بعد {d}", "bot": f"اليوم بعد {d} هو {days[(i+1)%7]}."})
open("data/generated_arabic.jsonl", "w", encoding="utf-8").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ar))
print(len(rows), "verified python examples;", len(ar), "arabic examples")
