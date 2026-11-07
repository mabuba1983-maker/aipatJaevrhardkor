# -*- coding: utf-8 -*-
"""Hand-written programming knowledge for Nuwaa (Arabic). Every entry with a check is EXECUTED by tools/gen_knowledge.py:
  py   -> run, stdout must equal exp          pyc -> must compile (needs network/stdin so it is not run)
  js   -> node, stdout must equal exp         jsc -> node --check
  sql  -> sqlite3 in memory, must not fail    sh  -> bash -n
Entries without a check are explanations or languages we cannot run here (Kotlin, Java, C, HTML, CSS): they are NOT marked verified."""
ENTRIES = []
def E(id, qs, text, lang="", code="", check=None, exp=None):
    ENTRIES.append(dict(id=id, qs=qs, text=text, lang=lang, code=code.strip("\n"), check=check, exp=exp))

# ---------------- Python ----------------
E("py_hello", ["كيف اكتب اول برنامج بايثون", "برنامج hello world بايثون", "كيف اطبع نص في بايثون", "print في بايثون"],
  "الدالة print تطبع أي نص أو رقم على الشاشة.", "python", 'print("مرحبا بالعالم")', "py", "مرحبا بالعالم")
E("py_variables", ["ما هي المتغيرات في بايثون", "كيف اعرف متغير في بايثون", "انواع المتغيرات variables بايثون"],
  "المتغير اسم يحفظ قيمة. بايثون تحدد النوع تلقائيا ولا تحتاج تكتبه.", "python",
  'name = "نواة"\nage = 3\nprice = 9.5\nprint(name, age, price)', "py", "نواة 3 9.5")
E("py_types", ["ما هي انواع البيانات في بايثون", "كيف اعرف نوع المتغير في بايثون", "type في بايثون data types"],
  "الأنواع الأساسية: int للأعداد الصحيحة، float للعشرية، str للنص، list للقوائم، dict للقواميس. الدالة type تعرض النوع.", "python",
  'print(type(5).__name__, type(5.0).__name__, type("a").__name__, type([1]).__name__, type({"a": 1}).__name__)', "py", "int float str list dict")
E("py_input", ["كيف اقرا مدخل من المستخدم في بايثون", "input في بايثون", "كيف استقبل رقم من المستخدم بايثون"],
  "الدالة input ترجع نصا دائما، حوّله برقم بـ int أو float عند الحاجة.", "python",
  'n = int(input("اكتب رقما: "))\nprint("ضعف الرقم:", n * 2)', "pyc")
E("py_if", ["كيف اكتب شرط if في بايثون", "if elif else بايثون", "الجمل الشرطية في بايثون"],
  "الشرط يبدأ بـ if، وبعده elif لشروط اضافية، وelse للحالة الاخيرة. الازاحة (4 مسافات) مهمة.", "python",
  'x = 7\nif x > 10:\n    print("اكبر من 10")\nelif x > 5:\n    print("كبير")\nelse:\n    print("صغير")', "py", "كبير")
E("py_for", ["كيف اكتب حلقة for في بايثون", "for loop بايثون", "التكرار بحلقة for و range"],
  "for تمر على عناصر أي مجموعة، وrange تولد أرقاما (النهاية غير مشمولة).", "python",
  "for i in range(1, 4):\n    print(i)", "py", "1\n2\n3")
E("py_while", ["كيف اكتب حلقة while في بايثون", "while loop بايثون", "حلقة while مع عداد"],
  "while تكرر ما دام الشرط صحيحا. انتبه أن يتغير الشرط داخل الحلقة وإلا تصير لا نهائية.", "python",
  "i = 3\nwhile i > 0:\n    print(i)\n    i -= 1", "py", "3\n2\n1")
E("py_list", ["كيف اتعامل مع القوائم list في بايثون", "اضافة عنصر لقائمة بايثون append", "ما هي القائمة list في بايثون"],
  "القائمة تحفظ عناصر مرتبة وقابلة للتعديل. الفهرس يبدأ من 0 والسالب يعد من النهاية.", "python",
  'fruits = ["تفاح", "موز"]\nfruits.append("برتقال")\nprint(len(fruits), fruits[0], fruits[-1])', "py", "3 تفاح برتقال")
E("py_dict", ["ما هو القاموس dict في بايثون", "كيف استخدم dictionary بايثون", "المرور على مفاتيح وقيم القاموس"],
  "القاموس يخزن أزواج مفتاح:قيمة، والوصول للقيمة عن طريق المفتاح بسرعة.", "python",
  'd = {"name": "سعد", "age": 20}\nd["city"] = "الرياض"\nfor k, v in d.items():\n    print(k, v)', "py", "name سعد\nage 20\ncity الرياض")
E("py_set", ["ما هي المجموعة set في بايثون", "كيف احذف التكرار من قائمة بايثون", "set بايثون"],
  "المجموعة set لا تقبل التكرار. تحويل القائمة إلى set يحذف المكرر.", "python",
  "s = set([1, 2, 2, 3])\nprint(sorted(s))", "py", "[1, 2, 3]")
E("py_tuple", ["ما هي tuple في بايثون", "الفرق بين list و tuple", "tuple بايثون unpacking"],
  "الـ tuple مثل القائمة لكنها لا تتغير بعد إنشائها. تقدر تفكها في متغيرات مباشرة.", "python",
  "t = (1, 2)\na, b = t\nprint(a + b)", "py", "3")
E("py_strings", ["كيف اتعامل مع النصوص strings في بايثون", "دوال النصوص بايثون strip lower replace", "كيف احول النص لحروف صغيرة بايثون"],
  "النصوص لها دوال جاهزة: strip تحذف الفراغات، lower/upper تغير حالة الحروف، replace تستبدل.", "python",
  's = "  Hello World "\nprint(s.strip().lower().replace("world", "py"))', "py", "hello py")
E("py_fstring", ["ما هو f-string في بايثون", "كيف ادمج متغير داخل نص بايثون", "format النصوص بايثون"],
  "اكتب f قبل النص وضع المتغير بين { } ليدخل في النص.", "python",
  'name = "علي"\nn = 3\nprint(f"{name} عنده {n} كتب")', "py", "علي عنده 3 كتب")
E("py_split_join", ["كيف اقسم نص الى كلمات بايثون split", "دالة join في بايثون", "كيف ادمج قائمة نصوص بايثون"],
  "split تقطع النص إلى قائمة، وjoin تدمج القائمة في نص بفاصل تختاره.", "python",
  'print("a,b,c".split(","), "-".join(["x", "y"]))', "py", "['a', 'b', 'c'] x-y")
