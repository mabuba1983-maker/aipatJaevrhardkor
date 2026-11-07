package ai.nuwaa

import android.content.Context
import android.graphics.BitmapFactory
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

class Answer(val text: String, val source: String, val file: MadeFile? = null)

/** A file the user sent with the + button. Up to 8 MB is kept in memory (a whole Quran text file fits). Sent files are read-only; files are created only when the user picks «إنشاء ملف». */
class Attached(val name: String, val size: Long, val bytes: ByteArray, val truncated: Boolean) { var announced = false }

/** One brain per process. Every chat message is answered by the language model WRITING the reply (no canned phrase, no lookup, no confidence gate);
 *  exact arithmetic is the only tool kept. Active sessions are cached in RAM; their complete transcript is archived on disk and replayed in chunks when needed.
 *  Model parameters, global learning records, and per-conversation history are stored separately. */
class Brain private constructor(private val ctx: Context) {
    companion object {
        @Volatile private var inst: Brain? = null

        fun get(c: Context): Brain {
            val i = inst
            if (i != null) return i
            synchronized(Brain::class.java) {
                val j = inst
                if (j != null) return j
                val b = Brain(c.applicationContext)
                b.loadKnowledge()
                inst = b
                return b
            }
        }
    }

    /** Verified programming snippets: used ONLY by the code page and to read files and the screen. Never used to answer a chat message. */
    val kb = Kb()
    @Volatile var modelStatus: String = "النموذج: لم يُحمَّل بعد"
    @Volatile var goal: String = ""

    var nlm: Nlm? = null
        private set
    private val lock = Any()
    private val sessions = LinkedHashMap<String, NlmSession>()
    private val nlmUserFile = File(ctx.filesDir, "nlm2_user.bin")
    private val nlmBackupFile = File(ctx.filesDir, "nlm2_user.bin.bak")
    // All learned material is stored on disk, separately from model parameters.
    // RAM keeps only a bounded working set for current training/retrieval.
    private val storage = NuwaaStorage(File(ctx.filesDir, "storage"))
    private var observed = 0
    private var lastReport = JSONObject()
    private var rehearsal = ""            // a sample of the original training text, replayed during self-development so nothing known is forgotten

    private fun readAsset(name: String): String =
        ctx.assets.open(name).bufferedReader(Charsets.UTF_8).use { r -> r.readText() }

    fun loadKnowledge() {
        try { Nlp.load(readAsset("syn.json")) } catch (e: Exception) { Nlp.load("{\"phrases\":{},\"words\":{},\"stop\":[],\"langs\":[]}") }
        try { kb.loadJsonl(readAsset("kb.jsonl")) } catch (e: Exception) { /* asset missing: the code page just has no snippets */ }
        try { rehearsal = readAsset("rehearse.txt") } catch (e: Exception) { rehearsal = "" }
        loadNlm()
    }

    private fun refreshMemoryStatus(m: Nlm) {
        modelStatus = "نموذج نواة (GRU): " + m.paramCount() + " معامل · ذاكرة RAM نشطة " + m.long.activeRecordCount() +
            " سجل (~" + (m.long.estimatedMemoryBytes() / 1024L) + " KB) · مرحّل من RAM منذ التشغيل " + m.long.archivedFromRam +
            " · أرشيف التخزين " + storage.count() + " سجل"
    }

