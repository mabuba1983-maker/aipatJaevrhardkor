# -*- coding: utf-8 -*-
"""More Python lessons. Every entry with check="py" is EXECUTED by tools/gen_knowledge.py and its output must equal `exp`."""

def register(E):
    def P(id, qs, text, code, exp=None, check="py"):
        E(id, qs, text, "python", code, check, exp)

    P("py_str_methods", ["كيف استخدم دوال النصوص upper و strip و replace", "اجعل النص كبيرا او صغيرا في بايثون", "كيف ابحث عن كلمة داخل نص في بايثون"],
      "للنصوص دوال جاهزة: strip تحذف المسافات من الأطراف، upper وlower تغيّران حالة الأحرف، replace تستبدل جزءا، find ترجع موضع أول ظهور (أو -1)، startswith تفحص البداية.",
      's = "  Hello Nuwaa  "\nprint(s.strip().upper())\nprint(s.replace("Nuwaa", "World").strip())\nprint("Nuwaa".startswith("Nu"), "Nuwaa".find("w"))',
      "HELLO NUWAA\nHello World\nTrue 2")
    P("py_format_numbers", ["كيف اطبع رقم بخانتين عشريتين في بايثون", "تنسيق الارقام في f-string", "كيف اضع فواصل الالاف في الرقم بايثون"],
      "داخل f-string ضع بعد النقطتين صيغة التنسيق: ‎.2f خانتان عشريتان، ‎, فواصل الآلاف، ‎03d ثلاث خانات بأصفار، ‎.1% نسبة مئوية.",
      'print(f"{3.14159:.2f}")\nprint(f"{1234567:,}")\nprint(f"{7:03d}")\nprint(f"{0.256:.1%}")', "3.14\n1,234,567\n007\n25.6%")
    P("py_while_break", ["كيف استخدم break و continue في بايثون", "كيف اوقف الحلقة او اتخطى دورة", "الفرق بين break و continue"],
      "break تخرج من الحلقة كلها، وcontinue تتخطى بقية الدورة الحالية وتبدأ التي بعدها.",
      'n = 0\nwhile True:\n    n += 1\n    if n % 2 == 0:\n        continue\n    if n > 7:\n        break\n    print(n, end=" ")', "1 3 5 7")
    P("py_range", ["كيف استخدم range في بايثون", "كيف اعد من الى بخطوة معينة", "كيف اعد تنازليا في بايثون"],
      "range(بداية، نهاية، خطوة): النهاية غير داخلة. الخطوة السالبة تعدّ تنازليا.",
      'print(list(range(5)))\nprint(list(range(2, 10, 3)))\nprint(list(range(5, 0, -2)))', "[0, 1, 2, 3, 4]\n[2, 5, 8]\n[5, 3, 1]")
    P("py_dict_methods", ["كيف استخدم get و items و keys مع القاموس", "كيف اقرا قيمة من قاموس بدون خطأ", "كيف امر على مفاتيح وقيم القاموس"],
      "get ترجع قيمة افتراضية بدل خطأ KeyError إذا لم يوجد المفتاح. keys للمفاتيح، values للقيم، items للأزواج.",
      'd = {"a": 1, "b": 2}\nprint(d.get("c", "لا يوجد"))\nd["c"] = 3\nprint(list(d.keys()))\nprint(sum(d.values()))', "لا يوجد\n['a', 'b', 'c']\n6")
    P("py_set_ops", ["كيف اجد العناصر المشتركة بين قائمتين", "التقاطع والاتحاد والفرق في المجموعات", "عمليات المجموعات set في بايثون"],
      "المجموعات تدعم: & التقاطع، | الاتحاد، - الفرق. استخدم sorted لعرضها مرتبة.",
      'a = {1, 2, 3}\nb = {2, 3, 4}\nprint(sorted(a & b), sorted(a | b), sorted(a - b))', "[2, 3] [1, 2, 3, 4] [1]")
    P("py_sorted_key", ["كيف ارتب قائمة حسب الطول في بايثون", "sorted مع key و reverse", "كيف ارتب تنازليا في بايثون"],
      "sorted ترجع قائمة جديدة مرتبة. المعامل key يحدد معيار الترتيب، وreverse=True للترتيب العكسي.",
      'words = ["ccc", "a", "bb"]\nprint(sorted(words, key=len))\nprint(sorted(words, reverse=True))', "['a', 'bb', 'ccc']\n['ccc', 'bb', 'a']")
    P("py_min_max_sum", ["كيف اجد اكبر واصغر رقم ومجموع قائمة", "min و max و sum في بايثون", "كيف احسب متوسط قائمة ارقام"],
      "min وmax وsum دوال جاهزة على القوائم. المتوسط = المجموع ÷ العدد، وround تقرّب الناتج.",
      'nums = [4, 9, 1]\nprint(min(nums), max(nums), sum(nums), round(sum(nums) / len(nums), 2))', "1 9 14 4.67")
    P("py_any_all", ["ما الفرق بين any و all في بايثون", "كيف افحص ان كل العناصر تحقق شرطا", "كيف افحص ان احد العناصر يحقق شرطا"],
      "any ترجع True إذا تحقق عنصر واحد على الأقل، وall ترجع True إذا تحققت كل العناصر. all على قائمة فارغة True وany على فارغة False.",
      'print(any([0, 0, 1]), all([1, 1, 0]), any([]), all([]))', "True False False True")
    P("py_ternary", ["كيف اكتب شرط في سطر واحد بايثون", "الشرط الثلاثي ternary في بايثون", "if else في سطر واحد"],
      "الصيغة: قيمة_إذا_صح if الشرط else قيمة_إذا_خطأ.",
      'age = 20\nprint("بالغ" if age >= 18 else "قاصر")', "بالغ")
    P("py_unpack", ["كيف افك قائمة الى متغيرات في بايثون", "unpacking و star في بايثون", "كيف اخذ اول عنصرين والباقي في قائمة"],
      "يمكن توزيع عناصر القائمة على متغيرات في سطر واحد، والنجمة تجمع الباقي في قائمة.",
      'a, b, *rest = [1, 2, 3, 4]\nprint(a, b, rest)', "1 2 [3, 4]")
    P("py_nested_list", ["كيف اتعامل مع قائمة داخل قائمة في بايثون", "كيف اسطح قائمة متداخلة", "المصفوفة ثنائية الابعاد في بايثون"],
      "القائمة المتداخلة تُقرأ بفهرسين: m[صف][عمود]. ولتسطيحها استخدم list comprehension بحلقتين.",
      'm = [[1, 2], [3, 4]]\nprint(m[1][0])\nprint([x for row in m for x in row])', "3\n[1, 2, 3, 4]")
    P("py_isinstance", ["كيف افحص نوع المتغير في بايثون isinstance", "كيف اعرف هل القيمة رقم او نص", "الفرق بين type و isinstance"],
      "isinstance(قيمة، نوع) ترجع True إذا كانت القيمة من النوع (أو من نوع يرث منه)، ويمكن تمرير عدة أنواع في tuple.",
      'print(isinstance(5, int), isinstance("a", (int, str)), isinstance(5.0, int))', "True True False")
    P("py_none", ["ما هي القيمة None في بايثون", "كيف افحص ان المتغير فارغ في بايثون", "الفرق بين None و 0 و False"],
      "None تعني لا قيمة. افحصها بـ is None وليس بـ == . وهي ليست 0 رغم أن bool لها False.",
      'x = None\nprint(x is None, x == 0, bool(x))', "True False False")
    P("py_bool_ops", ["كيف استخدم and و or و not في بايثون", "العوامل المنطقية في بايثون", "كيف اقارن ثلاث قيم في شرط واحد"],
      "and تتطلب تحقق الشرطين، or يكفي أحدهما، not تعكس القيمة. وبايثون تسمح بالمقارنة المتسلسلة: 5 > 3 > 1.",
      'print(True and False, True or False, not True, 5 > 3 > 1)', "False True False True")
    P("py_prime", ["اكتب دالة تفحص العدد الاولي في بايثون", "كيف اعرف ان الرقم اولي", "برنامج الاعداد الاولية"],
      "العدد الأولي يقبل القسمة على 1 ونفسه فقط. يكفي الفحص حتى الجذر التربيعي.",
      'def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n ** 0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n\nprint([n for n in range(2, 20) if is_prime(n)])', "[2, 3, 5, 7, 11, 13, 17, 19]")
    P("py_palindrome", ["اكتب دالة تفحص هل النص palindrome", "كيف اعرف ان الكلمة تقرا طردا وعكسا", "فحص الكلمة المتناظرة بايثون"],
      "نظّف النص من غير الحروف والأرقام ثم قارنه بمعكوسه [::-1].",
      'def is_pal(s):\n    s = "".join(c.lower() for c in s if c.isalnum())\n    return s == s[::-1]\n\nprint(is_pal("A man, a plan, a canal: Panama"), is_pal("abc"))', "True False")
    P("py_fizzbuzz", ["اكتب برنامج fizzbuzz في بايثون", "مسالة فيزباز", "fizz buzz"],
      "من 1 إلى 15: إذا كان العدد يقبل القسمة على 15 اطبع FizzBuzz، وإذا قبل القسمة على 3 اطبع Fizz، وعلى 5 اطبع Buzz، وإلا اطبع العدد نفسه.",
      'out = []\nfor i in range(1, 16):\n    if i % 15 == 0:\n        out.append("FizzBuzz")\n    elif i % 3 == 0:\n        out.append("Fizz")\n    elif i % 5 == 0:\n        out.append("Buzz")\n    else:\n        out.append(str(i))\nprint(" ".join(out))', "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz")
    P("py_factorial_loop", ["كيف احسب مضروب عدد بحلقة في بايثون", "factorial بايثون", "كيف احسب 5 مضروب"],
      "المضروب n! حاصل ضرب الأعداد من 1 إلى n. بالحلقة أو بالدالة الجاهزة math.factorial.",
      'import math\nf = 1\nfor i in range(1, 6):\n    f *= i\nprint(f, math.factorial(5))', "120 120")
    P("py_math", ["كيف استخدم مكتبة math في بايثون", "الجذر التربيعي والقوة والتقريب في بايثون", "العمليات الحسابية في بايثون // و %"],
      "مكتبة math فيها sqrt وfloor وceil وpi. وفي بايثون: ** للأس، // للقسمة الصحيحة، % لباقي القسمة، abs للقيمة المطلقة.",
      'import math\nprint(math.sqrt(16), round(math.pi, 3), math.floor(2.7), math.ceil(2.1), abs(-5), 2 ** 10, 17 // 5, 17 % 5)', "4.0 3.142 2 3 5 1024 3 2")
    P("py_random", ["كيف اختار رقم عشوائي في بايثون", "random.choice و shuffle", "كيف اخلط قائمة عشوائيا"],
      "مكتبة random: randint(a, b) رقم صحيح بين الحدين (شاملين)، choice تختار عنصرا، shuffle تخلط قائمة في مكانها. النتيجة تتغير كل مرة، لذلك لم تُشغَّل للتحقق من ناتجها.",
      'import random\nprint(random.randint(1, 10))\nitems = ["a", "b", "c"]\nprint(random.choice(items))\nrandom.shuffle(items)\nprint(items)', None, "pyc")
    P("py_try_finally", ["ما فائدة finally في بايثون", "try except finally", "متى ينفذ finally"],
      "كتلة finally تُنفَّذ دائما سواء حصل خطأ أم لا، وحتى عند return. تُستخدم لإغلاق الملفات والاتصالات.",
      'def f():\n    try:\n        return "try"\n    finally:\n        print("finally")\n\nprint(f())', "finally\ntry")
    P("py_raise", ["كيف اطلق خطا بنفسي في بايثون raise", "كيف اتحقق من المدخلات وارفع استثناء", "ValueError في بايثون"],
      "raise ترفع استثناء عندما تكتشف قيمة غير صالحة، ويلتقطه المستدعي بـ try/except.",
      'def check_age(a):\n    if a < 0:\n        raise ValueError("العمر لا يكون سالبا")\n    return a\n\ntry:\n    check_age(-1)\nexcept ValueError as e:\n    print("خطأ:", e)', "خطأ: العمر لا يكون سالبا")
    P("py_str_dunder", ["ما هو __str__ في بايثون", "كيف اغير طريقة طباعة الكائن", "الدوال السحرية في الكلاس"],
      "الدالة __str__ في الكلاس تحدد النص الذي يظهر عند print للكائن.",
      'class P:\n    def __init__(self, n):\n        self.n = n\n    def __str__(self):\n        return f"P({self.n})"\n\nprint(P(3))', "P(3)")
    P("py_property", ["ما هو property في بايثون", "كيف اجعل دالة تظهر كخاصية", "الخصائص المحسوبة في الكلاس"],
      "الديكوريتر @property يجعل الدالة تُقرأ كخاصية بدون أقواس، ويفيد لقيم تُحسب من غيرها.",
      'class Circle:\n    def __init__(self, r):\n        self.r = r\n    @property\n    def area(self):\n        return round(3.14159 * self.r ** 2, 2)\n\nprint(Circle(2).area)', "12.57")
    P("py_enumerate_start", ["كيف ابدا العد من واحد في enumerate", "enumerate مع start", "كيف اطبع الترقيم مع العناصر"],
      "enumerate(قائمة، start=1) تعطي الرقم والعنصر معا، ويمكن تحديد رقم البداية.",
      'for i, name in enumerate(["a", "b"], start=1):\n    print(i, name)', "1 a\n2 b")
    P("py_reversed", ["كيف اعكس قائمة او نص في بايثون", "reversed و [::-1]", "قلب ترتيب العناصر"],
      "reversed ترجع مكرِّرا للعناصر بترتيب معكوس (حوّله بـ list)، والشريحة [::-1] تعكس النص أو القائمة.",
      'print(list(reversed([1, 2, 3])), "abc"[::-1])', "[3, 2, 1] cba")
    P("py_count_words", ["كيف اعد تكرار كل كلمة في نص بدون Counter", "عداد الكلمات بقاموس", "كيف ابني قاموس تكرار"],
      "اقسم النص بـ split، ثم زد العداد في قاموس باستخدام get بقيمة افتراضية 0.",
      'text = "a b a c b a"\ncounts = {}\nfor w in text.split():\n    counts[w] = counts.get(w, 0) + 1\nprint(counts)', "{'a': 3, 'b': 2, 'c': 1}")
    P("py_list_methods", ["كيف ازيد واحذف عناصر القائمة append insert remove pop", "الفرق بين remove و pop", "كيف اضيف عنصر في اول القائمة"],
      "append تضيف في النهاية، insert(موضع، قيمة) تضيف في موضع، remove تحذف أول قيمة مطابقة، pop تحذف وترجع العنصر الأخير (أو عنصرا بموضعه)، sort ترتب في مكانها.",
      'l = [3, 1, 2]\nl.append(4)\nl.insert(0, 9)\nl.remove(1)\nl.pop()\nl.sort()\nprint(l)', "[2, 3, 9]")
    P("py_type_conversion", ["كيف احول النص الى رقم والعكس في بايثون", "int و str و float تحويل الانواع", "لماذا round(2.5) تعطي 2"],
      "int وfloat وstr وlist تحوّل بين الأنواع. int تقطع الجزء العشري. وround في بايثون تقرّب النصف إلى أقرب عدد زوجي: round(2.5)=2 وround(3.5)=4.",
      'print(int("42") + 1, str(3) + "4", float("2.5") * 2, list("abc"), int(3.9), round(2.5), round(3.5))', "43 34 5.0 ['a', 'b', 'c'] 3 2 4")
    P("py_str_checks", ["كيف افحص ان النص كله ارقام او حروف", "isdigit و isalpha", "كيف اتحقق من نوع محتوى النص"],
      "دوال الفحص: isalpha كلها حروف، isdigit كلها أرقام، isalnum حروف أو أرقام، isspace كلها مسافات.",
      'print("abc".isalpha(), "123".isdigit(), "a1".isalnum(), " ".isspace())', "True True True True")
    P("py_zip_dict", ["كيف احول قائمتين الى قاموس", "dict مع zip", "كيف اربط المفاتيح بالقيم"],
      "zip تجمع عنصرا من كل قائمة، وdict يحولها إلى قاموس.",
      'keys = ["a", "b"]\nvals = [1, 2]\nprint(dict(zip(keys, vals)))', "{'a': 1, 'b': 2}")
    P("py_unique_order", ["كيف احذف التكرار من قائمة مع حفظ الترتيب", "ازالة العناصر المكررة بايثون", "dict.fromkeys لحذف التكرار"],
      "المجموعة set تحذف التكرار لكنها لا تحفظ الترتيب. dict.fromkeys يحفظ ترتيب الظهور الأول.",
      'print(list(dict.fromkeys([3, 1, 3, 2, 1])))', "[3, 1, 2]")
    P("py_min_key", ["كيف اجد اصغر عنصر حسب خاصية معينة", "min مع key و lambda", "كيف اجد اكبر عنصر في قائمة tuples"],
      "min وmax تقبلان key لتحديد القيمة المقارَنة.",
      'people = [("a", 30), ("b", 25)]\nprint(min(people, key=lambda p: p[1]))', "('b', 25)")
    P("py_unittest", ["كيف اختبر الكود في بايثون unittest", "كيف اكتب اختبار لدالتي", "assert و unittest"],
      "unittest مكتبة جاهزة: اكتب كلاسا يرث TestCase وفيه دوال تبدأ بـ test، واستخدم assertEqual. وassert بسيط للفحص السريع.",
      'import os, unittest\n\ndef add(a, b):\n    return a + b\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\nsuite = unittest.defaultTestLoader.loadTestsFromTestCase(T)\nresult = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)\nprint(result.wasSuccessful())', "True")
    P("py_bin_hex", ["كيف احول رقم الى ثنائي او سداسي عشر في بايثون", "bin و hex و int بأساس", "النظام الثنائي في بايثون"],
      "bin للثنائي، hex للسداسي عشر، oct للثماني. وint(نص، أساس) يحوّل نصا من أساس معين.",
      'print(bin(10), hex(255), int("ff", 16), oct(8))', "0b1010 0xff 255 0o10")
    P("py_ord_chr", ["ما هو ord و chr في بايثون", "كيف اعرف رقم الحرف في unicode", "كيف احول رقم الى حرف"],
      "ord ترجع رقم الحرف في Unicode، وchr ترجع الحرف من رقمه. تعمل مع العربية أيضا.",
      'print(ord("a"), chr(98), ord("ع"))', "97 b 1593")
    P("py_arabic_text", ["كيف اتعامل مع النص العربي في بايثون", "طول الكلمة العربية وعكسها بايثون", "الترميز utf-8 للعربية"],
      "بايثون 3 تدعم العربية في النصوص مباشرة (Unicode). اقرأ الملفات وأكتبها بـ encoding=\"utf-8\" حتى لا تتشوه الحروف.",
      'print(len("مرحبا"), "مرحبا"[::-1])', "5 ابحرم")
    P("py_calculator", ["اكتب الة حاسبة في بايثون", "برنامج حاسبة بسيط", "كيف اصنع حاسبة بقاموس عمليات"],
      "اجعل كل عملية دالة داخل قاموس، ثم اختر الدالة بالرمز.",
      'def calc(a, op, b):\n    ops = {"+": lambda x, y: x + y, "-": lambda x, y: x - y, "*": lambda x, y: x * y, "/": lambda x, y: x / y}\n    return ops[op](a, b)\n\nprint(calc(6, "+", 3), calc(6, "/", 3))', "9 2.0")
    P("py_guess_game", ["اكتب لعبة تخمين الرقم في بايثون", "برنامج لعبة تخمين", "كيف اصنع لعبة بسيطة بايثون"],
      "الرقم السري يُختار عشوائيا، وحلقة while تسأل اللاعب وتقول له أكبر أو أصغر حتى يصيب. تحتاج إدخالا من المستخدم لذلك لم تُشغَّل للتحقق.",
      'import random\n\nsecret = random.randint(1, 20)\nwhile True:\n    g = int(input("خمّن الرقم: "))\n    if g == secret:\n        print("أصبت!")\n        break\n    print("أكبر" if g < secret else "أصغر")', None, "pyc")
    P("py_statistics", ["كيف احسب المتوسط والوسيط في بايثون", "مكتبة statistics", "mean و median"],
      "مكتبة statistics فيها mean للمتوسط وmedian للوسيط.",
      'import statistics\nprint(statistics.mean([1, 2, 3, 4]), statistics.median([1, 3, 2]))', "2.5 2")
    P("py_count_vowels", ["كيف اعد الحروف المتحركة في كلمة بايثون", "عد حروف معينة في نص", "كيف استخدم sum مع شرط"],
      "sum مع تعبير مولِّد تعدّ العناصر التي تحقق شرطا: كل عنصر صحيح يعطي 1.",
      'print(sum(1 for c in "education" if c in "aeiou"))', "5")
    P("py_transpose", ["كيف اقلب مصفوفة صفوف الى اعمدة في بايثون", "transpose بـ zip", "zip مع النجمة"],
      "zip(*m) تفك الصفوف وتجمع الأعمدة، فتحصل على المنقول (transpose).",
      'print([list(r) for r in zip(*[[1, 2], [3, 4]])])', "[[1, 3], [2, 4]]")
    P("py_sum_digits", ["كيف اجمع ارقام عدد في بايثون", "مجموع خانات الرقم", "حول الرقم الى نص ثم اجمع"],
      "حوّل العدد إلى نص بـ str، ثم حوّل كل حرف إلى int واجمعها.",
      'print(sum(int(d) for d in str(1234)))', "10")
    P("py_generator_expr", ["ما هو generator expression في بايثون", "الفرق بين الاقواس المربعة والعادية في comprehension", "كيف اوفر الذاكرة مع sum"],
      "التعبير المولِّد بأقواس عادية لا ينشئ قائمة كاملة في الذاكرة، بل يعطي القيم واحدة واحدة، فهو أوفر للذاكرة مع sum وmax.",
      'print(sum(x * x for x in range(5)))', "30")
