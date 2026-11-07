package ai.nuwaa

import org.json.JSONObject
import java.io.File
import java.io.ByteArrayOutputStream
import java.io.RandomAccessFile

/**
 * Append-only disk storage. Complete history stays on disk; only bounded tails are read into RAM.
 * There is no arbitrary record-count cap. Real limits are available device storage and filesystem limits.
 */
data class MemoryMatch(val text: String, val score: Double, val type: String, val timestamp: Long = 0L)

class NuwaaStorage(private val dir: File) {
    private val data = File(dir, "records.jsonl")
    private val meta = File(dir, "index.json")
    private val lock = Any()
    private val sessionsDir = File(dir, "sessions")

    init { if (!dir.exists()) dir.mkdirs() }

    fun append(kind: String, text: String) = synchronized(lock) {
        if (text.isBlank()) return@synchronized
        if (!dir.exists() && !dir.mkdirs()) throw IllegalStateException("تعذر إنشاء مجلد التخزين")
        val next = count() + 1L
        val row = JSONObject().put("id", next).put("time", System.currentTimeMillis())
            .put("type", kind).put("text", text).toString()
        // The archive is the source of truth: force the record to disk before Brain admits it to RAM.
        java.io.FileOutputStream(data, true).use { out ->
            out.write((row + "\n").toByteArray(Charsets.UTF_8))
            out.fd.sync()
        }
        val metaTemp = File(dir, "index.json.tmp")
        if (metaTemp.exists()) metaTemp.delete()
        java.io.FileOutputStream(metaTemp).use { out ->
            out.write(JSONObject().put("count", next).put("updated", System.currentTimeMillis()).toString().toByteArray(Charsets.UTF_8))
            out.fd.sync()
        }
        if (meta.exists() && !meta.delete()) throw IllegalStateException("تعذر تحديث فهرس الذاكرة")
        if (!metaTemp.renameTo(meta)) throw IllegalStateException("تعذر تثبيت فهرس الذاكرة")
    }

    private fun lastRecordId(): Long {
        if (!data.exists() || data.length() == 0L) return 0L
        return try {
            RandomAccessFile(data, "r").use { file ->
                var pointer = file.length() - 1L
                val line = ByteArrayOutputStream()
                while (pointer >= 0L) {
                    file.seek(pointer)
                    val value = file.read()
                    if (value == 10 && line.size() > 0) break
                    if (value >= 0 && value != 10) line.write(value)
                    pointer--
                }
                val raw = String(line.toByteArray().reversedArray(), Charsets.UTF_8).trim()
                if (raw.isEmpty()) 0L else JSONObject(raw).optLong("id", 0L)
            }
        } catch (_: Throwable) { 0L }
    }

    fun count(): Long = synchronized(lock) {
        val cached = try { if (meta.exists()) JSONObject(meta.readText(Charsets.UTF_8)).optLong("count", 0L) else 0L }
            catch (_: Throwable) { 0L }
        val tail = lastRecordId()
        if (tail > 0L) maxOf(cached, tail)
        else if (cached > 0L) cached
        else if (data.exists()) try {
            RandomAccessFile(data, "r").use { file ->
                var rows = 0L
                while (file.readLine() != null) rows++
                rows
            }
        } catch (_: Throwable) { 0L }
        else 0L
    }