    /** assets/nlm2.bin = the pretrained start; filesDir/nlm2_user.bin = what it learned on this phone (the long-term memory of the weights). */
    private fun loadNlm() {
        try {
            val base = ctx.assets.open("nlm2.bin").use { s -> s.readBytes() }
            val heapMb = Runtime.getRuntime().maxMemory() / 1e6      // no budget of mine: the only limit is what this phone really gives the app
            if (base.size * 3.0 / 1e6 > heapMb * 0.85) { modelStatus = "النموذج: تخطيته لأن ذاكرة هذا الجهاز للتطبيق ${heapMb.toInt()} MB فقط"; return }
            val m = try {
                when {
                    nlmUserFile.exists() -> try { Nlm.load(nlmUserFile.readBytes()) } catch (_: Throwable) {
                        if (nlmBackupFile.exists()) Nlm.load(nlmBackupFile.readBytes()) else Nlm.load(base)
                    }
                    nlmBackupFile.exists() -> Nlm.load(nlmBackupFile.readBytes())
                    else -> Nlm.load(base)
                }
            } catch (_: Throwable) { Nlm.load(base) }     // a damaged user file or interrupted save never blocks the start
            // RAM is only the active working set. Its budget is recalculated from live heap pressure;
            // older records remain in the append-only disk archive and can be retrieved when relevant.
            m.long.setBudgetProvider { Effort.memoryWorkingSetBytes() }
            val restoreBytes = Effort.memoryWorkingSetBytes() / 32L
            storage.forEachRecentText(restoreBytes) { line -> m.long.addNewestFirst(line) }
            nlm = m
            refreshMemoryStatus(m)
        } catch (e: java.io.FileNotFoundException) {
            modelStatus = "النموذج غير موجود في التطبيق (nlm2.bin)"
        } catch (e: Throwable) {
            modelStatus = "تعذر تحميل النموذج: " + (e.message ?: e.javaClass.simpleName)
        }
    }

    /** Kept for the start-up code: the model is loaded by loadKnowledge(); this only reports whether it is there. */
    fun loadModel() { /* nothing to do: loadKnowledge() already loaded it when the brain was created */ }

    private fun saveNlm() {
        try {
            nlm?.let { m ->
                val bytes = synchronized(lock) { m.toBytes() }
                val temp = File(ctx.filesDir, "nlm2_user.bin.tmp")
                if (temp.exists()) temp.delete()
                java.io.FileOutputStream(temp).use { out -> out.write(bytes); out.fd.sync() }
                if (nlmUserFile.exists()) {
                    if (nlmBackupFile.exists() && !nlmBackupFile.delete()) throw IllegalStateException("تعذر حذف النسخة الاحتياطية القديمة")
                    if (!nlmUserFile.renameTo(nlmBackupFile)) throw IllegalStateException("تعذر حفظ النسخة الاحتياطية")
                }
                if (!temp.renameTo(nlmUserFile)) {
                    if (nlmBackupFile.exists() && !nlmUserFile.exists()) nlmBackupFile.renameTo(nlmUserFile)
                    throw IllegalStateException("تعذر تثبيت ملف الأوزان الجديد")
                }
                if (nlmBackupFile.exists()) nlmBackupFile.delete()
            }
        } catch (_: Throwable) { /* retain the previous checkpoint; a later save can retry */ }
    }

    fun usedMb(): Double = android.os.Debug.getPss() / 1024.0

    /** Grows the model to (newE, newH), persists it immediately (so it survives a restart even before any training), and clears per-session
     *  memory (the vocabulary/shape changed under them). Returns a human-readable result; never throws. Safety: refuses if the grown model's
     *  training footprint (weights + Adam m + Adam v, the same ~3x rule loadNlm already uses) would not fit in what THIS phone actually granted
     *  the app right now — never a fixed number, always Runtime.getRuntime().maxMemory() at the moment of the attempt. */
    fun growModel(newE: Int, newH: Int): String {
        val m = nlm ?: return "النموذج غير محمّل."
        if (newE < m.e || newH < m.h) return "الحجم الجديد لازم يكون أكبر من الحالي."
        val projectedParams = (m.chars.size.toLong() * newE) + (newE.toLong() * 3 * newH + newH.toLong() * 3 * newH + 3L * newH) +
            (newH.toLong() * 3 * newH + newH.toLong() * 3 * newH + 3L * newH) + newH.toLong() * m.chars.size + m.chars.size
        val heap = Runtime.getRuntime().maxMemory(); val needed = projectedParams * 4.0 * 3.0
        if (needed > heap * 0.6) return "⚠ ما قدرت: هذا الحجم يحتاج تقريبا " + (needed / 1e6).toInt() + " MB، وذاكرة هذا الجهاز للتطبيق الآن " + (heap / 1e6).toInt() + " MB فقط. جرّب حجما أصغر."
        return try {
            val grown = synchronized(lock) { val g = Nlm.grow(m, newE, newH); nlm = g; sessions.clear(); g }
            saveNlm()
            "✅ كبّرت النموذج فعلا: من " + m.paramCount() + " إلى " + grown.paramCount() + " معامل. يبدأ بنفس سلوك القديم تماما، والمعرفة الإضافية فارغة حتى يتدرب. احفظت الحالة الجديدة؛ افتح ⚡ رفع الفهم لتدريبه."
        } catch (e: Throwable) { "⚠ فشل التكبير: " + (e.message ?: e.javaClass.simpleName) }
    }

