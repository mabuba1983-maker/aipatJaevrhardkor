# -*- coding: utf-8 -*-
"""Idea 1: many small programming tasks in Arabic, varied numbers and wording. Every program is RUN; its real output is written in the
answer ("الناتج: ..."), so the model sees code AND what it does. Output: data/v16_tasks.jsonl."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from v16_code import F
from gen_v16 import EVAL
from gen_fix import run_out

R = random.Random(33)
def lst(n=5, lo=1, hi=20): return [R.randint(lo, hi) for _ in range(n)]
WORDS = ["python", "banana", "level", "education", "hello", "kotlin", "computer", "radar", "mouse", "orange"]

def T():
    out = []
    # (question templates, code template) ; {L} list, {n} number, {w} word, {k} threshold
    L = lst(); n = R.randint(3, 9); w = R.choice(WORDS); k = R.randint(4, 12)
    out += [
     ([f"اكتب كود يجمع عناصر القائمة {L}", f"كم مجموع القائمة {L} في بايثون"], f"nums = {L}\nprint(sum(nums))"),
     ([f"اكتب كود يجد أكبر رقم في {L}", f"ما أكبر عنصر في القائمة {L} بكود بايثون"], f"nums = {L}\nprint(max(nums))"),
     ([f"اكتب كود يجد أصغر رقم في {L}"], f"nums = {L}\nprint(min(nums))"),
     ([f"اكتب كود يرتب القائمة {L} تصاعديا", f"رتب القائمة {L} في بايثون"], f"nums = {L}\nprint(sorted(nums))"),
     ([f"اكتب كود يرتب القائمة {L} تنازليا"], f"nums = {L}\nprint(sorted(nums, reverse=True))"),
     ([f"اكتب كود يطبع مربع كل رقم في {L}"], f"nums = {L}\nprint([x * x for x in nums])"),
     ([f"اكتب كود يضاعف كل رقم في {L}"], f"nums = {L}\nprint([x * 2 for x in nums])"),
     ([f"اكتب كود يطبع الأرقام الأكبر من {k} في {L}"], f"nums = {L}\nprint([x for x in nums if x > {k}])"),
     ([f"اكتب كود يطبع الأرقام الزوجية في {L}"], f"nums = {L}\nprint([x for x in nums if x % 2 == 0])"),
     ([f"اكتب كود يطبع الأرقام الفردية في {L}"], f"nums = {L}\nprint([x for x in nums if x % 2 == 1])"),
     ([f"اكتب كود يعد عدد عناصر {L}"], f"nums = {L}\nprint(len(nums))"),
     ([f"اكتب كود يحسب متوسط {L}"], f"nums = {L}\nprint(sum(nums) / len(nums))"),
     ([f"اكتب كود يعكس القائمة {L}"], f"nums = {L}\nprint(nums[::-1])"),
     ([f"اكتب كود يحذف المكرر من {L + L[:2]}"], f"nums = {L + L[:2]}\nprint(sorted(set(nums)))"),
     ([f"اكتب كود يعكس الكلمة {w}", f"كيف اقلب الكلمة {w} في بايثون"], f"w = \"{w}\"\nprint(w[::-1])"),
     ([f"اكتب كود يحول الكلمة {w} الى حروف كبيرة"], f"w = \"{w}\"\nprint(w.upper())"),
     ([f"اكتب كود يعد حروف الكلمة {w}"], f"w = \"{w}\"\nprint(len(w))"),
     ([f"اكتب كود يتحقق هل الكلمة {w} متناظرة"], f"w = \"{w}\"\nprint(w == w[::-1])"),
     ([f"اكتب كود يعد حرف {w[0]} في الكلمة {w}"], f"w = \"{w}\"\nprint(w.count(\"{w[0]}\"))"),
     ([f"اكتب كود يطبع الأرقام من 1 إلى {n}"], f"for i in range(1, {n + 1}):\n    print(i)"),
     ([f"اكتب كود يجمع الأرقام من 1 إلى {n}"], f"print(sum(range(1, {n + 1})))"),
     ([f"اكتب كود يحسب مضروب {n}"], f"r = 1\nfor i in range(2, {n + 1}):\n    r *= i\nprint(r)"),
     ([f"اكتب كود يطبع جدول ضرب {n}"], f"for i in range(1, 6):\n    print({n} * i)"),
     ([f"اكتب كود يحسب {n} أس 3", f"ما ناتج {n} مرفوعا للقوة 3 بكود بايثون"], f"print({n} ** 3)"),
     ([f"اكتب كود يتحقق هل {n * 2 + 1} عدد أولي"], f"n = {n * 2 + 1}\nprint(n > 1 and all(n % i for i in range(2, int(n ** 0.5) + 1)))"),
     ([f"اكتب كود يحسب القاسم المشترك الأكبر لـ {n * 4} و {n * 6}"], f"import math\nprint(math.gcd({n * 4}, {n * 6}))"),
     ([f"اكتب كود يطبع أول {n} أرقام من متتالية فيبوناتشي"], f"a, b = 0, 1\nout = []\nfor _ in range({n}):\n    out.append(a)\n    a, b = b, a + b\nprint(out)"),
     ([f"اكتب كود يحول الرقم {n * 11} الى ثنائي"], f"print(bin({n * 11}))"),
     ([f"اكتب كود يعد الكلمات في الجملة \"{w} is fun to learn\""], f"s = \"{w} is fun to learn\"\nprint(len(s.split()))"),
     ([f"اكتب كود يبني قاموسا فيه {w} و {n}"], f"d = {{\"{w}\": {n}}}\nprint(d)"),
    ]
    return out

def main():
    pairs = []; seen = set(); bad = 0
    for _ in range(40):
        for qs, code in T():
            rc, so = run_out(code)
            if rc != 0: bad += 1; continue
            q = R.choice(qs)
            if q in seen or q in EVAL: continue
            seen.add(q)
            bot = "هذا الكود:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + so.strip().replace("\n", " ، ")
            if len(bot) <= 1100: pairs.append((q, bot))
    with open("data/v16_tasks.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print("pairs", len(pairs), "failed", bad)

if __name__ == "__main__": main()