E("py_slicing", ["ما هو slicing في بايثون", "كيف اعكس قائمة او نص في بايثون", "تقطيع القوائم بايثون"],
  "الصيغة a[start:stop:step]. النهاية غير مشمولة، و[::-1] تعكس التسلسل.", "python",
  "a = [0, 1, 2, 3, 4, 5]\nprint(a[1:4], a[::-1], a[-2:])", "py", "[1, 2, 3] [5, 4, 3, 2, 1, 0] [4, 5]")
E("py_function", ["كيف اكتب دالة في بايثون", "تعريف function بايثون def", "ما هي الدوال وكيف ارجع قيمة return"],
  "الدالة تبدأ بـ def وتعيد نتيجة بـ return. استخدمها لتجنب تكرار الكود.", "python",
  "def add(a, b):\n    return a + b\n\nprint(add(2, 3))", "py", "5")
E("py_default_args", ["ما هي القيم الافتراضية للدوال في بايثون", "default arguments بايثون", "معامل اختياري في دالة بايثون"],
  "اعطِ المعامل قيمة افتراضية في التعريف فيصير اختياريا عند الاستدعاء.", "python",
  'def greet(name="ضيف"):\n    return "مرحبا " + name\n\nprint(greet(), greet("سارة"))', "py", "مرحبا ضيف مرحبا سارة")
E("py_args_kwargs", ["ما معنى args و kwargs في بايثون", "كيف استقبل عدد غير محدد من المعاملات بايثون", "*args **kwargs"],
  "*args تجمع المعاملات الموضعية في tuple، و**kwargs تجمع المعاملات المسماة في dict.", "python",
  "def f(*args, **kw):\n    return len(args), kw\n\nprint(f(1, 2, x=3))", "py", "(2, {'x': 3})")
E("py_lambda", ["ما هي lambda في بايثون", "دالة مجهولة بايثون", "كيف ارتب قائمة حسب طول النص بايثون"],
  "lambda دالة صغيرة بدون اسم في سطر واحد، مفيدة كمعامل key في الترتيب.", "python",
  'sq = lambda x: x * x\nprint(sq(4), sorted(["bb", "a", "ccc"], key=lambda s: len(s)))', "py", "16 ['a', 'bb', 'ccc']")
E("py_list_comp", ["ما هو list comprehension في بايثون", "كيف اكتب قائمة في سطر واحد بايثون", "فلترة قائمة بشرط بايثون"],
  "الصيغة [تعبير for عنصر in مجموعة if شرط] تبني قائمة جديدة بسطر واحد.", "python",
  "print([x * x for x in range(5) if x % 2 == 0])", "py", "[0, 4, 16]")
E("py_dict_comp", ["dictionary comprehension بايثون", "كيف انشئ قاموس بحلقة في سطر بايثون"],
  "نفس فكرة list comprehension لكن بأقواس { } وزوج مفتاح:قيمة.", "python",
  "print({x: x * 2 for x in range(3)})", "py", "{0: 0, 1: 2, 2: 4}")
E("py_map_filter", ["ما هي map و filter في بايثون", "دالة map بايثون", "دالة filter بايثون"],
  "map تطبق دالة على كل عنصر، وfilter تبقي العناصر التي يتحقق فيها الشرط. كلاهما يرجع كائنا نحوله بـ list.", "python",
  "print(list(map(lambda x: x + 1, [1, 2])), list(filter(lambda x: x > 1, [1, 2, 3])))", "py", "[2, 3] [2, 3]")
E("py_zip_enumerate", ["ما هي enumerate و zip في بايثون", "كيف اجيب الفهرس مع العنصر في حلقة بايثون", "دمج قائمتين بايثون zip"],
  "enumerate تعطيك الفهرس مع العنصر، وzip تمشي على أكثر من قائمة معا.", "python",
  'for i, (a, b) in enumerate(zip("ab", [1, 2])):\n    print(i, a, b)', "py", "0 a 1\n1 b 2")
E("py_class", ["كيف انشئ كلاس في بايثون", "ما هي البرمجة الكائنية OOP في بايثون", "class و __init__ و self بايثون"],
  "الكلاس قالب للكائنات. __init__ تجهز الكائن عند إنشائه، وself يشير للكائن نفسه.", "python",
  'class Dog:\n    def __init__(self, name):\n        self.name = name\n\n    def speak(self):\n        return self.name + " يقول هاو"\n\nprint(Dog("ريكس").speak())', "py", "ريكس يقول هاو")
E("py_inherit", ["ما هي الوراثة في بايثون", "inheritance بايثون كلاس يرث من كلاس", "override دالة في كلاس ابن"],
  "الكلاس الابن يرث من الأب بكتابة الأب بين أقواس، ويقدر يعيد تعريف الدوال (override).", "python",
  'class Animal:\n    def speak(self):\n        return "..."\n\nclass Cat(Animal):\n    def speak(self):\n        return "ميو"\n\nprint(Animal().speak(), Cat().speak())', "py", "... ميو")
E("py_exceptions", ["كيف اتعامل مع الاخطاء try except في بايثون", "معالجة الاستثناءات بايثون", "try except finally"],
  "ضع الكود الخطر في try والمعالجة في except، وfinally ينفذ دائما.", "python",
  'try:\n    1 / 0\nexcept ZeroDivisionError:\n    print("لا يمكن القسمة على صفر")\nfinally:\n    print("انتهى")', "py", "لا يمكن القسمة على صفر\nانتهى")
E("py_file", ["كيف اقرا واكتب ملف في بايثون", "open و with بايثون ملفات", "حفظ نص في ملف بايثون"],
  "استخدم with حتى يُغلق الملف تلقائيا، وحدد encoding='utf-8' للعربي.", "python",
  'with open("t.txt", "w", encoding="utf-8") as f:\n    f.write("مرحبا")\nwith open("t.txt", encoding="utf-8") as f:\n    print(f.read())', "py", "مرحبا")
E("py_json", ["كيف اتعامل مع json في بايثون", "تحويل نص json الى قاموس بايثون", "json.dumps و json.loads"],
  "loads تحول نص JSON إلى بيانات بايثون، وdumps تعمل العكس.", "python",
  'import json\nd = json.loads(\'{"a": 1}\')\nprint(d["a"], json.dumps({"x": [1, 2]}))', "py", '1 {"x": [1, 2]}')