    /** One fresh, memory-off attempt (nothing is remembered, nothing is looked up): used by the self-review. */
    fun selfAttempt(q: String): String {
        val m = nlm ?: return ""
        return synchronized(lock) { NlmSession(m, System.nanoTime()).reply(q, 500, 0.5f, 8, 0.15f, false, 0f, 0f).first }
    }

    // ---- hooks for Trainer (the «raise understanding» button) ----
    val modelLock: Any get() = lock
    fun trainModel(): Nlm? = nlm
    fun saveTrained() = saveNlm()
    /** The training text shipped with the app: one pair per line, the two lines of a pair joined by a tab. Returned as «س:..\nج:..\n» blocks. */
    fun trainPairs(): List<String> = try {
        readAsset("train.txt").split("\n").filter { it.length > 6 }.map { it.replace('\t', '\n') + "\n" }
    } catch (e: Exception) { emptyList() }

    // ---------------------------------------------------------------- the conversation
    private fun replaySessionMessage(s: NlmSession, role: String, chunk: String, start: Boolean, end: Boolean) {
        if (start) s.feed(if (role == "u") "س:" else "ج:")
        s.feed(chunk)
        if (end) s.feed("\n")
    }

    private fun persistSessionMessage(convId: String, role: String, text: String) {
        val normalized = if (role == "u") text.replace("\n", " ¶ ").trim() else text.replace("\n", "¶").trim()
        try { storage.appendSessionMessage(convId, role, normalized) } catch (_: Throwable) { /* conversation still works if disk is unavailable */ }
    }

    private fun sessionFor(m: Nlm, convId: String): NlmSession {
        val existing = sessions.remove(convId)
        val s = existing ?: NlmSession(m, System.nanoTime()).also { fresh ->
            storage.forEachSessionChunk(convId) { role, chunk, start, end ->
                replaySessionMessage(fresh, role, chunk, start, end)
            }
        }
        sessions[convId] = s
        while (sessions.size > 8) { val k = sessions.keys.first(); sessions.remove(k) }
        return s
    }

