package ai.nuwaa

import org.json.JSONObject
import java.io.File
import java.io.ByteArrayOutputStream
import java.io.RandomAccessFile

/**
 * Append-only disk storage. Complete history stays on disk; only bounded tails are read into RAM.
 * There is no arbitrary record-count cap. Real limits are available device storage and filesystem limits.
 */
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
        data.appendText(row + "\n", Charsets.UTF_8)
        meta.writeText(JSONObject().put("count", next).put("updated", System.currentTimeMillis()).toString(), Charsets.UTF_8)
    }

    fun count(): Long = synchronized(lock) {
        try {
            if (meta.exists()) JSONObject(meta.readText(Charsets.UTF_8)).optLong("count", 0L)
            else if (data.exists()) RandomAccessFile(data, "r").use { f ->
                var n = 0L
                while (f.readLine() != null) n++
                n
            } else 0L
        } catch (_: Throwable) { 0L }
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


    /** Persist one turn of a conversation separately from model weights and global learning records. */
    fun appendSessionMessage(convId: String, role: String, text: String) = synchronized(lock) {
        if (text.isEmpty()) return@synchronized
        if (role != "u" && role != "a") throw IllegalArgumentException("Unknown session role")
        if (!sessionsDir.exists() && !sessionsDir.mkdirs()) throw IllegalStateException("تعذر إنشاء مجلد جلسات الذاكرة")
        val file = sessionFile(convId)
        val row = JSONObject().put("role", role).put("text", text).toString()
        file.appendText(row + "\n", Charsets.UTF_8)
    }

    /** Replay a whole conversation sequentially from disk; only one JSONL record is held at a time. */
    fun forEachSessionMessage(convId: String, action: (String, String) -> Unit): Boolean = synchronized(lock) {
        val file = sessionFile(convId)
        if (!file.exists() || file.length() == 0L) return@synchronized false
        file.bufferedReader(Charsets.UTF_8).use { reader ->
            while (true) {
                val line = reader.readLine() ?: break
                try {
                    val row = JSONObject(line)
                    action(row.optString("role"), row.optString("text"))
                } catch (_: Throwable) { /* skip a damaged row and continue */ }
            }
        }
        true
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
