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
            var line = StringBuilder()
            while (pointer >= 0 && rows.size < limit) {
                f.seek(pointer)
                val ch = f.read().toChar()
                if (ch == '\n') {
                    if (line.isNotEmpty()) {
                        try { rows.add(JSONObject(line.reverse().toString()).optString("text")) } catch (_: Throwable) { }
                        line = StringBuilder()
                    }
                } else line.append(ch)
                pointer--
            }
            if (line.isNotEmpty() && rows.size < limit) {
                try { rows.add(JSONObject(line.reverse().toString()).optString("text")) } catch (_: Throwable) { }
            }
        }
        rows.reverse()
        rows
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