E("py_recursion", ["ما هي الدالة التراجعية recursion", "كيف احسب المضروب بالتراجع بايثون", "recursion بايثون factorial"],
  "الدالة تنادي نفسها مع حالة توقف (base case) واضحة وإلا لن تنتهي.", "python",
  "def fact(n):\n    if n <= 1:\n        return 1\n    return n * fact(n - 1)\n\nprint(fact(5))", "py", "120")
E("py_sort", ["كيف ارتب قائمة في بايثون", "sorted و sort الفرق", "ترتيب تنازلي بايثون reverse"],
  "sorted ترجع قائمة جديدة، وlist.sort تعدل القائمة نفسها. استخدم reverse=True للتنازلي وkey للمعيار.", "python",
  "print(sorted([3, 1, 2]), sorted([3, 1, 2], reverse=True))", "py", "[1, 2, 3] [3, 2, 1]")
E("py_binary_search", ["كيف اكتب البحث الثنائي binary search", "binary search بايثون", "خوارزمية البحث الثنائي", "كيف ابحث في قائمة مرتبة بسرعة"],
  "تعمل على قائمة مرتبة: قارن بالمنتصف وارم نصف القائمة في كل خطوة. التعقيد O(log n).", "python",
  "def bs(a, x):\n    lo, hi = 0, len(a) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if a[mid] == x:\n            return mid\n        if a[mid] < x:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n\nprint(bs([1, 3, 5, 7, 9], 7))", "py", "3")
E("py_bubble_sort", ["كيف اكتب خوارزمية الترتيب الفقاعي", "bubble sort بايثون", "خوارزمية ترتيب بسيطة بدون sorted"],
  "تقارن كل عنصرين متجاورين وتبدلهما إن كانا بالترتيب الخطأ. بسيطة لكنها بطيئة O(n²).", "python",
  "def bubble(a):\n    a = a[:]\n    for i in range(len(a)):\n        for j in range(len(a) - 1 - i):\n            if a[j] > a[j + 1]:\n                a[j], a[j + 1] = a[j + 1], a[j]\n    return a\n\nprint(bubble([5, 2, 9, 1]))", "py", "[1, 2, 5, 9]")
E("py_decorator", ["ما هو الـ decorator في بايثون", "كيف اكتب ديكوريتر", "@ فوق الدالة في بايثون"],
  "الـ decorator دالة تأخذ دالة وترجع دالة معدلة، وتُطبق بالرمز @ فوق التعريف.", "python",
  "def twice(f):\n    def w(*a):\n        return f(*a) * 2\n    return w\n\n@twice\ndef three():\n    return 3\n\nprint(three())", "py", "6")
E("py_generator", ["ما هو generator و yield في بايثون", "كيف استخدم yield", "المولدات بايثون"],
  "الدالة التي فيها yield تنتج القيم واحدة واحدة بدون تخزين الكل في الذاكرة.", "python",
  "def count(n):\n    for i in range(n):\n        yield i\n\nprint(list(count(3)))", "py", "[0, 1, 2]")
E("py_regex", ["كيف استخدم regex في بايثون", "التعبيرات النمطية re findall", "استخراج الارقام من نص بايثون"],
  "وحدة re تبحث بأنماط. \\d+ تعني رقما واحدا أو أكثر، وfindall ترجع كل التطابقات.", "python",
  'import re\nprint(re.findall(r"\\d+", "a12b345"))', "py", "['12', '345']")
E("py_datetime", ["كيف اتعامل مع التاريخ والوقت في بايثون", "datetime بايثون الفرق بين تاريخين", "تنسيق التاريخ strftime"],
  "وحدة datetime فيها date وdatetime. طرح تاريخين يعطي timedelta وفيه days.", "python",
  'from datetime import date\nprint(date(2024, 1, 31).strftime("%Y-%m-%d"), (date(2024, 3, 1) - date(2024, 2, 1)).days)', "py", "2024-01-31 29")
E("py_dataclass", ["ما هو dataclass في بايثون", "كيف انشئ كلاس بيانات بسرعة بايثون"],
  "@dataclass يولد __init__ و__repr__ تلقائيا من الحقول المعرفة.", "python",
  "from dataclasses import dataclass\n\n@dataclass\nclass P:\n    x: int\n    y: int = 0\n\nprint(P(1))", "py", "P(x=1, y=0)")
E("py_main_guard", ["ما معنى if __name__ == '__main__'", "لماذا نكتب main في بايثون", "__name__ main بايثون"],
  "هذا الشرط يشغل الكود فقط عند تشغيل الملف مباشرة، وليس عند استيراده من ملف آخر.", "python",
  'def main():\n    print("تشغيل")\n\nif __name__ == "__main__":\n    main()', "py", "تشغيل")
E("py_two_sum", ["حل مسألة two sum", "ايجاد رقمين مجموعهما يساوي هدف", "two sum بايثون بقاموس"],
  "خزّن ما رأيته في قاموس وابحث عن المكمل (الهدف - الرقم الحالي). التعقيد O(n).", "python",
  "def two_sum(a, t):\n    seen = {}\n    for i, x in enumerate(a):\n        if t - x in seen:\n            return [seen[t - x], i]\n        seen[x] = i\n\nprint(two_sum([2, 7, 11, 15], 9))", "py", "[0, 1]")
E("py_gcd", ["كيف احسب القاسم المشترك الاكبر gcd", "خوارزمية اقليدس بايثون"],
  "خوارزمية إقليدس: كرر (a, b) = (b, a % b) حتى يصير b صفرا.", "python",
  "def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a\n\nprint(gcd(12, 18))", "py", "6")
E("py_counter", ["كيف اعد تكرار الكلمات في نص بايثون", "Counter بايثون collections", "الكلمة الاكثر تكرارا بايثون"],
  "Counter من collections تعد التكرار، وmost_common ترجع الأكثر ظهورا.", "python",
  'from collections import Counter\nprint(Counter("a b a".split()).most_common(1))', "py", "[('a', 2)]")
E("py_csv", ["كيف اقرا ملف csv في بايثون", "csv بايثون DictReader"],
  "وحدة csv تقرأ الأسطر، وDictReader تعطيك كل سطر كقاموس بأسماء الأعمدة.", "python",
  'import csv, io\ndata = io.StringIO("name,age\\nali,20\\nsara,25")\nfor row in csv.DictReader(data):\n    print(row["name"], row["age"])', "py", "ali 20\nsara 25")