    /** Search the append-only archive one record at a time. The archive is never loaded into RAM as a whole.
     *  Only the best few matches are retained as a bounded working set; older records remain searchable on disk. */
    fun searchRelevant(query: String, limit: Int = 4): List<MemoryMatch> = synchronized(lock) {
        if (limit <= 0 || !data.exists() || query.isBlank()) return@synchronized emptyList()
        fun terms(value: String): Set<String> = try { Nlp.tokens(value) } catch (_: Throwable) { emptySet() }
        val wanted = terms(query)
        if (wanted.isEmpty()) return@synchronized emptyList()
        val best = ArrayList<MemoryMatch>(limit)
        data.bufferedReader(Charsets.UTF_8, 8192).use { reader ->
            while (true) {
                val line = reader.readLine() ?: break
                try {
                    val row = JSONObject(line)
                    val text = row.optString("text")
                    if (text.isBlank()) continue
                    val found = terms(text)
                    val overlap = wanted.count { it in found }
                    if (overlap == 0) continue
                    val coverage = overlap.toDouble() / wanted.size.toDouble()
                    val precision = overlap.toDouble() / found.size.coerceAtLeast(1).toDouble()
                    val phraseBonus = if (query.length >= 8 && text.contains(query, ignoreCase = true)) 1.0 else 0.0
                    val score = coverage * 0.75 + precision * 0.25 + phraseBonus
                    if (score < 0.12) continue
                    val item = MemoryMatch(text, score, row.optString("type"), row.optLong("time", 0L))
                    if (best.size < limit) {
                        best.add(item)
                    } else {
                        var worstIndex = 0
                        for (candidate in 1 until best.size) {
                            val current = best[candidate]
                            val worst = best[worstIndex]
                            if (current.score < worst.score ||
                                (current.score == worst.score && current.timestamp < worst.timestamp)) worstIndex = candidate
                        }
                        val worst = best[worstIndex]
                        if (item.score > worst.score ||
                            (item.score == worst.score && item.timestamp > worst.timestamp)) best[worstIndex] = item
                    }
                } catch (_: Throwable) { /* skip one damaged record; keep scanning the archive */ }
            }
        }
        best.sortedWith(compareByDescending<MemoryMatch> { it.score }.thenByDescending { it.timestamp })
    }

    /** Stream the complete archive chronologically, one record at a time. The caller must keep its own working set bounded. */
    fun forEachText(action: (String) -> Unit): Long = synchronized(lock) {
        if (!data.exists()) return@synchronized 0L
        var visited = 0L
        data.bufferedReader(Charsets.UTF_8, 8192).use { reader ->
            while (true) {
                val line = reader.readLine() ?: break
                try {
                    val text = JSONObject(line).optString("text")
                    if (text.isNotBlank()) { action(text); visited++ }
                } catch (_: Throwable) { /* skip a damaged record, keep the archive scan going */ }
            }
        }
        visited
    }

    /** Restore the newest archive records up to a byte budget. Reads backward and never scans the entire history. */
    fun forEachRecentText(maxTextBytes: Long, action: (String) -> Unit): Long = synchronized(lock) {
        if (maxTextBytes <= 0L || !data.exists()) return@synchronized 0L
        val newestFirst = ArrayList<String>()
        var usedBytes = 0L
        RandomAccessFile(data, "r").use { file ->
            var pointer = file.length() - 1L
            var line = ByteArrayOutputStream()
            fun consumeLine() {
                if (line.size() == 0) return
                try {
                    val bytes = line.toByteArray().reversedArray()
                    val text = JSONObject(String(bytes, Charsets.UTF_8)).optString("text")
                    if (text.isNotBlank() && usedBytes < maxTextBytes) {
                        val selected = if (text.length > 512) text.takeLast(512) else text
                        newestFirst.add(selected)
                        usedBytes += selected.length.toLong() * 2L
                    }
                } catch (_: Throwable) { /* ignore one damaged record */ }
                line = ByteArrayOutputStream()
            }
            while (pointer >= 0L && usedBytes < maxTextBytes) {
                file.seek(pointer)
                val value = file.read()
                if (value == 10) consumeLine() else if (value >= 0) line.write(value)
                pointer--
            }
            if (usedBytes < maxTextBytes) consumeLine()
        }
        for (text in newestFirst) action(text)
        newestFirst.size.toLong()
    }

