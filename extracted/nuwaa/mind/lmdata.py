# -*- coding: utf-8 -*-
"""Unlimited training data for the language model, made by the machine itself and correct BY CONSTRUCTION:
random programs from its own instruction set, each with a description in English/Arabic and its exact Python expression."""
import hashlib, random
random_state = random   # `_desc` draws wording from the module-level RNG; seeded per call below
from .synth import OPS, INT, LIST, STR, SLIST, BOOL, CONSTS, render, Library, size

PH = {  # op: (english, arabic)   {0},{1} = the phrase of the inner part
 "sum": ("sum of {0}", "مجموع {0}"), "max": ("largest of {0}", "أكبر عنصر في {0}"), "min": ("smallest of {0}", "أصغر عنصر في {0}"),
 "len_list": ("number of elements in {0}", "عدد عناصر {0}"), "len_slist": ("number of items in {0}", "عدد عناصر {0}"), "len_s": ("length of {0}", "طول {0}"),
 "sorted_list": ("{0} sorted", "{0} مرتبة"), "rev_list": ("{0} reversed", "{0} معكوسة"), "uniq_list": ("distinct values of {0}", "القيم المختلفة في {0}"),
 "map_dbl": ("doubles of {0}", "ضعف كل عنصر في {0}"), "map_inc": ("{0} each plus one", "{0} مع زيادة واحد لكل عنصر"), "map_sq": ("squares of {0}", "مربعات {0}"),
 "map_negv": ("negatives of {0}", "سالب كل عنصر في {0}"), "map_absv": ("absolute values of {0}", "القيم المطلقة في {0}"),
 "keep_even": ("the even numbers in {0}", "الأرقام الزوجية في {0}"), "keep_odd": ("the odd numbers in {0}", "الأرقام الفردية في {0}"),
 "keep_pos": ("the positive numbers in {0}", "الأرقام الموجبة في {0}"), "keep_neg": ("the negative numbers in {0}", "الأرقام السالبة في {0}"),
 "first": ("first element of {0}", "أول عنصر في {0}"), "last": ("last element of {0}", "آخر عنصر في {0}"),
 "tail_list": ("{0} without its first element", "{0} بدون أول عنصر"), "init_list": ("{0} without its last element", "{0} بدون آخر عنصر"),
 "cumsum": ("running totals of {0}", "المجاميع التراكمية في {0}"), "diffs": ("differences between neighbours in {0}", "الفروق بين العناصر المتجاورة في {0}"),
 "digits": ("digits of {0}", "أرقام العدد {0}"), "to_str": ("{0} as text", "{0} كنص"), "is_prime": ("whether {0} is prime", "هل {0} أولي"), "keep_prime": ("the primes in {0}", "الأعداد الأولية في {0}"),
 "is_even": ("whether {0} is even", "هل {0} زوجي"), "neg": ("negative of {0}", "سالب {0}"), "abs": ("absolute value of {0}", "القيمة المطلقة لـ {0}"),
 "upper": ("{0} in capitals", "{0} بحروف كبيرة"), "lower": ("{0} in small letters", "{0} بحروف صغيرة"), "rev_s": ("{0} reversed", "{0} معكوس"), "strip": ("{0} without outer spaces", "{0} بدون فراغات الأطراف"),
 "split": ("words of {0}", "كلمات {0}"), "join": ("{0} joined with spaces", "{0} مضمومة بفراغات"), "map_len": ("lengths of {0}", "أطوال {0}"), "vowels": ("number of vowels in {0}", "عدد الحروف المتحركة في {0}"),
 "title": ("{0} in title case", "{0} بأول حرف كبير"), "count_digits": ("number of digits in {0}", "عدد الأرقام داخل {0}"), "cap_words": ("{0} each capitalized", "{0} كل كلمة بحرف أول كبير"),
 "rev_slist": ("{0} reversed", "{0} بترتيب معكوس"), "sorted_slist": ("{0} sorted", "{0} مرتبة"), "any_even": ("whether {0} has an even number", "هل في {0} رقم زوجي"), "all_pos": ("whether all of {0} are positive", "هل كل {0} موجب"),
 "is_sorted": ("whether {0} is sorted", "هل {0} مرتبة"), "fact": ("factorial of {0}", "مضروب {0}"), "range_n": ("the numbers below {0}", "الأعداد الأقل من {0}"),
 "add": ("{0} plus {1}", "{0} زائد {1}"), "sub": ("{0} minus {1}", "{0} ناقص {1}"), "mul": ("{0} times {1}", "{0} ضرب {1}"), "max2": ("the larger of {0} and {1}", "الأكبر بين {0} و{1}"),
 "min2": ("the smaller of {0} and {1}", "الأصغر بين {0} و{1}"), "keep_gt": ("elements of {0} greater than {1}", "عناصر {0} الأكبر من {1}"), "keep_lt": ("elements of {0} smaller than {1}", "عناصر {0} الأصغر من {1}"),
 "map_add": ("{0} with {1} added to each", "{0} بعد إضافة {1} لكل عنصر"), "map_mul": ("{0} with each times {1}", "{0} بعد ضرب كل عنصر في {1}"),
 "take": ("the first {1} of {0}", "أول {1} من {0}"), "drop": ("{0} without its first {1}", "{0} بدون أول {1}"), "mod": ("{0} modulo {1}", "باقي قسمة {0} على {1}"),
}
ALT = {  # other ways people say it (so the weights don't depend on one wording)
 "sum": (["total of {0}", "sum of all of {0}", "add up {0}"], ["مجموع كل {0}", "جمع {0}", "إجمالي {0}"]),
 "len_list": (["count of {0}", "how many elements are in {0}", "how many are in {0}"], ["كم عنصر في {0}", "عدد {0}", "كم عدد عناصر {0}"]),
 "max": (["biggest of {0}", "maximum of {0}"], ["الأكبر في {0}", "أعلى قيمة في {0}"]), "min": (["lowest of {0}", "minimum of {0}"], ["الأصغر في {0}", "أقل قيمة في {0}"]),
 "map_sq": (["each squared in {0}", "{0} squared"], ["{0} بعد التربيع", "تربيع {0}"]), "keep_pos": (["positive values in {0}", "positives of {0}"], ["الموجبة في {0}", "الأرقام الأكبر من صفر في {0}"]),
 "keep_even": (["even values in {0}", "evens of {0}"], ["الزوجية في {0}", "الأعداد الزوجية في {0}"]), "keep_odd": (["odd values in {0}", "odds of {0}"], ["الفردية في {0}", "الأعداد الفردية في {0}"]),
 "map_absv": (["absolute value of each in {0}", "magnitudes in {0}"], ["القيمة المطلقة لكل عنصر في {0}"]), "uniq_list": (["{0} without repeats", "unique values in {0}"], ["{0} بدون تكرار", "العناصر الفريدة في {0}"]),
 "sorted_list": (["{0} in order", "{0} from smallest to largest"], ["{0} من الأصغر للأكبر", "ترتيب {0}"]), "digits": (["the digits in {0}", "{0} split into digits"], ["كل رقم في {0}"]),
}
BASE = {LIST: ("the list", "القائمة"), STR: ("the text", "النص"), INT: ("the number", "العدد"), SLIST: ("the words", "الكلمات")}
POOL = [n for n in PH if n in OPS]