E("py_memo", ["كيف اسرع دالة فيبوناتشي بايثون", "lru_cache memoization", "البرمجة الديناميكية fibonacci"],
  "التخزين المؤقت (memoization) يحفظ نتائج الاستدعاءات السابقة فيمنع التكرار. lru_cache تفعله بسطر واحد.", "python",
  "from functools import lru_cache\n\n@lru_cache(None)\ndef fib(n):\n    return n if n < 2 else fib(n - 1) + fib(n - 2)\n\nprint(fib(30))", "py", "832040")
E("py_swap", ["كيف ابدل قيمة متغيرين في بايثون", "swap بايثون"],
  "بايثون تسمح بالتبديل بسطر واحد بدون متغير مؤقت.", "python", "a, b = 1, 2\na, b = b, a\nprint(a, b)", "py", "2 1")
E("py_scope", ["ما هو نطاق المتغير scope في بايثون", "global و local بايثون", "لماذا يظهر UnboundLocalError"],
  "المتغير داخل الدالة محلي. لتعديل متغير خارجي استخدم global (والأفضل تمرير القيمة وإرجاعها).", "python",
  "x = 1\n\ndef f():\n    global x\n    x += 1\n\nf()\nprint(x)", "py", "2")
E("py_mutable", ["ما الفرق بين mutable و immutable", "لماذا تتغير القائمة داخل الدالة", "القابلة للتغيير بايثون"],
  "القوائم والقواميس قابلة للتغيير وتُمرر بالمرجع، أما الأرقام والنصوص وtuple فلا تتغير.", "python",
  "def add(a):\n    a.append(1)\n\nx = []\nadd(x)\nprint(x)", "py", "[1]")
E("py_copy", ["الفرق بين copy و deepcopy", "نسخ قائمة في بايثون", "لماذا تتغير القائمة الاصلية بعد النسخ"],
  "b = a لا ينسخ بل يشير لنفس القائمة. استخدم a.copy() لنسخة سطحية وdeepcopy لنسخة كاملة للقوائم المتداخلة.", "python",
  "import copy\na = [[1], [2]]\nb = copy.deepcopy(a)\nb[0].append(9)\nprint(a, b)", "py", "[[1], [2]] [[1, 9], [2]]")
E("py_is_eq", ["الفرق بين == و is في بايثون", "is و == بايثون"],
  "== تقارن القيمة، وis تقارن هل هما نفس الكائن في الذاكرة.", "python",
  "a = [1]\nb = [1]\nprint(a == b, a is b)", "py", "True False")
E("py_stack_queue", ["ما الفرق بين stack و queue", "كيف اعمل stack في بايثون", "طابور queue بايثون deque"],
  "Stack: آخر داخل أول خارج (LIFO) وتناسبه list. Queue: أول داخل أول خارج (FIFO) وتناسبه deque.", "python",
  "from collections import deque\ns = [1, 2]\ns.append(3)\nq = deque([1, 2])\nq.append(3)\nprint(s.pop(), q.popleft())", "py", "3 1")
E("py_bfs", ["كيف اكتب البحث بالعرض BFS", "bfs و dfs في بايثون", "المشي على الرسم البياني graph"],
  "BFS يزور الجيران طبقة طبقة باستخدام طابور، وDFS يغوص بعمق باستخدام مكدس أو تراجع.", "python",
  "from collections import deque\n\ndef bfs(g, s):\n    seen, q, out = {s}, deque([s]), []\n    while q:\n        n = q.popleft()\n        out.append(n)\n        for m in g[n]:\n            if m not in seen:\n                seen.add(m)\n                q.append(m)\n    return out\n\nprint(bfs({1: [2, 3], 2: [4], 3: [4], 4: []}, 1))", "py", "[1, 2, 3, 4]")
E("py_linked_list", ["ما هي القائمة المترابطة linked list", "linked list بايثون"],
  "كل عقدة تحمل قيمة ومؤشرا للعقدة التالية. الإضافة في البداية O(1) لكن الوصول بالفهرس O(n).", "python",
  "class Node:\n    def __init__(self, v, nxt=None):\n        self.v, self.next = v, nxt\n\nhead = Node(1, Node(2, Node(3)))\nn = head\nwhile n:\n    print(n.v)\n    n = n.next", "py", "1\n2\n3")
E("py_venv", ["كيف انشئ بيئة افتراضية venv في بايثون", "كيف اثبت مكتبة بايثون pip", "pip install"],
  "البيئة الافتراضية تعزل مكتبات كل مشروع. فعّلها ثم ثبّت المكتبات بـ pip.", "bash",
  "python -m venv venv\nsource venv/bin/activate   # ويندوز: venv\\Scripts\\activate\npip install requests\npip freeze > requirements.txt", "sh")
E("py_requests", ["كيف اجلب بيانات من API في بايثون", "مكتبة requests بايثون", "طلب HTTP GET بايثون"],
  "مكتبة requests (تثبت بـ pip) ترسل الطلب وترجع الاستجابة، وjson() تحولها لبيانات.", "python",
  'import requests\nr = requests.get("https://api.github.com")\nprint(r.status_code)\nprint(r.json())', "pyc")
E("py_flask", ["كيف انشئ موقع بسيط بايثون flask", "خادم ويب بايثون", "flask hello world"],
  "Flask إطار خفيف: كل مسار route هو دالة ترجع الصفحة.", "python",
  'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/")\ndef home():\n    return "مرحبا"\n\napp.run()', "pyc")

# ---------------- JavaScript ----------------
E("js_hello", ["كيف اطبع في جافاسكربت console.log", "اول برنامج جافاسكربت", "hello world javascript"],
  "console.log تطبع في وحدة التحكم (console) في المتصفح أو Node.", "javascript", 'console.log("مرحبا");', "js", "مرحبا")
E("js_vars", ["الفرق بين var و let و const", "كيف اعرف متغير في جافاسكربت", "const و let جافاسكربت"],
  "استخدم const افتراضيا، وlet إذا ستغير القيمة، وتجنب var لأن نطاقها يسبب أخطاء.", "javascript",
  "let a = 1;\nconst b = 2;\na = 5;\nconsole.log(a + b);", "js", "7")
E("js_arrow", ["ما هي الدالة السهمية arrow function", "كيف اكتب دالة في جافاسكربت", "=> في جافاسكربت"],
  "الدالة السهمية صيغة مختصرة للدوال: (المعاملات) => الناتج.", "javascript",
  "const add = (a, b) => a + b;\nconsole.log(add(2, 3));", "js", "5")