    /**
     * Select a chronological, evenly spaced sample across the COMPLETE archive.
     * Only a caller-supplied byte budget is retained; no fixed message-count limit is used.
     */
    fun sampleTexts(maxTextBytes: Long): List<String> = synchronized(lock) {
        if (maxTextBytes <= 0L || !data.exists()) return@synchronized emptyList()
        var totalRows = 0L
        data.bufferedReader(Charsets.UTF_8, 8192).use { reader ->
            while (true) {
                val line = reader.readLine() ?: break
                try { if (JSONObject(line).optString("text").isNotBlank()) totalRows++ } catch (_: Throwable) { }
            }
        }
        if (totalRows == 0L) return@synchronized emptyList()
        val targetRows = (maxTextBytes / 4096L).coerceAtLeast(1L)
        val stride = ((totalRows + targetRows - 1L) / targetRows).coerceAtLeast(1L)
        val perRecordChars = (maxTextBytes / targetRows / 2L).coerceAtLeast(1L).coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
        val result = ArrayList<String>()
        var rowIndex = 0L
        var usedBytes = 0L
        data.bufferedReader(Charsets.UTF_8, 8192).use { reader ->
            while (true) {
                val line = reader.readLine() ?: break
                try {
                    val text = JSONObject(line).optString("text")
                    if (text.isBlank()) continue
                    if (rowIndex % stride == 0L && usedBytes < maxTextBytes) {
                        val remainingChars = ((maxTextBytes - usedBytes - 64L).coerceAtLeast(0L) / 2L)
                            .coerceAtMost(perRecordChars.toLong()).toInt()
                        if (remainingChars > 0) {
                            val selected = if (text.length <= remainingChars) text else if (remainingChars > 48) {
                                val side = remainingChars / 2
                                text.take(side) + " […] " + text.takeLast(remainingChars - side - 5)
                            } else text.take(remainingChars)
                            result.add(selected)
                            usedBytes += selected.length.toLong() * 2L + 64L
                        }
                    }
                    rowIndex++
                } catch (_: Throwable) { /* skip damaged record */ }
            }
        }
        result
    }

    /** Read only the latest N entries, without loading the full archive. */
    fun lastTexts(limit: Int): List<String> = synchronized(lock) {
        if (limit <= 0 || !data.exists()) return@synchronized emptyList()
        val rows = ArrayList<String>(limit)
        RandomAccessFile(data, "r").use { f ->
            var pointer = f.length() - 1
            var line = ByteArrayOutputStream()
            fun consumeLine() {
                if (line.size() == 0) return
                try {
                    val bytes = line.toByteArray().reversedArray()
                    rows.add(JSONObject(String(bytes, Charsets.UTF_8)).optString("text"))
                } catch (_: Throwable) { }
                line = ByteArrayOutputStream()
            }
            while (pointer >= 0 && rows.size < limit) {
                f.seek(pointer)
                val ch = f.read()
                if (ch == 10) consumeLine() else if (ch >= 0) line.write(ch)
                pointer--
            }
            if (rows.size < limit) consumeLine()
        }
        rows.reverse()
        rows
    }


    /** Persist a conversation message in bounded JSONL chunks, without a message-count cap. */
    fun appendSessionMessage(convId: String, role: String, text: String) = synchronized(lock) {
        if (text.isEmpty()) return@synchronized
        if (role != "u" && role != "a") throw IllegalArgumentException("Unknown session role")
        if (!sessionsDir.exists() && !sessionsDir.mkdirs()) throw IllegalStateException("تعذر إنشاء مجلد جلسات الذاكرة")
        val file = sessionFile(convId)
        java.io.FileOutputStream(file, true).bufferedWriter(Charsets.UTF_8).use { writer ->
            var offset = 0
            var first = true
            while (offset < text.length) {
                var next = minOf(offset + 4096, text.length)
                if (next < text.length && next > offset &&
                    java.lang.Character.isHighSurrogate(text[next - 1]) &&
                    java.lang.Character.isLowSurrogate(text[next])) next--
                val row = JSONObject()
                    .put("role", if (first) role else "")
                    .put("start", first)
                    .put("end", next == text.length)
                    .put("text", text.substring(offset, next))
                writer.append(row.toString()).append('\n')
                first = false
                offset = next
            }
        }
    }