    /** Every chat message enters here. convId = the conversation: its short-term memory is its own NlmSession. */
    fun answer(q: String, convId: String): Answer {
        val m = nlm ?: return Answer("النموذج غير محمّل: " + modelStatus, "none")
        return synchronized(lock) {
            val s = sessionFor(m, convId)
            val math = Skills.tryMath(q)
            var historyAnswer = ""
            val result = if (!Scope.inScope(q)) {
                historyAnswer = Scope.REFUSAL
                s.feed("س:" + q.replace("\n", " ¶ ").trim() + "\nج:" + historyAnswer.replace("\n", "¶") + "\n")
                Answer(historyAnswer, "scope")
            } else if (math != null) {
                historyAnswer = math
                s.feed("س:" + q.replace("\n", " ¶ ").trim() + "\nج:" + historyAnswer.replace("\n", "¶") + "\n")
                Answer(historyAnswer, "math")
            } else {
                val hit = try { kb.search(q, 1).firstOrNull()?.score ?: 0.0 } catch (e: Throwable) { 0.0 }
                val plan = Effort.plan(ctx, q, hit)
                val memories = try { storage.searchRelevant(q, 3).filter { it.score >= 0.18 } } catch (_: Throwable) { emptyList() }
                // Restore only relevant archived memories into the RAM working set; FIFO spillover keeps it bounded.
                for (memory in memories) m.long.add(memory.text)
                refreshMemoryStatus(m)
                val verifiedExamples = try { kb.search(q, 2).filter { it.score >= Kb.LOW && it.item.v >= 1 } } catch (_: Throwable) { emptyList() }
                val generationPrompt = if (memories.isEmpty() && verifiedExamples.isEmpty()) q else buildString {
                    if (memories.isNotEmpty()) {
                        append("سياق مسترجع من ذاكرة المستخدم، استخدمه فقط إذا كان مرتبطاً بالطلب ولا تخترع تفاصيل غير موجودة فيه:\n")
                        for ((index, item) in memories.withIndex()) {
                            append("[ذكرى ").append(index + 1).append("] ").append(item.text).append("\n")
                        }
                    }
                    if (verifiedExamples.isNotEmpty()) {
                        append("أمثلة برمجية سابقة اجتازت فحصاً بدرجة تشغيل واحدة على الأقل؛ استخدمها كمرجع ولا تدّعِ أنك شغّلت كود الطلب الحالي:\n")
                        for ((index, hit) in verifiedExamples.withIndex()) {
                            append("[مثال متحقق ").append(index + 1).append("] ").append(hit.item.a.take(1800)).append("\n")
                        }
                    }
                    append("طلب المستخدم الحالي:\n").append(q)
                }
                val t0 = System.nanoTime()
                val r = if (plan.tries > 1) s.replyThink(generationPrompt, plan.maxChars, plan.tries) else s.reply(generationPrompt, plan.maxChars, plan.temp)
                historyAnswer = r.first
                val made = maxOf(20, r.first.length) * plan.tries
                val ms = (System.nanoTime() - t0) / 1_000_000.0 / made
                Effort.msPerChar = if (Effort.msPerChar <= 0.0) ms else 0.7 * Effort.msPerChar + 0.3 * ms
                hear(m, q)
                var foot = ""
                if (plan.level == Level.THINK) foot = "\n\n🧠 وضع التفكير: جربت " + plan.tries + " محاولات واخترت الأوضح."
                else if (plan.note.isNotEmpty()) foot = "\n\n🔋 " + plan.note + ": رديت بإيجاز."
                Answer(FileTools.display(r.first) + foot, "lm")
            }
            persistSessionMessage(convId, "u", q)
            persistSessionMessage(convId, "a", historyAnswer)
            result
        }
    }

    /** Learning by listening: nothing to type, nothing announced. Long-term memory at once, the weights by a few small steps. */
    private fun hear(m: Nlm, q: String) {
        val line = q.replace("\n", " ").trim()
        if (line.isEmpty()) return
        // Persist first. Only after durable archival do we add the text to the bounded RAM working set.
        val archived = try {
            storage.append("conversation", line)
            true
        } catch (_: Throwable) {
            false
        }
        // Never let a RAM-only copy be evicted as though it were safely archived.
        if (archived) {
            m.observe(line)
            m.long.enforceBudget()
            refreshMemoryStatus(m)
        }
        observed++
        if (observed % 10 == 0) saveNlm()
    }