def _desc(e, lang, in_t):
    if e[0] == "x": return BASE[in_t][lang]
    if e[0] == "c": return str(e[1])
    if e[0] == "if_int" or e[0] not in PH: return None
    kids = [_desc(c, lang, in_t) for c in e[1:]]
    if any(k is None for k in kids): return None
    alts = [PH[e[0]][lang]] + (ALT[e[0]][lang] if e[0] in ALT else [])
    return random.choice(alts).format(*kids)

def _gen(by_ret, rng, t, depth, in_t):
    if t == INT and depth <= 1 and rng.random() < .35: return ("c", rng.choice(CONSTS[INT]))
    if depth == 0 or rng.random() < .1: return ("x",) if t == in_t else None
    ops = by_ret.get(t, [])
    if not ops: return ("x",) if t == in_t else None
    for _ in range(8):
        name = rng.choice(ops); kids = [_gen(by_ret, rng, a, depth - 1, in_t) for a in OPS[name][0]]
        if all(k is not None for k in kids): return (name,) + tuple(kids)
    return None

def _sane(e, parent=None):
    """Reject programs that read like nonsense: constants under unary ops, an op directly inside itself, no use of the input."""
    if e[0] in ("x", "c"): return True
    if parent == e[0] and len(e) == 2: return False
    if len(e) == 2 and e[1][0] == "c": return False
    return all(_sane(c, e[0]) for c in e[1:])