E("js_array_methods", ["دوال المصفوفات map filter reduce", "كيف افلتر مصفوفة في جافاسكربت", "reduce جافاسكربت"],
  "map تحول كل عنصر، filter تختار، reduce تجمع كل العناصر في قيمة واحدة.", "javascript",
  "const n = [1, 2, 3, 4];\nconsole.log(JSON.stringify(n.map(x => x * 2)), JSON.stringify(n.filter(x => x % 2 === 0)), n.reduce((s, x) => s + x, 0));", "js", "[2,4,6,8] [2,4] 10")
E("js_destructuring", ["ما هو destructuring و spread في جافاسكربت", "فك المصفوفة والكائن جافاسكربت", "... في جافاسكربت"],
  "التفكيك يسحب القيم من كائن أو مصفوفة بسطر واحد، وspread (...) ينشر العناصر.", "javascript",
  "const { a, b } = { a: 1, b: 2 };\nconst [x, ...rest] = [1, 2, 3];\nconsole.log(a + b, x, rest.length, Math.max(...[1, 5, 3]));", "js", "3 1 2 5")
E("js_async", ["ما هو async await في جافاسكربت", "كيف اتعامل مع Promise", "الدوال غير المتزامنة جافاسكربت"],
  "Promise وعد بنتيجة لاحقة، وawait داخل دالة async ينتظر النتيجة بدون تجميد الصفحة.", "javascript",
  'const wait = ms => new Promise(r => setTimeout(r, ms));\n(async () => {\n  await wait(10);\n  console.log("تم");\n})();', "js", "تم")
E("js_fetch", ["كيف اجلب بيانات من API في جافاسكربت fetch", "fetch جافاسكربت", "طلب HTTP من المتصفح"],
  "fetch ترجع Promise، استخدم await ثم response.json() لقراءة البيانات.", "javascript",
  'async function load() {\n  const r = await fetch("https://api.github.com");\n  if (!r.ok) throw new Error("فشل الطلب");\n  console.log(await r.json());\n}\nload();', "jsc")
E("js_class", ["كيف انشئ كلاس في جافاسكربت", "class و extends جافاسكربت", "الوراثة في جافاسكربت"],
  "class تعرّف قالبا، وconstructor يجهز الكائن، وextends للوراثة وsuper لاستدعاء الأب.", "javascript",
  'class A {\n  constructor(n) { this.n = n; }\n  hi() { return "مرحبا " + this.n; }\n}\nclass B extends A {\n  hi() { return super.hi() + "!"; }\n}\nconsole.log(new B("سعد").hi());', "js", "مرحبا سعد!")
E("js_closure", ["ما هو closure في جافاسكربت", "الاغلاق closure مثال عداد"],
  "الدالة الداخلية تتذكر متغيرات الدالة التي أنشأتها حتى بعد انتهائها.", "javascript",
  "function counter() {\n  let c = 0;\n  return () => ++c;\n}\nconst next = counter();\nconsole.log(next(), next());", "js", "1 2")
E("js_json", ["كيف اتعامل مع json في جافاسكربت", "JSON.parse و JSON.stringify"],
  "JSON.parse تحول النص إلى كائن، وJSON.stringify تحول الكائن إلى نص.", "javascript",
  'const o = JSON.parse(\'{"a":1}\');\nconsole.log(o.a, JSON.stringify({ x: [1, 2] }));', "js", '1 {"x":[1,2]}')
E("js_template", ["ما هي template literals في جافاسكربت", "كيف ادمج متغير في نص جافاسكربت"],
  "استخدم علامة ` (backtick) و${متغير} لإدخال القيم في النص.", "javascript",
  "const name = 'علي';\nconsole.log(`مرحبا ${name}، 2+3=${2 + 3}`);", "js", "مرحبا علي، 2+3=5")
E("js_sort_numbers", ["لماذا sort لا ترتب الارقام صح في جافاسكربت", "ترتيب الارقام جافاسكربت"],
  "sort ترتب كنصوص افتراضيا (10 قبل 9). مرر دالة مقارنة للأرقام.", "javascript",
  "console.log(JSON.stringify([10, 9, 1].sort()), JSON.stringify([10, 9, 1].sort((a, b) => a - b)));", "js", "[1,10,9] [1,9,10]")
E("js_map_set", ["ما هو Map و Set في جافاسكربت", "حذف التكرار من مصفوفة جافاسكربت"],
  "Set لا تقبل التكرار، وMap قاموس يقبل أي نوع مفتاح.", "javascript",
  'const m = new Map([["a", 1]]);\nm.set("b", 2);\nconsole.log(m.size, [...new Set([1, 1, 2])].length);', "js", "2 2")
E("js_try_catch", ["معالجة الاخطاء في جافاسكربت try catch", "throw جافاسكربت"],
  "ضع الكود في try وامسك الخطأ في catch، وthrow ترمي خطأ بنفسك.", "javascript",
  'try {\n  throw new Error("مشكلة");\n} catch (e) {\n  console.log(e.message);\n}', "js", "مشكلة")
E("js_dom_event", ["كيف اربط زر بدالة في جافاسكربت", "addEventListener", "تغيير محتوى عنصر في الصفحة DOM"],
  "اختر العنصر بـ querySelector ثم اربط الحدث بـ addEventListener وعدّل textContent.", "javascript",
  'const btn = document.querySelector("#btn");\nbtn.addEventListener("click", () => {\n  document.querySelector("#out").textContent = "تم الضغط";\n});', "jsc")
E("js_localstorage", ["كيف احفظ بيانات في المتصفح localStorage", "تخزين محلي جافاسكربت"],
  "localStorage يحفظ نصوصا بالمفتاح والقيمة وتبقى بعد اغلاق الصفحة. حول الكائنات بـ JSON.", "javascript",
  'localStorage.setItem("user", JSON.stringify({ name: "سعد" }));\nconst u = JSON.parse(localStorage.getItem("user"));\nconsole.log(u.name);', "jsc")
E("js_node_server", ["كيف انشئ سيرفر بسيط في node", "express او http في node js"],
  "وحدة http المدمجة في Node تكفي لخادم بسيط.", "javascript",
  'const http = require("http");\nhttp.createServer((req, res) => {\n  res.end("مرحبا");\n}).listen(3000);', "jsc")

# ---------------- HTML / CSS ----------------
E("html_page", ["كيف اكتب صفحة html عربية", "هيكل صفحة html الاساسي", "html rtl عربي"],
  "اجعل الاتجاه rtl واللغة ar في وسم html وحدد ترميز UTF-8.", "html",
  '<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>صفحتي</title>\n</head>\n<body>\n  <h1>مرحبا</h1>\n  <p>هذه فقرة.</p>\n</body>\n</html>')