    /** If the message is a real request to create a file, returns what to write (the activity writes it and reports the truth); null if it is not such a request. */
    fun fileRequest(q: String, convId: String, lastBot: String, forced: Boolean = false): Pair<MadeFile?, String>? {
        val fr = FileTools.parseCreate(q, lastBot, kb, forced) ?: return null
        val f = fr.first
        if (f != null && f.note.isEmpty()) return fr                       // the user dictated the content: it is written exactly as said
        val m = nlm
        if (m != null) {
            // the MODEL builds the file: it chooses the name and writes the content (thinking mode: several attempts, the surest one wins)
            val project = Regex("مشروع|مجلد|ملفات|عدة|فولدر").containsMatchIn(q)
            val table = Regex("جدول|csv|بيانات|صفوف|أعمدة").containsMatchIn(q)
            // The same live heap-based budget used by chat; no separate tiny file/table cap.
            val attempts = when { project -> 3; table -> 2; else -> 3 }
            val outputLimit = Effort.outputCharBudget(attempts)

            // Code generation must receive the user's earlier project constraints, not just the latest sentence.
            // Retrieve from the complete disk archive; only the best few relevant records enter this prompt.
            val projectMemories = try {
                storage.searchRelevant(q, if (project) 6 else 3).filter { it.score >= 0.16 }
            } catch (_: Throwable) { emptyList() }
            val codeExamples = try {
                kb.search(q, if (project) 3 else 2).filter { it.score >= Kb.LOW && it.item.v >= 1 }
            } catch (_: Throwable) { emptyList() }
            val projectPrompt = if (projectMemories.isEmpty() && codeExamples.isEmpty()) q else buildString {
                if (projectMemories.isNotEmpty()) {
                    append("متطلبات وسياق سابق استُرجع من أرشيف المستخدم. اعتبرها قيوداً للمشروع فقط إذا كانت تخص المشروع الحالي، ولا تستبدل بها طلبه الحالي:\\n")
                    for ((index, memory) in projectMemories.withIndex()) {
                        append("[سياق سابق ").append(index + 1).append("] ")
                            .append(memory.text.take(1000)).append("\\n")
                    }
                }
                if (codeExamples.isNotEmpty()) {
                    append("أمثلة كود سابقة اجتازت تشغيلًا أو اختبارًا. هي مراجع فقط وليست دليلاً على تشغيل الملف الحالي:\\n")
                    for ((index, example) in codeExamples.withIndex()) {
                        append("[مثال ").append(index + 1).append("] ")
                            .append(example.item.a.take(1400)).append("\\n")
                    }
                }
                append("تعليمات صارمة للمهمة الحالية:\\n")
                append("- حافظ على كل شرط ذكره المستخدم في الطلب الحالي والسياق السابق المرتبط به.\\n")
                append("- لا تحذف ميزة موجودة ولا تغيّر ملفات غير مطلوبة.\\n")
                append("- لا تدّعِ أن الكود بُني أو شُغّل أو اختُبر؛ لم يحدث ذلك ضمن توليد النص.\\n")
                append("- إذا تعارضت المتطلبات أو نقصت معلومة تمنع إنشاء ملف صحيح، صرّح بالنقص بدلاً من اختراع قيمة.\\n")
                append("طلب المستخدم الحالي:\\n").append(q)
            }
            val written = synchronized(lock) {
                sessionFor(m, convId).replyThink(projectPrompt, outputLimit, attempts) { FileTools.allSane(it) }.first
            }
            val own = FileTools.fromModel(written)
            if (own != null) return Pair(own, "")
            val code = if (written.contains("```")) written.substringAfter("```").substringAfter('\n').substringBefore("```").trim('\n') else ""
            if (f != null && code.length >= 12) return Pair(MadeFile(f.name, (code + "\n").toByteArray(Charsets.UTF_8), "المحتوى كتبه النموذج نفسه"), "")
        }
        if (fr.first == null) return fr
        return Pair(null, "حاولت أكتب محتوى الملف وما طلع شيء واضح. قل لي المحتوى بنفسك: «أنشئ ملف ... فيه ...».")
    }