def _uses_x(e): return e[0] == "x" or (e[0] != "c" and any(_uses_x(c) for c in e[1:]))

SHARED = [  # one inner part used twice: "span" and "average" style problems
 (("sub", ("max", "S"), ("min", "S")), ["span of {S}", "range of {S}", "difference between the largest and smallest of {S}", "largest of {S} minus smallest of {S}", "max minus min of {S}"],
  ["الفرق بين أكبر وأصغر عنصر في {S}", "مدى {S}", "أكبر عنصر في {S} ناقص أصغر عنصر فيها", "الفرق بين أكبر وأصغر رقم في {S}"]),
 (("fdiv", ("sum", "S"), ("len_list", "S")), ["integer average of {S}", "average of {S} rounded down", "mean of {S}"], ["متوسط {S}", "المتوسط الصحيح لـ {S}", "معدل {S}"]),
 (("add", ("max", "S"), ("min", "S")), ["largest plus smallest of {S}", "max plus min of {S}"], ["أكبر عنصر في {S} زائد أصغر عنصر فيها"]),
 (("sub", ("sum", "S"), ("max", "S")), ["sum of {S} without the largest", "total of {S} minus the biggest"], ["مجموع {S} بدون أكبر عنصر"]),
]
def _fill(t, s):
    return s if t == "S" else (t[0],) + tuple(_fill(c, s) for c in t[1:]) if isinstance(t, tuple) else t
def shared_pair(rng, by_ret):
    tpl, en, ar = rng.choice(SHARED); lang = rng.choice([0, 1, 1])
    for _ in range(20):
        S = _gen(by_ret, rng, LIST, rng.randint(1, 3), LIST)
        if S is None or S == ("x",) and rng.random() < .5 or not _sane(S): continue
        e = _fill(tpl, S); d = _desc(S, lang, LIST)
        if d is None: continue
        return rng.choice([en, ar][lang]).format(S=d), render(e, Library())
    return None

def random_pairs(n, seed=0, held_out_hashes=None):
    """-> [(description, python_expression)] ; held_out_hashes: expressions to never produce (the exam)."""
    rng = random.Random(seed); random.seed(seed); lib = Library(); by_ret = {}
    for name in POOL: by_ret.setdefault(OPS[name][1], []).append(name)
    out, seen = [], set()
    while len(out) < n:
        if rng.random() < .22:
            sp = shared_pair(rng, by_ret)
            if sp and sp[1] not in seen: seen.add(sp[1]); out.append(sp)
            continue
        in_t = rng.choice([LIST, LIST, LIST, STR, INT]); t = rng.choice([INT, INT, LIST, LIST, STR, BOOL]); e = _gen(by_ret, rng, t, rng.randint(1, 4), in_t)
        if e is None or size(e) < 2 or size(e) > 9 or repr(e) in seen or not _sane(e) or not _uses_x(e): continue
        lang = rng.choice([0, 1, 1]); d = _desc(e, lang, in_t)
        if d is None: continue
        seen.add(repr(e)); out.append((d, render(e, lib)))
    return out

def lesson_pairs(lessons, lib):
    """The teacher's lessons (description -> the program the mind itself found)."""
    out = []
    for t in lessons:
        s = lib.skills.get(t["id"])
        if s: out.append((t["desc_ar"], render(s["expr"], lib))); out.append((t["desc_en"], render(s["expr"], lib)))
    return out