E("html_form", ["كيف اعمل نموذج form في html", "حقل ادخال وزر في html"],
  "النموذج form يحوي حقولا input وزر submit، وlabel لكل حقل.", "html",
  '<form>\n  <label for="n">الاسم</label>\n  <input id="n" name="name" required>\n  <button type="submit">ارسال</button>\n</form>')
E("html_elements", ["كيف اضيف رابط وصورة وقائمة في html", "وسوم html المهمة"],
  "الرابط a، الصورة img (مع alt)، القوائم ul وli.", "html",
  '<a href="https://example.com">رابط</a>\n<img src="a.png" alt="وصف الصورة">\n<ul>\n  <li>الاول</li>\n  <li>الثاني</li>\n</ul>')
E("css_center", ["كيف اوسط عنصر في css", "توسيط div في المنتصف", "center div css"],
  "أسهل طريقة: flex مع justify-content و align-items على الأب.", "css",
  ".parent {\n  display: flex;\n  justify-content: center;\n  align-items: center;\n  min-height: 100vh;\n}")
E("css_flex", ["ما هو flexbox في css", "كيف اعمل صف عناصر متساوية css", "display flex"],
  "flexbox ترتب العناصر في صف أو عمود. flex:1 توزع المساحة بالتساوي.", "css",
  ".row {\n  display: flex;\n  gap: 12px;\n}\n.row > div {\n  flex: 1;\n}")
E("css_grid", ["ما هو css grid", "كيف اعمل شبكة اعمدة css", "grid-template-columns"],
  "grid تقسم الصفحة لصفوف وأعمدة. repeat وfr تحدد الأعمدة.", "css",
  ".grid {\n  display: grid;\n  grid-template-columns: repeat(3, 1fr);\n  gap: 16px;\n}")
E("css_responsive", ["كيف اجعل الصفحة متجاوبة مع الجوال", "media query css", "responsive design"],
  "أضف وسم viewport في html واستخدم media query لتغيير التنسيق حسب العرض.", "css",
  "@media (max-width: 600px) {\n  .grid {\n    grid-template-columns: 1fr;\n  }\n}")
E("css_vars_dark", ["كيف اعمل الوضع الليلي dark mode في css", "متغيرات css variables"],
  "عرّف الألوان كمتغيرات ثم بدّلها داخل prefers-color-scheme.", "css",
  ":root { --bg: #fff; --fg: #111; }\n@media (prefers-color-scheme: dark) {\n  :root { --bg: #111; --fg: #eee; }\n}\nbody { background: var(--bg); color: var(--fg); }")

# ---------------- SQL ----------------
E("sql_basic", ["كيف انشئ جدول واضيف بيانات sql", "create table و insert", "استعلام select بسيط"],
  "CREATE TABLE ينشئ الجدول، INSERT يضيف صفا، SELECT يقرأ البيانات.", "sql",
  "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER);\nINSERT INTO users (name, age) VALUES ('سعد', 20), ('سارة', 25);\nSELECT * FROM users;", "sql")
E("sql_where_order", ["كيف افلتر النتائج في sql where", "order by و limit في sql"],
  "WHERE يفلتر الصفوف، ORDER BY يرتب، LIMIT يحدد العدد.", "sql",
  "CREATE TABLE users (name TEXT, age INTEGER);\nINSERT INTO users VALUES ('a', 20), ('b', 30), ('c', 25);\nSELECT name FROM users WHERE age >= 25 ORDER BY age DESC LIMIT 2;", "sql")
E("sql_join", ["ما هو join في sql", "كيف اربط جدولين في sql", "inner join و left join"],
  "JOIN يربط جدولين بعمود مشترك. INNER يعيد المتطابق فقط، وLEFT يبقي كل صفوف الجدول الأيسر.", "sql",
  "CREATE TABLE users (id INTEGER, name TEXT);\nCREATE TABLE orders (id INTEGER, user_id INTEGER, total REAL);\nINSERT INTO users VALUES (1, 'سعد');\nINSERT INTO orders VALUES (1, 1, 50.0);\nSELECT u.name, o.total FROM users u JOIN orders o ON o.user_id = u.id;", "sql")
E("sql_group", ["كيف اجمع واعد في sql group by", "دوال COUNT و SUM و AVG"],
  "GROUP BY يجمع الصفوف المتشابهة، وتستخدم معه COUNT وSUM وAVG. HAVING يفلتر المجموعات.", "sql",
  "CREATE TABLE s (city TEXT, v INTEGER);\nINSERT INTO s VALUES ('x', 1), ('x', 2), ('y', 5);\nSELECT city, COUNT(*), SUM(v) FROM s GROUP BY city HAVING SUM(v) > 2;", "sql")
E("sql_update_delete", ["كيف اعدل واحذف بيانات في sql", "update و delete", "حذف سجل او صف من جدول"],
  "دائما ضع WHERE مع UPDATE وDELETE وإلا تتأثر كل الصفوف.", "sql",
  "CREATE TABLE t (id INTEGER, n TEXT);\nINSERT INTO t VALUES (1, 'a'), (2, 'b');\nUPDATE t SET n = 'z' WHERE id = 1;\nDELETE FROM t WHERE id = 2;\nSELECT * FROM t;", "sql")
E("sql_index", ["ما هو الفهرس index في قواعد البيانات", "كيف اسرع استعلام sql"],
  "الفهرس يسرّع البحث في العمود لكنه يبطئ الإضافة قليلا ويستهلك مساحة. أنشئه للأعمدة التي تبحث بها كثيرا.", "sql",
  "CREATE TABLE u (id INTEGER, email TEXT);\nCREATE INDEX idx_u_email ON u(email);", "sql")

# ---------------- Bash / Git ----------------
E("sh_basics", ["ما هي اوامر لينكس الاساسية", "اوامر الطرفية terminal الاساسية", "ls cd mkdir"],
  "ls تعرض الملفات، cd تنتقل بين المجلدات، mkdir تنشئ مجلدا، cp تنسخ، mv تنقل، rm تحذف (بحذر).", "bash",
  "pwd\nls -la\nmkdir مشروع\ncd مشروع\ncp a.txt b.txt\nmv b.txt c.txt", "sh")
E("sh_grep_find", ["كيف ابحث داخل الملفات grep", "امر find لينكس"],
  "grep تبحث عن نص داخل الملفات، وfind تبحث عن ملفات بالاسم.", "bash",
  'grep -rn "TODO" .\nfind . -name "*.py"', "sh")