    /** The conversation ended: its short-term memory is gone. (What was said is already in the long-term memory.) */
    fun endConversation(convId: String) { synchronized(lock) { sessions.remove(convId) } }

    /** Rebuild the full conversation state. New archives replay from disk in bounded chunks; legacy chats stream every stored message. */
    fun resume(convId: String, msgs: List<Msg>) {
        val m = nlm ?: return
        synchronized(lock) {
            if (sessions.containsKey(convId)) return
            val s = NlmSession(m, System.nanoTime())
            val archived = storage.forEachSessionChunk(convId) { role, chunk, start, end ->
                replaySessionMessage(s, role, chunk, start, end)
            }
            if (!archived) {
                for (x in msgs) {
                    val role = if (x.role == "u") "u" else "a"
                    persistSessionMessage(convId, role, x.text)
                    val normalized = if (role == "u") x.text.replace("\n", " ¶ ").trim() else x.text.replace("\n", "¶").trim()
                    replaySessionMessage(s, role, normalized, true, true)
                }
            }
            sessions[convId] = s
            while (sessions.size > 8) sessions.remove(sessions.keys.first())
        }
    }

    // ---------------------------------------------------------------- self-development
    /** The self-development button: re-read everything heard, train on it, keep the result only if it got better. */
    fun develop(): String {
        val m = nlm ?: return "النموذج غير محمّل."
        val texts = storage.lastTexts(400).map { if (it.length > 2048) it.takeLast(2048) else it }
        if (texts.size < 3) return "ما فيه بيانات كافية في التخزين للتدريب بعد. أضف أمثلة أكثر ثم أعد المحاولة."
        val r = synchronized(lock) { m.develop(texts, 2, 3e-4f, rehearsal) }
        saveNlm()
        lastReport = JSONObject().put("heard", storage.count()).put("bits_before", r.first.toDouble()).put("bits_after", r.second.toDouble()).put("params", m.paramCount())
        val f = { x: Float -> String.format(java.util.Locale.US, "%.2f", x) }
        val sb = StringBuilder()
        sb.append("راجعت بيانات من التخزين. إجمالي السجلات: ").append(storage.count()).append(".\n")
        sb.append("• تدربت على آخر ").append(texts.size).append(" رسالة، وقست نفسي قبل وبعد: ").append(f(r.first)).append(" ← ").append(f(r.second)).append(" بت/حرف (الأقل أفضل).\n")
        if (r.second >= r.first) sb.append("• ما تحسّنت هذه المرة، فرجعت لأوزاني السابقة بدون تغيير.\n") else sb.append("• تحسّنت، وحفظت الأوزان الجديدة.\n")
        sb.append("• حجم النموذج: ").append(m.paramCount()).append(" معامل. التخزين المنفصل يحتوي ").append(storage.count()).append(" سجلًا.\n")
        sb.append("\nاضغط «ملف المطور» لأخرج لك ملفا فيه أوزاني الجديدة وذاكرتي وتقرير التحسن، وترسله لمن يفحصه.")
        return sb.toString()
    }

    private fun sha(b: ByteArray): String = java.security.MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { x -> String.format("%02x", x) }

    /** The developer file (a zip): manifest.json (report + sha256 of the other files), nlm2.bin (weights), memory.txt (long-term memory).
     *  `python -m nuwaa.lm.devfile check FILE` says whether it is broken. It holds weights and memory only: never code. */
    fun devFile(): ByteArray {
        val m = nlm ?: throw IllegalStateException("النموذج غير محمّل")
        val w = synchronized(lock) { m.toBytes() }
        val mem = storage.exportPlainText()
        val files = JSONObject().put("nlm2.bin", sha(w)).put("memory.txt", sha(mem))
        val man = JSONObject().put("version", 2).put("created", System.currentTimeMillis() / 1000).put("params", m.paramCount()).put("vocab", m.v)
            .put("emb", m.e).put("hid", m.h).put("memory_lines", storage.count()).put("files", files).put("report", lastReport).put("origin", "android")
        val bos = java.io.ByteArrayOutputStream()
        java.util.zip.ZipOutputStream(bos).use { z ->
            z.putNextEntry(java.util.zip.ZipEntry("manifest.json")); z.write(man.toString(1).toByteArray(Charsets.UTF_8)); z.closeEntry()
            z.putNextEntry(java.util.zip.ZipEntry("nlm2.bin")); z.write(w); z.closeEntry()
            z.putNextEntry(java.util.zip.ZipEntry("memory.txt")); z.write(mem); z.closeEntry()
        }
        return bos.toByteArray()
    }

