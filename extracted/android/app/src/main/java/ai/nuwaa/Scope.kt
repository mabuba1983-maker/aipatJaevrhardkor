package ai.nuwaa

/** Mirror of nuwaa/skills/scope.py: a fixed, rule-based specialization check that runs BEFORE the model, not the model judging itself.
 *  Nuwaa only answers programming, Arabic and English questions; anything clearly outside that is refused honestly instead of risking a made-up
 *  answer. Deliberately conservative: an ambiguous message is allowed through rather than wrongly refused. */
object Scope {
    const val REFUSAL = "أنا متخصص فقط في البرمجة واللغة العربية والإنجليزية، وهذا السؤال خارج تخصصي، فلن أعطيك جوابا قد يكون غير دقيق. " +
        "اسألني عن كود، أو خطأ برمجي، أو قاعدة نحوية أو إملائية، أو ترجمة، وسأساعدك."

    private val IN_SCOPE = listOf(
        "بايثون", "python", "كود", "برنام", "خوارزم", "دالة", "متغير", "حلقة", "مصفوفة", "قائمة", "قاموس", "كلاس", "class", "function",
        "javascript", "kotlin", "java", "html", "css", "sql", "git", "api", "json", "csv", "ملف", "مشروع", "تطبيق", "سيرفر", "server",
        "bug", "error", "خطا", "اصلاح", "صحح", "راجع", "تتبع", "trace", "compile", "debug", "نحو", "صرف", "اعراب",
        "همزه", "تاء مربوطه", "املاء", "لغه عربيه", "قواعد عربيه", "arabic grammar", "english grammar", "ترجم", "translate",
        "grammar", "vocabulary", "tense", "verb", "noun", "sentence")
    private val OUT_OF_SCOPE = listOf(
        "ابني بيت", "بناء بيت", "اعمار", "مقاول", "وصفه", "طبخه", "طبخ", "اكله", "كبسه", "عاصمه", "تاريخ الدوله", "حرب عالميه",
        "تشخيص مرض", "تشخيص", "مرض", "جرعه دواء", "اعراض مرض", "تصليح سياره", "صيانه سياره", "محرك سياره", "فلك", "تنجيم", "ابراج",
        "حكم شرعي", "فتوى", "تفسير سوره", "وزن طفل", "رجيم", "تمارين رياضيه", "رياضه كره", "دوري كره", "نتيجه مباراه",
        "سعر الذهب", "سعر العمله", "اسهم", "بورصه", "عقار للبيع", "حجز فندق", "تذكره طيران")

    private fun norm(t: String): String {
        var s = t.lowercase(java.util.Locale.ROOT)
        s = s.replace(Regex("[إأآا]"), "ا").replace("ى", "ي").replace("ة", "ه")
        s = s.replace(Regex("(?<=\\s)ال(?=\\w)|^ال(?=\\w)"), "")
        return s.replace(Regex("\\s+"), " ").trim()
    }

    fun inScope(q: String): Boolean {
        val n = norm(q)
        if (IN_SCOPE.any { n.contains(norm(it)) }) return true
        if (OUT_OF_SCOPE.any { n.contains(norm(it)) }) return false
        return true
    }
}