E("sh_loop", ["كيف اكتب حلقة for في bash", "سكربت bash بسيط"],
  "السكربت ملف نصي يبدأ بـ shebang، وتشغله بعد chmod +x.", "bash",
  '#!/bin/bash\nfor f in *.txt; do\n  echo "ملف: $f"\ndone', "sh")
E("git_basics", ["كيف ابدا مشروع git", "اوامر git الاساسية", "git add commit"],
  "git init ينشئ المستودع، add يجهز التغييرات، commit يحفظها كنسخة.", "bash",
  'git init\ngit add .\ngit commit -m "اول نسخة"\ngit status\ngit log --oneline', "sh")
E("git_branch", ["كيف انشئ فرع branch في git", "دمج الفروع merge", "git checkout switch"],
  "الفرع نسخة موازية للعمل. أنشئه، اشتغل عليه، ثم ادمجه في الفرع الرئيسي.", "bash",
  "git switch -c feature\n# ... تعديلات و commit ...\ngit switch main\ngit merge feature", "sh")
E("git_undo", ["كيف اتراجع عن تعديل في git", "الغاء اخر commit", "git restore reset"],
  "restore يتراجع عن تعديلات الملف قبل commit، وreset --soft HEAD~1 يلغي آخر commit ويبقي التعديلات.", "bash",
  "git restore ملف.txt\ngit reset --soft HEAD~1", "sh")
E("git_github", ["كيف ارفع مشروعي على github", "git push و remote", "الفرق بين git و github"],
  "Git أداة لتتبع النسخ على جهازك، وGitHub موقع يستضيف المستودعات. اربطهما بـ remote ثم push.", "bash",
  "git remote add origin https://github.com/user/repo.git\ngit branch -M main\ngit push -u origin main", "sh")

# ---------------- Kotlin / Java / C (not executed here) ----------------
E("kt_basics", ["كيف اكتب برنامج كوتلن", "متغيرات كوتلن val و var", "اساسيات kotlin"],
  "val ثابت وvar متغير. كوتلن تستنتج النوع، والدالة تبدأ بـ fun.", "kotlin",
  'fun main() {\n    val name = "نواة"\n    var n = 1\n    n += 1\n    println("$name $n")\n}')
E("kt_null", ["ما هو null safety في كوتلن", "علامة ؟ و !! في كوتلن", "التعامل مع null في kotlin"],
  "النوع String? يقبل null. استخدم ?. للوصول الآمن و?: لقيمة بديلة، وتجنب !! لأنها تسبب انهيارا.", "kotlin",
  'val s: String? = null\nprintln(s?.length ?: 0)')
E("kt_class", ["كيف انشئ كلاس في كوتلن", "data class كوتلن", "class kotlin"],
  "data class تولد toString وequals وcopy تلقائيا للكلاسات التي تحمل بيانات.", "kotlin",
  'data class User(val name: String, val age: Int)\n\nfun main() {\n    val u = User("سعد", 20)\n    println(u.copy(age = 21))\n}')
E("kt_when_lists", ["ما هو when في كوتلن", "القوائم و lambda في كوتلن", "map و filter كوتلن"],
  "when بديل switch أقوى. القوائم لها map وfilter وsum مثل بايثون.", "kotlin",
  'val xs = listOf(1, 2, 3, 4)\nprintln(xs.filter { it % 2 == 0 }.map { it * 10 })\nval r = when (xs.size) {\n    0 -> "فارغة"\n    in 1..3 -> "صغيرة"\n    else -> "كبيرة"\n}')
E("kt_coroutines", ["ما هي coroutines في كوتلن", "كيف اشغل كود في الخلفية في اندرويد"],
  "coroutines تسمح بتنفيذ عمل طويل (شبكة، ملفات) بدون تجميد الواجهة، وتُشغل بـ launch داخل scope مناسب.", "kotlin",
  'lifecycleScope.launch {\n    val data = withContext(Dispatchers.IO) { loadFromNetwork() }\n    textView.text = data\n}')
E("java_hello", ["كيف اكتب برنامج جافا", "hello world java", "كلاس main في جافا"],
  "كل برنامج جافا داخل class، والتنفيذ يبدأ من الدالة main.", "java",
  'public class Main {\n    public static void main(String[] args) {\n        System.out.println("مرحبا");\n    }\n}')
E("c_hello", ["كيف اكتب برنامج بلغة سي", "hello world c", "المؤشرات pointers في c"],
  "في C تدير الذاكرة بنفسك. المؤشر متغير يحمل عنوان متغير آخر، وprintf للطباعة.", "c",
  '#include <stdio.h>\n\nint main(void) {\n    int x = 5;\n    int *p = &x;\n    printf("%d\\n", *p);\n    return 0;\n}')

# ---------------- Android ----------------
E("android_lifecycle", ["ما هي دورة حياة Activity في اندرويد", "onCreate onStart onResume", "lifecycle اندرويد"],
  "الترتيب: onCreate ← onStart ← onResume (ظاهرة وتتفاعل) ← onPause ← onStop ← onDestroy. جهز الواجهة في onCreate، واحفظ البيانات في onPause/onStop.", "")
E("android_permissions", ["كيف اطلب صلاحية في اندرويد", "permissions اندرويد الكاميرا", "requestPermissions"],
  "اعلن الصلاحية في AndroidManifest.xml، وللصلاحيات الخطرة اطلبها وقت التشغيل ووضّح للمستخدم سبب الطلب.", "xml",
  '<uses-permission android:name="android.permission.CAMERA"/>')
E("android_intent", ["ما هو Intent في اندرويد", "كيف افتح شاشة جديدة في اندرويد", "startActivity"],
  "الـ Intent رسالة تطلب فتح شاشة أو تطبيق آخر، وتحمل بيانات بـ putExtra.", "kotlin",
  'val i = Intent(this, SecondActivity::class.java)\ni.putExtra("name", "سعد")\nstartActivity(i)')
E("android_gradle", ["ما هو gradle في اندرويد", "كيف ابني ملف apk", "فشل بناء التطبيق gradle"],
  "Gradle أداة البناء. الأمر gradle assembleDebug يبني APK للتجربة. عند الفشل اقرأ أول سطر خطأ (error:) في السجل، فهو غالبا السبب الحقيقي.", "bash",
  "./gradlew assembleDebug", "sh")
E("android_ui_thread", ["لماذا يتجمد تطبيقي في اندرويد", "التطبيق يعلق ويتوقف", "NetworkOnMainThreadException", "thread الواجهة الرئيسي"],
  "الواجهة تعمل على خيط واحد. لا تنفذ عملا طويلا أو شبكة عليه؛ شغله في خيط/coroutine ثم حدّث الواجهة عبر runOnUiThread.", "")