    private fun withNote(e: KbItem): String {
        if (!e.a.contains("```")) return e.a
        val note = when (e.v) {
            2 -> "✓ هذا الكود شُغِّل واختُبر ناتجه قبل إضافته إلى معرفتي."
            1 -> "✓ هذا الكود شُغِّل بدون أخطاء."
            0 -> "✓ فُحصت صياغة هذا الكود فقط (لم يُشغَّل بالكامل)."
            else -> "⚠ لم أستطع تشغيل هذا الكود هنا. جرّبه قبل الاعتماد عليه."
        }
        return e.a + "\n\n" + note
    }

    // ---------------- files (read-only) ----------------
    private fun decodeText(b: ByteArray): String? {
        val n = minOf(b.size, 4096)
        for (i in 0 until n) if (b[i].toInt() == 0) return null
        for (cut in 0..3) {                      // a 300 KB cut may land inside a multi-byte Arabic letter
            if (b.size - cut <= 0) break
            try {
                return Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(b, 0, b.size - cut)).toString()
            } catch (e: Exception) { /* try cutting one more byte */ }
        }
        return null
    }

    private fun magic(b: ByteArray): String {
        fun s(vararg v: Int): Boolean = b.size >= v.size && v.indices.all { i -> (b[i].toInt() and 255) == v[i] }
        return when {
            s(0x89, 0x50, 0x4E, 0x47) -> "صورة PNG"
            s(0xFF, 0xD8, 0xFF) -> "صورة JPEG"
            s(0x47, 0x49, 0x46, 0x38) -> "صورة GIF"
            s(0x25, 0x50, 0x44, 0x46) -> "ملف PDF"
            s(0x50, 0x4B, 0x03, 0x04) -> "ملف مضغوط (ZIP أو APK أو DOCX...)"
            s(0x7F, 0x45, 0x4C, 0x46) -> "برنامج ELF"
            else -> "ملف ثنائي غير معروف"
        }
    }

    private fun sizeText(n: Long): String = if (n >= 1_000_000) String.format(java.util.Locale.US, "%.1f MB", n / 1e6) else if (n >= 1000) (n / 1000).toString() + " KB" else "$n بايت"

    private val langNames = mapOf("py" to "بايثون", "js" to "جافاسكربت", "kt" to "كوتلن", "java" to "جافا", "html" to "HTML", "css" to "CSS", "sql" to "SQL",
        "sh" to "Bash", "c" to "C", "cpp" to "C++", "json" to "JSON", "xml" to "XML", "md" to "Markdown", "txt" to "نص", "csv" to "CSV", "ts" to "TypeScript", "go" to "Go", "rs" to "Rust", "php" to "PHP", "gradle" to "Gradle", "kts" to "كوتلن")
    private val defRe = Regex("""\b(?:def|function|fun|class|interface|object|struct|func)\s+([A-Za-z_]\w*)""")
    private val errWords = listOf("error", "exception", "traceback", "failed", "fatal", "خطأ", "فشل", "تعذر")

    /** Honest limit: Nuwaa sees the file as TEXT or as NUMBERS (bytes). It reports structure, finds lines that match your question and
     *  matches errors against its knowledge. It does not understand meaning and does not look at pictures. */
    fun answerAbout(att: Attached, q: String): Answer {
        val sb = StringBuilder()
        sb.append("📎 ").append(att.name).append(" · ").append(sizeText(att.size))
        if (att.truncated) sb.append(" (قرأت أول 8 MB فقط)")
        sb.append("\n")
        val text = FileTools.textOf(att.name, att.bytes)
        if (text == null) {
            sb.append("النوع: ").append(magic(att.bytes)).append("\nهذا ملف غير نصي (صورة أو PDF أو برنامج)، أقرأ منه البايتات فقط ولا أفهم محتواه.\n")
            val opts = BitmapFactory.Options(); opts.inJustDecodeBounds = true
            try { BitmapFactory.decodeByteArray(att.bytes, 0, att.bytes.size, opts) } catch (e: Throwable) { }
            if (opts.outWidth > 0) sb.append("أبعاد الصورة: ").append(opts.outWidth).append("×").append(opts.outHeight).append(" (ما أفهم محتواها)\n")
            val seen = BooleanArray(256); for (x in att.bytes) seen[x.toInt() and 255] = true
            sb.append("أول البايتات: ").append(att.bytes.take(24).joinToString(" ") { x -> (x.toInt() and 255).toString() })
            sb.append("\nعدد القيم المختلفة: ").append(seen.count { v -> v }).append(" من 256")
            return Answer(sb.toString(), "file")
        }
        return Answer(FileTools.answer(att.name, att.size, att.truncated, text, q, kb), "file")
    }

    /**
     * Sends a locally generated visual description into Nuwaa's language model.
     * The current GRU receives text concepts, not pixels or image embeddings.
     */
    fun answerVisual(imageName: String, question: String, visualDescription: String, convId: String): Answer {
        val ask = question.ifBlank { "صف لي ما الذي يظهر في هذه الصورة." }
        val prompt = "حلّل الصورة المرفقة باسم «" + imageName.take(100) + "». هذه ملاحظات محلل الرؤية المحلي: " +
            visualDescription.take(1600) + ". استخدمها كأدلة محدودة، ولا تخترع تفاصيل غير مكتشفة، وميّز بين ما رُصد وما لا يمكن الجزم به. سؤال المستخدم: " + ask
        return answer(prompt, convId)
    }

    /** Honest limit: this reads the TEXT on the screen (through the accessibility reader) and matches it with the knowledge base. It does not understand images. */
    fun adviseScreen(screen: String, goalText: String): String {
        val t = screen.trim()
        if (t.isEmpty()) return "لا أستطيع قراءة نص الشاشة الآن. فعّل «قارئ الشاشة» من التطبيق، ثم افتح الصفحة التي تريدها."
        val lines = t.lines().map { l -> l.trim() }.filter { l -> l.isNotEmpty() }
        val errWords = listOf("error", "exception", "failed", "traceback", "denied", "not found", "crash", "خطأ", "فشل", "تعذر", "غير موجود", "توقف")
        val errLine = lines.firstOrNull { l -> val lw = l.lowercase(); errWords.any { w -> lw.contains(w) } }
        val sb = StringBuilder()
        if (errLine != null) sb.append("لاحظت رسالة تشبه خطأ: «").append(errLine.take(120)).append("»\nاقرأ الرسالة كاملة، وابحث بنصها نفسه، وغيّر شيئا واحدا كل مرة.\n")
        if (goalText.isNotBlank()) sb.append("هدفك: «").append(goalText.take(80)).append("».\n")
        val shown = lines.filter { l -> l.length in 2..20 }.take(8)
        if (shown.isNotEmpty()) sb.append("العناصر الظاهرة الآن: ").append(shown.joinToString("، "))
        // this is a fixed, rule-based reading of the screen (real text, real error detection) — never the model talking, and never a looked-up canned line
        return "📱 قراءة آلية للشاشة (ليست من النموذج):\n" + sb.toString().trim()
    }
}
