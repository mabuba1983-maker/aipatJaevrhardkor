# -*- coding: utf-8 -*-
import json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from nuwaa.memory.kb import KB, HIGH, LOW, tokens

def make_kb():
    kb = KB().load_jsonl(ROOT / "data/kb/kb.jsonl")
    for f in ("arabic_chat", "python_chat", "instructions_ar"): kb.load_jsonl(ROOT / "data" / f"{f}.jsonl")
    return kb

# queries written AFTER the phrasings in kb_entries.py (SET1 partly used while tuning, FRESH only after) -> id (or ids joined by |)
SET1 = [
 ("وش الفرق بين let و const في جافاسكربت","js_vars"),("ابي اتعلم الحلقات في بايثون for","py_for"),("كيف اكتب دالة بايثون ترجع قيمة","py_function"),
 ("شلون اقرأ ملف نصي بايثون","py_file"),("كيف اعمل كلاس واستخدمه في python","py_class"),("اريد مثال على try except","py_exceptions"),
 ("ايش هو الـ API","c_api"),("وش معنى خطأ 404","c_http_codes"),("كيف ارفع الكود على github","git_github"),("اريد اتعلم البرمجة من الصفر","c_roadmap"),
 ("كيف اتجاوز خطأ NameError","c_read_error"),("كيف اوسّط الdiv بالcss","css_center"),("ما هو ال flexbox","css_flex"),
 ("كيف اربط جدولين في قاعدة البيانات","sql_join"),("كيف احذف صف من جدول sql","sql_update_delete"),("اعطني مثال على async await","js_async"),
 ("كيف اجمع عناصر المصفوفة بجافاسكربت","js_array_methods"),("ما هي دورة حياة النشاط في الاندرويد","android_lifecycle"),("كيف اطلب اذن الكاميرا في تطبيق اندرويد","android_permissions"),
 ("كيف اتعامل مع القيم الفارغة في كوتلن","kt_null"),("ما هو الديكوريتر","py_decorator"),("كيف احول نص الى json في بايثون","py_json"),
 ("اشرح لي big o","c_bigo"),("ما الفرق بين المترجم والمفسر","c_compiler"),("كيف اثبت مكتبة في بايثون","py_venv"),
 ("وش هو list comprehension","py_list_comp"),("كيف ابحث عن رقم في قائمة مرتبة بسرعة","py_binary_search"),("كيف اعكس نص في بايثون","py_slicing"),
 ("كيف اسوي موقع بايثون","py_flask"),("كيف اغير لون الخلفية للوضع الداكن","css_vars_dark"),("الكود حقي فيه خطأ وش اسوي","c_debug"),
 ("كيف انشئ فرع جديد في جيت","git_branch"),("وش هو الاطار framework","c_library_framework"),("كيف احمي كلمات السر","c_security"),
 ("كيف اضيف عنصر لقائمة","py_list"),("كيف اطبع نص في جافا","java_hello"),("ما هو gradle","android_gradle"),("لماذا يتجمد التطبيق عندي","android_ui_thread"),
 ("كيف اعرف عدد تكرار كل كلمة","py_counter|py_count_words"),("كيف احسب الفرق بين تاريخين","py_datetime"),
]
FRESH = [  # written after tuning; ids accepted if the top answer is any of the listed entries
 ("وش يسوي الامر print","py_hello"),("ابغى افهم المتغيرات","py_variables"),("كيف اقرا رقم من المستخدم","py_input"),
 ("كيف اكرر امر عشر مرات في بايثون","py_for"),("كيف اجيب اكبر رقم بقائمة بايثون","py_sort|py_list|py_min_max_sum"),("كيف احول قائمة الى مجموعة بدون تكرار","py_set"),
 ("شنو الفرق بين tuple و list","py_tuple"),("كيف اضمن ان الملف يتقفل بعد القراءة","py_file"),("وش هو yield","py_generator"),
 ("كيف استخرج الارقام من نص بالregex","py_regex"),("كيف اسوي كلاس يرث من كلاس ثاني","py_inherit"),("كيف احسب فيبوناتشي بسرعة","py_memo"),
 ("كيف اطلب بيانات من موقع بايثون","py_requests"),("وش الفرق بين == و is","py_is_eq"),("ايش معنى async و await","js_async"),
 ("كيف اغير نص عنصر في الصفحة بالجافاسكربت","js_dom_event"),("كيف احفظ بيانات في المتصفح","js_localstorage"),("ليش ترتيب الارقام في js غلط","js_sort_numbers"),
 ("كيف اكتب شبكة بثلاث اعمدة","css_grid"),("كيف اخلي الصفحة تناسب الجوال","css_responsive"),("كيف اسوي نموذج تسجيل في html","html_form"),
 ("وش الفرق بين inner join و left join","sql_join"),("كيف اعد الصفوف لكل مدينة في sql","sql_group"),("كيف اسرع البحث في قاعدة البيانات","sql_index"),
 ("كيف اتراجع عن اخر commit","git_undo"),("كيف ادمج فرعين في git","git_branch"),("اوامر لينكس الاساسية","sh_basics"),
 ("كيف اعرف كلاس في كوتلن data class","kt_class"),("كيف اشغل شغل طويل في الخلفية بدون تجميد الواجهة","kt_coroutines|android_ui_thread"),
 ("كيف افتح شاشة ثانية في تطبيقي","android_intent"),("ما معنى 401 و 403","c_http_codes"),("كيف اتجنب ثغرة sql injection","c_security"),
 ("كيف اعرف ان كودي سريع","c_bigo"),("ايش الفرق بين stack و queue","py_stack_queue"),("ما هو التعلم الالي وكيف يتدرب النموذج","c_ai_model"),
]
OOD = ["ما هو سعر الذهب اليوم","من فاز بكاس العالم","كيف اطبخ كبسة","احكي لي نكتة","ما عاصمة فرنسا","وش الجو في الرياض","كيف ارتب غرفتي","من هو اغنى رجل في العالم","كم عمر الشمس","ما معنى الحياة","كيف اخسر وزني","وين اقرب مطعم","اكتب لي قصيدة","كيف اسافر لتركيا"]

class KbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.kb = make_kb()
    def test_every_own_question_finds_itself(self):
        for l in (ROOT / "data/kb/kb.jsonl").read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            for q in d["q"]:
                s, it = self.kb.search(q, 1)[0]; self.assertGreaterEqual(s, 0.99, q)
    def test_paraphrase_quality(self):
        confident = right = top1 = 0
        for q, exp in SET1 + FRESH:
            r = self.kb.search(q, 1); s, it = r[0] if r else (0, None)
            ok = it is not None and (it["id"] in exp.split("|") or (it["id"] == "" and s >= HIGH))   # an old hand-written pair may also answer correctly
            top1 += ok
            if s >= HIGH: confident += 1; right += ok
        n = len(SET1 + FRESH)
        print(f"\n  paraphrases: top1 {top1}/{n}; confident {confident}, of which right {right}")
        self.assertGreaterEqual(top1 / n, 0.80)
        self.assertGreaterEqual(right / max(1, confident), 0.95)        # when it answers confidently it must be right
    def test_unrelated_questions_never_answered_confidently(self):
        for q in OOD: self.assertLess(self.kb.best(q)[1], HIGH, q)
    def test_language_mismatch_is_penalised(self):
        s, it = self.kb.search("كيف اجمع عناصر المصفوفة بجافاسكربت", 1)[0]
        self.assertNotIn("python", it["lang"])
    def test_arabic_normalisation(self):
        self.assertEqual(tokens("أَكْتُبْ دالّة"), tokens("اكتب دالة"))
        self.assertEqual(tokens("احسب ٢ + ٣"), tokens("احسب 2 + 3"))

class CodeSamplesAreReallyRun(unittest.TestCase):
    def test_all_checkable_samples_pass_and_file_is_in_sync(self):
        import gen_knowledge
        out = Path(tempfile.mkdtemp()) / "kb.jsonl"; rows = gen_knowledge.build(str(out))
        self.assertGreaterEqual(sum(1 for r in rows if r["v"] == 2), 50)
        self.assertEqual(out.read_text(encoding="utf-8"), (ROOT / "data/kb/kb.jsonl").read_text(encoding="utf-8"))

if __name__ == "__main__": unittest.main()
