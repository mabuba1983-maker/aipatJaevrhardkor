package ai.nuwaa

/**
 * Small, isolated web-search decision layer.
 * It only adds web context to factual/current-information questions.
 * If search fails, the original prompt is returned unchanged.
 */
object WebDecision {
    private val searchSignals = listOf(
        "ابحث", "ابحث لي", "مصدر", "مصادر", "رابط",
        "آخر الأخبار", "اخر الاخبار", "آخر تحديث", "اخر تحديث",
        "اليوم", "حاليا", "حالياً", "الآن", "الان",
        "سعر", "أسعار", "اسعار", "موعد", "نتيجة", "نتائج",
        "من هو", "من هي", "متى", "أين", "اين",
        "ما هو", "ما هي", "وش最新", "latest", "today",
        "current", "recent", "price", "news", "version"
    )

    private val simpleChat = listOf(
        "هلا", "مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير",
        "شكرا", "يعطيك العافية", "كيف حالك"
    )

    fun prepare(query: String): String {
        val q = query.trim()
        if (q.length < 12 || simpleChat.any { q.equals(it, ignoreCase = true) }) return query
        if (q.matches(Regex("""[\\d٠-٩۰-۹\\s+\\-*/().،,=×÷]+"""))) return query

        val lower = q.lowercase(java.util.Locale.ROOT)
        val shouldSearch = searchSignals.any { lower.contains(it.lowercase(java.util.Locale.ROOT)) }
        if (!shouldSearch) return query

        return try {
            val context = TavilySearch.search(q, 4)
            if (context.isBlank() || context == "لم يُعثر على نتائج مفيدة.") query
            else """
                سؤال المستخدم:
                $q

                معلومات ويب حديثة جُمعت لهذا السؤال:
                $context

                أجب عن سؤال المستخدم اعتماداً على المعلومات أعلاه عند صلتها بالسؤال.
                ميّز بين المعلومة المؤكدة وغير المؤكدة، ولا تخترع تفاصيل أو مصادر.
                إذا لم تكفِ النتائج، صرّح بأن المعلومات غير كافية.
            """.trimIndent()
        } catch (_: Throwable) {
            // Network/API failures must never stop the existing local model.
            query
        }
    }
}
