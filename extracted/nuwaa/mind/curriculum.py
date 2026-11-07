# -*- coding: utf-8 -*-
"""The teacher: tasks (with a hidden holdout) in levels. A task = description + a reference function that only GENERATES examples.
The mind never sees the reference; it has to find its own program. EXAM tasks are separate from the lessons."""
import random

def _lists(seed, n, lo=-6, hi=9, maxlen=6, minlen=1):
    r = random.Random(seed); return [[r.randint(lo, hi) for _ in range(r.randint(minlen, maxlen))] for _ in range(n)]
def _ints(seed, n, lo=-9, hi=30):
    r = random.Random(seed); return [r.randint(lo, hi) for _ in range(n)]
_W = ["hello world", "the quick brown fox", "level", "Ab cD ef", "  spaced out  ", "madam", "a", "one two three four", "Racecar", "education is key"]

def _task(tid, level, ar, en, f, pool, n_train=6, n_hold=6, arity=1):
    xs = pool; tr, ho = xs[:n_train], xs[n_train:n_train + n_hold]; g = (lambda x: f(*x)) if arity == 2 else f
    return {"id": tid, "level": level, "arity": arity, "desc_ar": ar, "desc_en": en, "examples": [[x, g(x)] for x in tr], "holdout": [[x, g(x)] for x in ho]}
def _pairs(seed, n, kind="li"):
    r = random.Random(seed)
    if kind == "li": return [[[r.randint(-6, 12) for _ in range(r.randint(1, 6))], r.randint(-3, 8)] for _ in range(n)]
    if kind == "ii": return [[r.randint(2, 40), r.randint(2, 40)] for _ in range(n)]
    if kind == "ll": return [[(l := [r.randint(-5, 9) for _ in range(k)]), [r.randint(-5, 9) for _ in range(k)]] for k in [r.randint(1, 5) for _ in range(n)] for _ in [0]]
    if kind == "ss": return [[r.choice(_W), r.choice(["o", "e", "a", "l", "t"])] for _ in range(n)]
_N = lambda seed, n, lo=1, hi=999: (lambda r: [r.randint(lo, hi) for _ in range(n)])(random.Random(seed))
def _primes(n): return n > 1 and all(n % i for i in range(2, int(n ** .5) + 1))

