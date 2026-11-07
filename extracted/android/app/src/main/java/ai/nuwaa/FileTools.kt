package ai.nuwaa

import java.io.ByteArrayInputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.zip.ZipInputStream

/** A file Nuwaa was asked to create. It is written by MainActivity; the reply says "created" only after the bytes were really written and re-read. */
class MadeFile(val name: String, val bytes: ByteArray, val note: String, val more: List<MadeFile> = emptyList())

/** Reads the REAL content of a sent file and answers questions about it by computing on it (counts, searches, line lookups, top words, duplicates).
 *  Honest limit: it does not understand meaning; it never invents lines: everything shown comes from the file with its line number. */
object FileTools {
    // ------------------------------------------------------------ text extraction
    private fun decodeUtf8(b: ByteArray, len: Int = b.size): String? {
        for (cut in 0..3) {                      // a size cut may land inside a multi-byte Arabic letter
            if (len - cut <= 0) break
            try {
                return Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(b, 0, len - cut)).toString().removePrefix("\uFEFF")
            } catch (e: Exception) { /* try cutting one more byte */ }
        }
        return null
    }

    /** Text of a file, or null if it is not text. Handles UTF-8, UTF-16 (BOM), Windows-1256 Arabic, and the text inside .docx. */
    fun textOf(name: String, b: ByteArray): String? {
        if (b.size >= 4 && b[0] == 0x50.toByte() && b[1] == 0x4B.toByte()) return zipText(name, b)
        val n = minOf(b.size, 4096)
        if (b.size >= 2 && ((b[0] == 0xFF.toByte() && b[1] == 0xFE.toByte()) || (b[0] == 0xFE.toByte() && b[1] == 0xFF.toByte())))
            return try { String(b, Charsets.UTF_16) } catch (e: Exception) { null }
        for (i in 0 until n) if (b[i].toInt() == 0) return null
        decodeUtf8(b)?.let { return it }
        // not valid UTF-8: old Arabic files are often Windows-1256
        return try { String(b, java.nio.charset.Charset.forName("windows-1256")) } catch (e: Exception) { null }
    }

    private fun zipText(name: String, b: ByteArray): String? {
        val sb = StringBuilder()
        try {
            ZipInputStream(ByteArrayInputStream(b)).use { z ->
                var e = z.nextEntry
                var count = 0
                while (e != null && count < 200) {
                    count++
                    val en = e.name
                    val lower = en.lowercase(java.util.Locale.ROOT)
                    val data = z.readBytes()
                    if (lower == "word/document.xml") {
                        val xml = String(data, Charsets.UTF_8)
                        return xml.replace(Regex("</w:p>"), "\n").replace(Regex("<[^>]+>"), "")
                            .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"")
                    }
                    val isText = lower.endsWith(".txt") || lower.endsWith(".md") || lower.endsWith(".py") || lower.endsWith(".kt") || lower.endsWith(".json") ||
                        lower.endsWith(".csv") || lower.endsWith(".js") || lower.endsWith(".html") || lower.endsWith(".java") || lower.endsWith(".xml") || lower.endsWith(".css")
                    if (isText && !e.isDirectory) { sb.append("=== ").append(en).append(" ===\n"); decodeUtf8(data)?.let { sb.append(it).append("\n") } }
                    else if (!e.isDirectory) sb.append("# ملف داخل الأرشيف: ").append(en).append(" (").append(data.size).append(" بايت)\n")
                    e = z.nextEntry
                }
            }
        } catch (ex: Exception) { return null }
        return if (sb.isEmpty()) null else sb.toString()
    }

    // ------------------------------------------------------------ question understanding
    private val commandWords = setOf("كم", "عدد", "مره", "مرة", "تكرر", "تكرار", "تكررت", "ابحث", "بحث", "اين", "وين", "جد", "اعطني", "اعرض", "اظهر", "اطلع", "سطر", "اسطر", "سطور",
        "كلمه", "كلمة", "كلمات", "عن", "في", "فيه", "هذا", "الملف", "ملف", "لي", "من", "هل", "يوجد", "موجود", "ورد", "وردت", "تظهر", "ظهرت", "ما", "هي", "هو", "اكتب", "قل", "لخص", "راجع",
        "عباره", "عبارة", "جمله", "جملة", "لو", "سمحت", "ممكن", "يا", "نواه", "نواة", "الي", "الى", "إلى", "على", "علي", "اللي", "الذي", "التي", "فقط")

    private fun quoted(q: String): String? {
        val m = Regex("[«\"“'‘]([^»\"”'’]{1,80})[»\"”'’]").find(q)
        return m?.groupValues?.get(1)?.trim()?.ifEmpty { null }
    }

    /** The word or phrase the user is asking about. */
    private fun term(q: String): String {
        quoted(q)?.let { return Nlp.norm(it).trim() }
        val nq = Nlp.norm(q)
        val after = Regex("(?:كلمه|عباره|جمله|لفظ|عن|ابحث|ورد|وردت|يوجد|بكلمه)\\s+(.+)$").find(nq)?.groupValues?.get(1)
        val cand = (after ?: nq).split(Regex("\\s+")).filter { it.isNotEmpty() && it !in commandWords && !it.all { c -> c.isDigit() } }
        return cand.joinToString(" ").trim()
    }

    private fun has(nq: String, vararg w: String): Boolean = w.any { nq.contains(Nlp.norm(it)) }

    private fun lineNo(nq: String): Int? =
        Regex("(?:سطر|السطر|رقم)\\s*(\\d{1,7})").find(nq)?.groupValues?.get(1)?.toIntOrNull()

    // ------------------------------------------------------------ answers
    fun answer(name: String, size: Long, truncated: Boolean, text: String, q: String, kb: Kb): String {
        val lines = text.split("\n").map { it.trimEnd('\r') }
        val normLines = ArrayList<String>(lines.size)
        for (l in lines) normLines.add(Nlp.norm(l))
        val words = ArrayList<String>()
        for (l in normLines) for (w in l.split(Regex("[^\\p{L}\\p{N}_]+"))) if (w.isNotEmpty()) words.add(w)
        val nonBlank = lines.count { it.isNotBlank() }
        val nq = Nlp.norm(q)
        val sb = StringBuilder()
        val head = "📎 " + name + " · " + lines.size + " سطر (" + nonBlank + " غير فارغ) · " + words.size + " كلمة · " + text.length + " حرف" + (if (truncated) " · قرأت أول جزء فقط من الملف لكبره" else "")

        val ln = lineNo(nq)
        val t = term(q)
        when {
            ln != null -> {
                if (ln < 1 || ln > lines.size) sb.append("الملف فيه ").append(lines.size).append(" سطر فقط، ولا يوجد سطر ").append(ln).append(".")
                else for (i in maxOf(1, ln - 1)..minOf(lines.size, ln + 1)) sb.append("سطر ").append(i).append(": ").append(lines[i - 1].trim().take(300)).append(if (i == ln) "  ◀" else "").append("\n")
            }
            has(nq, "كم سطر", "عدد الاسطر", "عدد السطور", "كم عدد الاسطر", "كم سطرا") && t.isEmpty() || (has(nq, "كم سطر", "عدد الاسطر") && t.isEmpty()) ->
                sb.append("عدد الأسطر: ").append(lines.size).append(" (غير الفارغة: ").append(nonBlank).append(").")
            has(nq, "كم كلمه", "عدد الكلمات", "كم عدد الكلمات") && t.isEmpty() ->
                sb.append("عدد الكلمات: ").append(words.size).append(" · المختلفة منها: ").append(words.toHashSet().size).append(".")
            has(nq, "اكثر الكلمات", "اشهر الكلمات", "الاكثر تكرارا", "اكثر كلمه") -> {
                val cnt = HashMap<String, Int>()
                for (w in words) if (w.length >= 3) cnt[w] = (cnt[w] ?: 0) + 1
                sb.append("أكثر الكلمات تكرارا (٣ أحرف فأكثر):\n")
                for ((w, c) in cnt.entries.sortedByDescending { it.value }.take(15)) sb.append("• ").append(w).append(" ← ").append(c).append("\n")
            }
            has(nq, "مكرر", "تكرار الاسطر", "اسطر مكرره") && t.isEmpty() || has(nq, "الاسطر المكرره", "اسطر مكرره") -> {
                val seen = HashMap<String, Int>()
                for ((i, l) in normLines.withIndex()) { val k = l.trim(); if (k.length >= 3) { val f = seen[k]; if (f == null) seen[k] = i + 1 } }
                val dup = ArrayList<Pair<Int, Int>>(); val first = HashMap<String, Int>()
                for ((i, l) in normLines.withIndex()) { val k = l.trim(); if (k.length < 3) continue; val f = first[k]; if (f == null) first[k] = i + 1 else dup.add(Pair(i + 1, f)) }
                if (dup.isEmpty()) sb.append("ما وجدت أسطرا مكررة.") else {
                    sb.append("وجدت ").append(dup.size).append(" سطرا مكررا. أمثلة:\n")
                    for ((a, b) in dup.take(10)) sb.append("سطر ").append(a).append(" يكرر سطر ").append(b).append(": ").append(lines[a - 1].trim().take(100)).append("\n")
                }
            }
            t.isNotEmpty() && (has(nq, "كم مره", "كم مرة", "عدد مرات", "كم تكرر", "كم ورد", "كم وردت", "عدد تكرار", "تكرار")) -> {
                var total = 0; var inLines = 0
                for (l in normLines) { var from = 0; var any = false; while (true) { val k = l.indexOf(t, from); if (k < 0) break; total++; any = true; from = k + maxOf(1, t.length) }; if (any) inLines++ }
                sb.append("«").append(t).append("» ظهرت ").append(total).append(" مرة في ").append(inLines).append(" سطر (العد يشمل ورودها داخل كلمات أطول مثل «و").append(t).append("»).")
            }
            t.isNotEmpty() && has(nq, "ابحث", "اين", "وين", "جد", "ورد", "وردت", "يوجد", "موجود", "سطر فيه", "اسطر فيها", "اعرض", "اظهر", "اطلع", "عن") -> sb.append(searchBlock(lines, normLines, t, 8))
            nq.isBlank() || has(nq, "لخص", "ملخص", "راجع", "افحص", "حلل", "ماذا في", "وش في", "ايش في", "محتوى", "اقرأ", "اقرا", "اعرض الملف") || t.isEmpty() -> sb.append(overview(name, lines, normLines, words, kb, text))
            else -> sb.append(searchBlock(lines, normLines, t, 6))
        }
        return (head + "\n\n" + sb.toString().trim()).trim()
    }

    private fun searchBlock(lines: List<String>, normLines: List<String>, t: String, limit: Int): String {
        val sb = StringBuilder()
        val hits = ArrayList<Int>()
        for ((i, l) in normLines.withIndex()) if (l.contains(t)) hits.add(i)
        if (hits.isNotEmpty()) {
            sb.append("وجدت «").append(t).append("» في ").append(hits.size).append(" سطر. أول النتائج:\n")
            for (i in hits.take(limit)) sb.append("سطر ").append(i + 1).append(": ").append(lines[i].trim().take(240)).append("\n")
            if (hits.size > limit) sb.append("… و").append(hits.size - limit).append(" نتيجة أخرى. اسألني عن سطر محدد بقولك: سطر ").append(hits[limit] + 1)
            return sb.toString()
        }
        // no exact phrase: rank lines by how many of the words they contain
        val ws = t.split(Regex("\\s+")).filter { it.length >= 2 }
        if (ws.isEmpty()) return "ما فهمت ما تريد أن أبحث عنه. اكتب الكلمة بين علامتي اقتباس، مثل: ابحث عن «الصبر»."
        val scored = ArrayList<Pair<Int, Int>>()
        for ((i, l) in normLines.withIndex()) { val sc = ws.count { l.contains(it) }; if (sc > 0) scored.add(Pair(sc, i)) }
        if (scored.isEmpty()) return "ما وجدت «" + t + "» في الملف (بحثت بعد توحيد الهمزات وإزالة التشكيل)."
        sb.append("ما وجدت العبارة كاملة، لكن هذه أقرب الأسطر:\n")
        for ((_, i) in scored.sortedWith(compareByDescending<Pair<Int, Int>> { it.first }.thenBy { it.second }).take(limit)) sb.append("سطر ").append(i + 1).append(": ").append(lines[i].trim().take(240)).append("\n")
        return sb.toString()
    }

    private val langOf = mapOf("py" to "بايثون", "js" to "جافاسكربت", "kt" to "كوتلن", "java" to "جافا", "html" to "HTML", "css" to "CSS", "json" to "JSON", "csv" to "CSV", "md" to "Markdown", "txt" to "نص", "xml" to "XML", "sql" to "SQL", "sh" to "Bash")
    private val defRe = Regex("""\b(?:def|function|fun|class|interface|object|struct|func)\s+([A-Za-z_]\w*)""")
    private val errWords = listOf("error", "exception", "traceback", "failed", "fatal", "خطأ", "فشل", "تعذر")

    private fun overview(name: String, lines: List<String>, normLines: List<String>, words: List<String>, kb: Kb, text: String): String {
        val sb = StringBuilder()
        val ext = name.substringAfterLast('.', "").lowercase(java.util.Locale.ROOT)
        sb.append("النوع: ").append(langOf[ext] ?: "نص").append("\n")
        val arabicLetters = text.count { it in '\u0621'..'\u064A' }
        if (arabicLetters > text.length / 4) sb.append("اللغة: الغالب عليه العربية، والتشكيل فيه ").append(text.count { it in '\u064B'..'\u0652' }).append(" علامة.\n")
        val defs = LinkedHashSet<String>()
        for (m in defRe.findAll(text)) { defs.add(m.groupValues[1]); if (defs.size >= 12) break }
        if (defs.isNotEmpty()) sb.append("التعريفات: ").append(defs.joinToString("، ")).append("\n")
        val first = lines.withIndex().filter { it.value.isNotBlank() }.take(5)
        sb.append("\nأول الأسطر:\n"); for ((i, l) in first) sb.append("سطر ").append(i + 1).append(": ").append(l.trim().take(160)).append("\n")
        val last = lines.withIndex().filter { it.value.isNotBlank() }.toList().takeLast(2)
        if (last.isNotEmpty()) { sb.append("\nآخر الأسطر:\n"); for ((i, l) in last) sb.append("سطر ").append(i + 1).append(": ").append(l.trim().take(160)).append("\n") }
        val heads = lines.withIndex().filter { (_, l) -> val k = l.trim(); k.length in 3..60 && (k.startsWith("سورة") || k.startsWith("باب") || k.startsWith("فصل") || k.startsWith("#") || k.lowercase().startsWith("chapter")) }.take(8)
        if (heads.isNotEmpty()) { sb.append("\nعناوين ظاهرة:\n"); for ((i, l) in heads) sb.append("سطر ").append(i + 1).append(": ").append(l.trim()).append("\n") }
        val cnt = HashMap<String, Int>()
        for (w in words) if (w.length >= 3) cnt[w] = (cnt[w] ?: 0) + 1
        val top = cnt.entries.sortedByDescending { it.value }.take(8)
        if (top.isNotEmpty()) sb.append("\nأكثر الكلمات تكرارا: ").append(top.joinToString("، ") { it.key + " (" + it.value + ")" }).append("\n")
        if (ext == "json") {
            val tt = text.trim()
            val j = try { if (tt.startsWith("[")) "مصفوفة JSON فيها " + org.json.JSONArray(tt).length() + " عنصر" else "كائن JSON فيه " + org.json.JSONObject(tt).length() + " مفتاح" } catch (e: Exception) { "⚠ JSON غير صالح: " + (e.message ?: "").take(80) }
            sb.append("\n").append(j).append("\n")
        }
        var shown = 0
        for ((i, l) in lines.withIndex()) {
            if (shown >= 3) break
            val lw = l.lowercase(java.util.Locale.ROOT)
            if (l.length < 400 && errWords.any { w -> lw.contains(w) }) {
                if (shown == 0) sb.append("\nأسطر تشبه أخطاء:\n")
                sb.append("سطر ").append(i + 1).append(": ").append(l.trim().take(120)).append("\n"); shown++
            }
        }
        val blank = lines.count { it.isBlank() }
        sb.append("\nجرّب أن تسألني: كم مرة ورد «كلمة»؟ · ابحث عن «عبارة» · سطر 100 · أكثر الكلمات تكرارا · الأسطر المكررة.")
        if (blank > lines.size / 2) sb.append("\n(أكثر من نصف الأسطر فارغة.)")
        return sb.toString()
    }

    // ------------------------------------------------------------ creating files
    private val createVerbs = listOf("انشئ", "أنشئ", "انشاء", "إنشاء", "انشي", "سوي", "سو لي", "اعمل", "جهز", "ولد", "اكتب لي ملف", "اكتب ملف", "اصنع", "صنع", "نشئ", "نشاء", "تسوي", "تعمل", "تجهز", "اكتبلي")
    private val questionStarts = listOf("كيف", "هل", "ماذا", "لماذا", "وش ", "ايش", "ما ")
    private val extWords = listOf(
        "py" to listOf("بايثون", "python", ".py", "بايثن"), "js" to listOf("جافاسكربت", "جافا سكربت", "javascript", ".js"),
        "html" to listOf("html", "صفحه ويب", "صفحة ويب", "موقع"), "css" to listOf("css", "ستايل"), "json" to listOf("json", "جيسون"),
        "csv" to listOf("csv", "جدول"), "md" to listOf("markdown", "ماركداون", ".md"), "sql" to listOf("sql", "قاعده بيانات", "قاعدة بيانات"),
        "kt" to listOf("كوتلن", "kotlin", ".kt"), "java" to listOf("جافا", " java"), "sh" to listOf("bash", "باش", ".sh"),
        "txt" to listOf("نصي", "نص ", "txt", "ملاحظات", "نص\u200f"))

    /** Returns the file to write if the message is a real request to create one (verb + the word «ملف»), else null. Never claims anything: the caller writes it. */
    // ---- files the MODEL builds itself: its reply holds  <<ملف:name.ext>> ... <<نهاية>>  and the app writes exactly that block ----
    private val blockRe = Regex("<<ملف:([^>\\n]{1,80})>>\\n?(.*?)\\n?<<نهاية>>", RegexOption.DOT_MATCHES_ALL)
    private val okExt = setOf("txt", "md", "csv", "json", "html", "css", "js", "py", "kt", "java", "sql", "sh", "xml")

    /** A safe file name from what the model wrote: no folders, no odd characters, a known extension; null if it is not usable. */
    fun cleanName(raw: String): String? {
        var n = raw.trim().substringAfterLast('/').substringAfterLast('\\')
        n = n.replace(Regex("[^\\p{L}\\p{N}_\\-. ]"), "").trim().replace(' ', '_').trimStart('.')
        val ext = n.substringAfterLast('.', "").lowercase(java.util.Locale.ROOT)
        if (n.length < 3 || n.length > 60 || ext !in okExt) return null
        return n
    }

    /** «folder/name.ext»: at most one folder, both parts cleaned (no «..», no odd characters), the file part with a known extension. */
    fun cleanPath(raw: String): String? {
        val parts = raw.trim().replace('\\', '/').split('/').filter { it.isNotBlank() }
        if (parts.isEmpty() || parts.size > 2) return null
        val file = cleanName(parts.last()) ?: return null
        if (parts.size == 1) return file
        val dir = parts[0].replace(Regex("[^\\p{L}\\p{N}_\\-]"), "").take(40)
        if (dir.isEmpty()) return null
        return dir + "/" + file
    }

    /** The file(s) the model wrote in its reply, or null if it wrote none (or only broken blocks). One block = one file; several blocks = a project:
     *  the first file comes back with the others in `more`. Nothing here is invented by the app. */
    fun fromModel(text: String): MadeFile? {
        val made = ArrayList<MadeFile>(); var total = 0
        for (m in blockRe.findAll(text)) {
            val name = cleanPath(m.groupValues[1]) ?: continue
            val body = m.groupValues[2]
            if (body.isBlank() || body.length > 20000) continue
            total += body.length
            if (made.size >= 12 || total > 60000) break
            if (made.any { it.name == name }) continue
            made.add(MadeFile(name, (body.trimEnd('\n') + "\n").toByteArray(Charsets.UTF_8), "المحتوى كتبه النموذج نفسه"))
        }
        if (made.isEmpty()) return null
        return MadeFile(made[0].name, made[0].bytes, made[0].note, made.drop(1))
    }

    /** A cheap on-phone check of what the model wrote (the phone cannot run Python): balanced brackets, a colon at the end of block heads, valid JSON,
     *  equal columns in csv, a complete html page. Used to prefer a better attempt in thinking mode; it can say «no», never «works». */
    fun sanityOk(name: String, body: String): Boolean {
        val ext = name.substringAfterLast('.', "").lowercase(java.util.Locale.ROOT)
        if (ext in setOf("py", "js", "json", "java", "kt", "css")) {
            if (body.count { it == '(' } != body.count { it == ')' } || body.count { it == '[' } != body.count { it == ']' } || body.count { it == '{' } != body.count { it == '}' }) return false
        }
        if (ext == "py") {
            for (ln in body.split("\n")) {
                val t = ln.trim()
                if (t.contains("#")) continue
                if (Regex("^(def|class|if|elif|for|while|with|try|except|finally)\\b.*").matches(t) && !t.endsWith(":")) return false
                if (t == "else" ) return false
            }
        }
        if (ext == "json") {
            val t = body.trim()
            try { if (t.startsWith("[")) org.json.JSONArray(t) else org.json.JSONObject(t) } catch (e: Exception) { return false }
        }
        if (ext == "csv") {
            val rows = body.trim().split("\n").filter { it.isNotBlank() }
            if (rows.isNotEmpty() && rows.any { it.count { c -> c == ',' } != rows[0].count { c -> c == ',' } }) return false
        }
        if (ext == "html" && body.contains("<html") && !body.contains("</html>")) return false
        return true
    }
    /** Every file block in a reply passes sanityOk (a reply with no block fails). */
    fun allSane(text: String): Boolean {
        var any = false
        for (m in blockRe.findAll(text)) { any = true; if (!sanityOk(m.groupValues[1], m.groupValues[2])) return false }
        return any
    }

    /** The reply as shown in the chat when no file is made: the block becomes a plain code box. */
    fun display(text: String): String = blockRe.replace(text) { r -> "```\n" + r.groupValues[2].trimEnd('\n') + "\n```" }

    fun parseCreate(q: String, lastBot: String, kb: Kb, forced: Boolean = false): Pair<MadeFile?, String>? {
        val t = q.trim()
        val nq = " " + Nlp.norm(t) + " "
        // an INDEFINITE «ملف» only: «الملف» / «للملف» point to a file that already exists («اعمل ملخص للملف» must not create anything)
        if (!forced) {      // not forced: only a clear order to create a file counts; with the file button pressed every message is such an order
            if (!Regex("\\sملفا?\\s").containsMatchIn(nq) && !nq.contains(" file ")) return null
            if (questionStarts.any { nq.trim().startsWith(Nlp.norm(it).trim()) }) return null
            if (createVerbs.none { nq.contains(Nlp.norm(it)) }) return null
        }
        var ext = ""
        for ((e, ws) in extWords) if (ws.any { nq.contains(Nlp.norm(it)) }) { ext = e; break }
        val explicit = Regex("([\\w\\-]{1,40})\\.(py|js|html|css|json|csv|md|sql|kt|java|sh|txt)").find(t)
        var name = ""
        if (explicit != null) { name = explicit.value; ext = explicit.groupValues[2] }
        if (ext.isEmpty()) ext = "txt"
        if (name.isEmpty()) {
            val nm = Regex("(?:باسم|اسمه|اسمها|سمه|سمها)\\s+([\\w\\-]{1,40})").find(t)?.groupValues?.get(1)
            name = (nm ?: "nuwaa") + "." + ext
        }
        // content: only what the user dictated; otherwise the MODEL writes it (Brain.fileRequest)
        var content = ""
        val dict = Regex("(?:فيه|فيها|يحتوي على|يحتوي|تحتوي على|تحتوي|محتواه|محتواها|نصه|نصها|مكتوب فيه|مكتوب فيها|يكتب|يطبع|تطبع)\\s*[:：]?\\s*(.+)$", RegexOption.DOT_MATCHES_ALL).find(t)
        if (dict != null) {
            val body = dict.groupValues[1].trim().trim('«', '»', '"', '“', '”')
            val verb = dict.value.substringBefore(body).trim()
            content = if (ext == "py" && (verb.startsWith("يطبع") || verb.startsWith("تطبع"))) "print(\"" + body.replace("\\", "\\\\").replace("\"", "\\\"") + "\")\n" else body + "\n"
        }
        val note = ""        // no pre-written content of any kind: not the verified examples, not an earlier reply. Only the user's own words, or what the model writes.
        if (content.isBlank()) {
            val descr = t.replace(Regex("ملف|انشئ|أنشئ|انشاء|إنشاء|سوي|اعمل|جهز|ولد|بايثون|لي|نصي|جافاسكربت|html|json|csv"), " ").trim().split(Regex("\\s+")).count { it.length >= 3 }
            if (descr >= 2) return Pair(MadeFile(name, ByteArray(0), "LM"), "")      // the request describes what it should hold: Brain asks the model to write it
        }
        if (content.isBlank()) return Pair(null, "أقدر أنشئ الملف، لكن ما أعرف ماذا أكتب فيه. قل مثلا: «أنشئ ملف نصي فيه ...» أو «أنشئ ملف بايثون يطبع مرحبا».")
        return Pair(MadeFile(name, content.toByteArray(Charsets.UTF_8), note), "")
    }
}