# ---------------- Concepts ----------------
E("c_api", ["ما هو API", "ايش معنى واجهة برمجة التطبيقات", "تعريف api"],
  "الـ API طريقة محددة يتكلم بها برنامج مع برنامج آخر: ترسل طلبا بصيغة معروفة وتستلم ردا (غالبا JSON).", "")
E("c_rest", ["ما هو REST", "طرق HTTP GET POST PUT DELETE", "ما الفرق بين get و post"],
  "GET لقراءة البيانات، POST لإنشاء، PUT/PATCH للتعديل، DELETE للحذف. كل مورد له رابط مثل /users/1.", "")
E("c_http_codes", ["ما معنى اكواد HTTP 200 404 500", "رموز حالة http", "ما هو خطأ 404"],
  "200 نجاح، 201 تم الإنشاء، 400 طلب خاطئ، 401 غير مصرح، 403 ممنوع، 404 غير موجود، 500 خطأ في الخادم.", "")
E("c_oop", ["ما هي اساسيات البرمجة الكائنية", "الاربع ركائز OOP", "encapsulation inheritance polymorphism"],
  "الأركان: التغليف (إخفاء التفاصيل)، الوراثة، تعدد الأشكال (نفس الاسم بسلوك مختلف)، والتجريد (إظهار الضروري فقط).", "")
E("c_bigo", ["ما هو Big O", "تعقيد الخوارزميات", "ايش معنى O(n)"],
  "Big O يصف كيف يزيد الزمن مع حجم المدخلات: O(1) ثابت، O(log n) البحث الثنائي، O(n) مرور واحد، O(n log n) ترتيب سريع، O(n²) حلقتان متداخلتان.", "")
E("c_algorithm", ["ما هي الخوارزمية", "تعريف algorithm"],
  "الخوارزمية خطوات محددة ومرتبة لحل مشكلة، مثل وصفة الطبخ: مدخلات، خطوات، مخرجات.", "")
E("c_compiler", ["الفرق بين compiler و interpreter", "ما هو المترجم والمفسر", "لغة مترجمة ولغة مفسرة"],
  "المترجم يحول كل الكود إلى ملف تنفيذي قبل التشغيل (C، Kotlin). المفسر ينفذ الكود سطرا سطرا (بايثون، جافاسكربت).", "")
E("c_library_framework", ["الفرق بين library و framework", "المكتبة والاطار"],
  "المكتبة أنت تستدعيها وقت ما تحتاج. الإطار (framework) هو الذي يستدعي كودك ضمن هيكله.", "")
E("c_sql_nosql", ["الفرق بين SQL و NoSQL", "متى استخدم قاعدة بيانات علائقية"],
  "SQL جداول وعلاقات وبنية ثابتة (PostgreSQL، MySQL). NoSQL مرنة بوثائق أو مفاتيح (MongoDB، Redis). اختر SQL عندما تكون العلاقات والدقة مهمة.", "")
E("c_debug", ["كيف اصلح الاخطاء debugging", "الكود لا يعمل ماذا افعل", "طريقة تتبع الخطأ في البرنامج", "الكود فيه خطأ وش اسوي", "البرنامج ما يشتغل"],
  "1) اقرأ رسالة الخطأ كاملة وانظر آخر سطر ورقم السطر. 2) كرّر المشكلة بأصغر مثال. 3) اطبع قيم المتغيرات أو استخدم debugger. 4) غيّر شيئا واحدا كل مرة. 5) ابحث بنص الخطأ نفسه.", "")
E("c_read_error", ["كيف اقرا رسالة الخطأ في بايثون", "ما معنى traceback", "SyntaxError و NameError و TypeError"],
  "اقرأ الـ traceback من الأسفل: آخر سطر يذكر نوع الخطأ وسببه. SyntaxError خطأ كتابة، NameError اسم غير معرّف، TypeError نوع غير مناسب، IndexError فهرس خارج المدى، KeyError مفتاح غير موجود.", "")
E("c_clean_code", ["كيف اكتب كود نظيف", "نصائح لتحسين جودة الكود", "clean code"],
  "اختر أسماء واضحة، اجعل الدالة تعمل شيئا واحدا، لا تكرر الكود (DRY)، اكتب تعليقا للسبب لا للوصف، واختبر الكود.", "")
E("c_roadmap", ["كيف ابدا تعلم البرمجة", "خطة تعلم البرمجة للمبتدئين", "من اين ابدا في البرمجة"],
  "ابدأ بلغة واحدة (بايثون سهلة). تعلم: المتغيرات، الشروط، الحلقات، الدوال، القوائم والقواميس. ثم ابنِ مشاريع صغيرة (آلة حاسبة، قائمة مهام) وبعدها تعلم Git وقواعد البيانات. الممارسة اليومية أهم من كثرة الدروس.", "")
E("c_async_sync", ["الفرق بين المتزامن وغير المتزامن", "synchronous و asynchronous"],
  "المتزامن ينفذ خطوة بعد خطوة وينتظر. غير المتزامن يبدأ عملا بطيئا (شبكة) ويكمل الباقي ثم يعالج النتيجة عند وصولها.", "")
E("c_git_why", ["لماذا استخدم git", "ما فائدة التحكم بالاصدارات"],
  "Git يحفظ تاريخ التعديلات، يسمح بالتراجع، ويتيح لعدة أشخاص العمل على نفس المشروع بدون ضياع عمل بعض.", "")
E("c_security", ["كيف احمي تطبيقي من الاختراق", "نصائح امان البرمجة", "sql injection"],
  "لا تثق بمدخلات المستخدم: استخدم استعلامات مهيأة (parameterized) ضد SQL injection، لا تخزن كلمات السر نصا (استخدم تجزئة مثل bcrypt)، ولا تضع المفاتيح السرية في الكود أو GitHub.", "")
E("c_ai_model", ["ما هو نموذج الذكاء الاصطناعي اللغوي", "كيف يتعلم النموذج", "ما هو التدريب training"],
  "النموذج اللغوي شبكة عصبية تتعلم توقع الحرف أو الكلمة التالية من نصوص كثيرة. جودته تعتمد على حجمه وكمية وجودة بيانات التدريب، فالنموذج الصغير الذي دُرّب على بيانات قليلة يحفظ أكثر مما يفهم.", "")

# ---------------- added later: Arabic dictionary/grammar + more Python (see kb_arabic.py, kb_python2.py) ----------------
import kb_arabic, kb_python2
kb_arabic.register(E)
kb_python2.register(E)