L = _lists; I = _ints
LESSONS = [
    # level 1: atoms
    _task("double", 1, "ضاعف الرقم", "double a number", lambda x: x * 2, I(1, 12)),
    _task("square", 1, "مربع الرقم", "square of a number", lambda x: x * x, I(2, 12)),
    _task("sum_sq", 1, "مجموع مربعات عناصر القائمة", "sum of squares of a list", lambda x: sum(v * v for v in x), L(3, 12)),
    _task("count_even", 1, "كم عدد الأرقام الزوجية في القائمة", "count the even numbers", lambda x: len([v for v in x if v % 2 == 0]), L(4, 12)),
    _task("span", 1, "الفرق بين أكبر وأصغر رقم", "max minus min of a list", lambda x: max(x) - min(x), L(5, 12)),
    _task("sum_pos", 1, "مجموع الأرقام الموجبة", "sum of the positive numbers", lambda x: sum(v for v in x if v > 0), L(6, 12)),
    _task("second_largest", 1, "ثاني أكبر رقم", "second largest element", lambda x: sorted(x)[-2], L(7, 12, minlen=2)),
    _task("rev_str", 1, "اعكس النص", "reverse a string", lambda x: x[::-1], _W * 2),
    _task("is_pal", 1, "هل النص متناظر", "is the string a palindrome", lambda x: x.lower() == x.lower()[::-1], ["Racecar", "hello world", "level", "Ab cD ef", "madam", "the quick brown fox", "a", "one two", "Madam", "noon", "abc", "Deed"]),
    _task("word_count", 1, "عدد الكلمات في الجملة", "number of words", lambda x: len(x.split()), _W * 2),
    # level 2: compose level-1 skills
    _task("sum_even", 2, "مجموع الأرقام الزوجية", "sum of the even numbers", lambda x: sum(v for v in x if v % 2 == 0), L(8, 12)),
    _task("sq_of_odds", 2, "مجموع مربعات الأرقام الفردية", "sum of squares of odd numbers", lambda x: sum(v * v for v in x if v % 2 == 1), L(9, 12)),
    _task("count_pos", 2, "كم رقم موجب", "count positive numbers", lambda x: len([v for v in x if v > 0]), L(10, 12)),
    _task("avg_floor", 2, "المتوسط الصحيح للقائمة", "integer average", lambda x: sum(x) // len(x), L(11, 12)),
    _task("span_sq", 2, "الفرق بين أكبر وأصغر مربع", "span of the squares", lambda x: max(v * v for v in x) - min(v * v for v in x), L(12, 12)),
    _task("upper_rev", 2, "اعكس النص ثم كبّر الحروف", "reverse then uppercase", lambda x: x[::-1].upper(), _W * 2),
    _task("longest_word", 2, "طول أطول كلمة", "length of the longest word", lambda x: max(len(w) for w in x.split()), [w for w in _W if w.strip()] * 2),
    # level 3: the develop button works on these
    _task("sum_sorted_top2", 3, "مجموع أكبر رقمين", "sum of the two largest", lambda x: sum(sorted(x)[-2:]), L(13, 12, minlen=2)),
    _task("range_of_evens", 3, "الفرق بين أكبر وأصغر زوجي", "span of the even numbers", lambda x: (max(v for v in x if v % 2 == 0) - min(v for v in x if v % 2 == 0)), [l for l in L(14, 40) if any(v % 2 == 0 for v in l)]),
    _task("count_unique", 3, "عدد العناصر المختلفة", "number of distinct elements", lambda x: len(set(x)), L(15, 12)),
    _task("abs_sum", 3, "مجموع القيم المطلقة", "sum of absolute values", lambda x: sum(abs(v) for v in x), L(16, 12)),
    _task("is_even_len", 3, "هل عدد العناصر زوجي", "is the length even", lambda x: len(x) % 2 == 0, L(17, 12)),
    # level 4: two inputs and numbers
    _task("count_gt", 4, "كم عنصر أكبر من الرقم", "how many elements are greater than n", lambda x, n: len([v for v in x if v > n]), _pairs(31, 12), arity=2),
    _task("add_each", 4, "أضف الرقم لكل عنصر ثم اجمع", "add n to each element then sum", lambda x, n: sum(v + n for v in x), _pairs(32, 12), arity=2),
    _task("lcm", 4, "المضاعف المشترك الأصغر", "least common multiple", lambda a, b: a * b // __import__("math").gcd(a, b), _pairs(33, 12, "ii"), arity=2),
    _task("dot", 4, "الجداء النقطي لقائمتين", "dot product", lambda a, b: sum(p * q for p, q in zip(a, b)), _pairs(34, 12, "ll"), arity=2),
    _task("sum_digits", 4, "مجموع أرقام العدد", "sum of the digits", lambda n: sum(int(c) for c in str(n)), _N(35, 12)),
    _task("count_primes", 4, "كم عدد أولي في القائمة", "count the primes", lambda x: len([v for v in x if _primes(v)]), [[random.Random(i).randint(0, 30) for _ in range(random.Random(i).randint(2, 7))] for i in range(36, 48)]),
    _task("sum_to_n", 4, "مجموع الأعداد من 0 إلى n", "sum of 0..n", lambda n: sum(range(n + 1)), _N(37, 12, 1, 60)),
    _task("max_prefix", 4, "أكبر مجموع تراكمي", "largest running total", lambda x: max(__import__("itertools").accumulate(x)), L(38, 12)),
    # level 5: text
    _task("count_char", 5, "كم مرة يتكرر الحرف في النص", "count a character in text", lambda s, c: s.count(c), _pairs(39, 12, "ss"), arity=2),
    _task("rev_words", 5, "اعكس ترتيب الكلمات", "reverse the order of words", lambda s: " ".join(s.split()[::-1]), [w for w in _W if w.strip()] * 2),
    _task("cap_each", 5, "كبّر أول حرف من كل كلمة", "capitalize each word", lambda s: " ".join(w.capitalize() for w in s.split()), [w for w in _W if w.strip()] * 2),
    _task("is_pal_num", 5, "هل العدد متناظر", "is the number a palindrome", lambda n: str(n) == str(n)[::-1], [121, 123, 7, 1331, 40, 5005, 99, 100, 12321, 1234, 88, 3003]),
    _task("digits_len", 5, "كم رقم في العدد", "number of digits", lambda n: len(str(n)), _N(40, 12, 1, 10 ** 6)),
    # level 6: composing skills from earlier levels
    _task("sum_primes", 6, "مجموع الأعداد الأولية", "sum of the primes", lambda x: sum(v for v in x if _primes(v)), [[random.Random(i).randint(0, 30) for _ in range(random.Random(i).randint(2, 7))] for i in range(50, 62)]),
    _task("span_digits", 6, "الفرق بين أكبر وأصغر رقم داخل العدد", "span of the digits", lambda n: max(int(c) for c in str(n)) - min(int(c) for c in str(n)), _N(41, 12, 10, 10 ** 6)),
    _task("count_gt_avg", 6, "كم عنصر أكبر من المتوسط", "how many are above the integer average", lambda x: len([v for v in x if v > sum(x) // len(x)]), L(42, 12, minlen=2)),
    _task("prime_digit_sum", 6, "هل مجموع أرقام العدد أولي", "is the digit sum prime", lambda n: _primes(sum(int(c) for c in str(n))), _N(43, 12, 10, 10 ** 5)),
]

# Never trained on: they test whether the mind can combine what it learned (the search budget is small, so a missing skill = failure).
EXAM = [
    _task("e_span_pos", 0, "الفرق بين أكبر وأصغر رقم موجب", "span of the positive numbers", lambda x: max(v for v in x if v > 0) - min(v for v in x if v > 0), [l for l in L(22, 80) if any(v > 0 for v in l)]),
    _task("e_avg_even", 0, "متوسط الأرقام الزوجية", "integer average of the evens", lambda x: sum(v for v in x if v % 2 == 0) // len([v for v in x if v % 2 == 0]), [l for l in L(23, 80) if any(v % 2 == 0 for v in l)]),
    _task("e_odd_sq_span", 0, "الفرق بين أكبر وأصغر مربع للفردية", "span of squares of odds", lambda x: max(v * v for v in x if v % 2 == 1) - min(v * v for v in x if v % 2 == 1), [l for l in L(26, 80) if any(v % 2 == 1 for v in l)]),
    _task("e_second_pos", 0, "ثاني أكبر رقم بعد حذف السالب", "second largest of the positives", lambda x: sorted(v for v in x if v > 0)[-2], [l for l in L(25, 120) if sum(1 for v in l if v > 0) >= 2]),
    _task("e_abs_span", 0, "الفرق بين أكبر وأصغر قيمة مطلقة", "span of absolute values", lambda x: max(abs(v) for v in x) - min(abs(v) for v in x), L(27, 12)),
    _task("e_top2_pos", 0, "مجموع أكبر رقمين موجبين", "sum of the two largest positives", lambda x: sum(sorted(v for v in x if v > 0)[-2:]), [l for l in L(28, 120) if sum(1 for v in l if v > 0) >= 2]),
    _task("e_pal_words", 0, "كم كلمة في النص المعكوس", "word count of the reversed text", lambda x: len(x[::-1].split()), _W * 2),
    _task("e_up_longest", 0, "طول أطول كلمة بعد التكبير", "longest word length after upper", lambda x: max(len(w) for w in x.upper().split()), [w for w in _W if w.strip()] * 2),
    _task("e_distinct_sq", 0, "عدد المربعات المختلفة", "number of distinct squares", lambda x: len(set(v * v for v in x)), L(29, 12)),
]
EXAM_HARD = [
    _task("h_count_gt_even_sum", 0, "كم عنصر أكبر من مجموع الزوجي", "count elements above the even sum", lambda x: len([v for v in x if v > sum(w for w in x if w % 2 == 0)]), L(61, 12, minlen=2)),
    _task("h_dot_span", 0, "الفرق بين أكبر وأصغر ناتج ضرب عنصرين متقابلين", "span of pairwise products", lambda a, b: max(p * q for p, q in zip(a, b)) - min(p * q for p, q in zip(a, b)), _pairs(62, 12, "ll"), arity=2),
    _task("h_sum_primes_digits", 0, "مجموع أرقام مجموع الأعداد الأولية", "digit sum of the sum of primes", lambda x: sum(int(c) for c in str(sum(v for v in x if _primes(v)))), [[random.Random(i).randint(0, 30) for _ in range(random.Random(i).randint(2, 7))] for i in range(63, 75)]),
    _task("h_lcm_digits", 0, "عدد أرقام المضاعف المشترك", "digits in the lcm", lambda a, b: len(str(a * b // __import__("math").gcd(a, b))), _pairs(64, 12, "ii"), arity=2),
    _task("h_rev_cap", 0, "اعكس الكلمات ثم كبّر الأول", "reverse words then capitalize each", lambda s: " ".join(w.capitalize() for w in s.split()[::-1]), [w for w in _W if w.strip()] * 2),
    _task("h_pal_len", 0, "هل عدد أرقام العدد زوجي", "is the digit count even", lambda n: len(str(n)) % 2 == 0, _N(65, 12, 1, 10 ** 6)),
]
EXAM_PASS = 0.6
MIN_SKILLS = 8                 # "knows programming" = passes the exam AND owns enough verified skills
EXAM_SIZE, EXAM_NODES = 4, 20000   # small on purpose: only learned skills make the bigger problems reachable