    /** Replay one small text chunk at a time; start/end mark message boundaries. */
    fun forEachSessionChunk(convId: String, action: (String, String, Boolean, Boolean) -> Unit): Boolean = synchronized(lock) {
        val file = sessionFile(convId)
        if (!file.exists() || file.length() == 0L) return@synchronized false
        file.bufferedReader(Charsets.UTF_8).use { reader ->
            while (true) {
                val line = reader.readLine() ?: break
                try {
                    val row = JSONObject(line)
                    action(row.optString("role"), row.optString("text"),
                        row.optBoolean("start"), row.optBoolean("end"))
                } catch (_: Throwable) { /* skip a damaged row and continue */ }
            }
        }
        true
    }

    /** Return the first user request plus the newest user messages, bounded by a caller-supplied live context budget. */
    fun sessionUserContext(convId: String, maxChars: Int): String = synchronized(lock) {
        if (maxChars <= 0) return@synchronized ""
        val file = sessionFile(convId)
        if (!file.exists()) return@synchronized ""
        var firstUser: String? = null
        val recent = java.util.ArrayDeque<String>()
        var recentChars = 0
        var role = ""
        var message = StringBuilder()
        fun retainUserMessage(value: String) {
            if (value.isBlank()) return
            if (firstUser == null) {
                firstUser = value
                return
            }
            val firstCost = minOf(firstUser!!.length, maxChars / 2)
            val allowance = (maxChars - firstCost).coerceAtLeast(0)
            if (allowance <= 0) return
            val retained = if (value.length <= allowance) value else {
                val side = maxOf(1, allowance / 2)
                value.take(side) + " […] " + value.takeLast(side)
            }
            recent.addLast(retained)
            recentChars += retained.length
            while (recent.isNotEmpty() && recentChars > allowance) {
                recentChars -= recent.removeFirst().length
            }
        }
        file.bufferedReader(Charsets.UTF_8).use { reader ->
            while (true) {
                val line = reader.readLine() ?: break
                try {
                    val row = JSONObject(line)
                    if (row.optBoolean("start")) {
                        role = row.optString("role")
                        message = StringBuilder()
                    }
                    if (role == "u") message.append(row.optString("text"))
                    if (row.optBoolean("end")) {
                        if (role == "u") retainUserMessage(message.toString())
                        role = ""
                        message = StringBuilder()
                    }
                } catch (_: Throwable) { /* skip a damaged chunk */ }
            }
        }
        val initial = firstUser ?: return@synchronized recent.joinToString("\n")
        val firstBudget = maxOf(1, maxChars / 2)
        val keptInitial = if (initial.length <= firstBudget) initial else {
            val side = maxOf(1, firstBudget / 2)
            initial.take(side) + "\n[… وسط الطلب الأول مختصر لحفظ مساحة السياق …]\n" + initial.takeLast(side)
        }
        val out = StringBuilder("[أول طلب للمستخدم في هذه المحادثة — احتفظ بقيوده الأصلية]\n")
            .append(keptInitial)
        for (item in recent) out.append("\n[طلب سابق أحدث]\n").append(item)
        out.toString()
    }

    private fun sessionFile(convId: String): File {
        val key = java.security.MessageDigest.getInstance("SHA-256")
            .digest(convId.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
        return File(sessionsDir, "$key.jsonl")
    }

    /** Plain-text compatibility export for the existing developer bundle. */
    fun exportPlainText(): ByteArray = synchronized(lock) {
        val out = ByteArrayOutputStream()
        if (data.exists()) RandomAccessFile(data, "r").use { f ->
            while (true) {
                val line = f.readLine() ?: break
                try {
                    val raw = String(line.toByteArray(Charsets.ISO_8859_1), Charsets.UTF_8)
                    val value = JSONObject(raw).optString("text")
                    out.write(value.toByteArray(Charsets.UTF_8))
                    out.write(10)
                } catch (_: Throwable) { }
            }
        }
        out.toByteArray()
    }
}
