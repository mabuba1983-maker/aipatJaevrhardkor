package ai.nuwaa

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class Msg(val role: String, val text: String)   // role: "u" = user, "b" = Nuwaa

class Conv(val id: String, var title: String, var updated: Long, val msgs: ArrayList<Msg>)

/** One JSON file per conversation in filesDir/chats. Nothing leaves the phone. */
class ChatStore(private val dir: File) {
    init { dir.mkdirs() }

    fun create(): Conv {
        val id = System.currentTimeMillis().toString() + "_" + (0..9999).random()
        return Conv(id, "محادثة جديدة", System.currentTimeMillis(), ArrayList())
    }

    fun save(c: Conv) {
        val arr = JSONArray()
        for (m in c.msgs) arr.put(JSONObject().put("r", m.role).put("t", m.text))
        val o = JSONObject().put("id", c.id).put("title", c.title).put("updated", c.updated).put("msgs", arr)
        val tmp = File(dir, c.id + ".tmp")
        tmp.writeText(o.toString(), Charsets.UTF_8)
        val dst = File(dir, c.id + ".json")
        if (!tmp.renameTo(dst)) { dst.writeText(o.toString(), Charsets.UTF_8); tmp.delete() }
    }

    fun load(f: File): Conv? {
        return try {
            val o = JSONObject(f.readText(Charsets.UTF_8))
            val msgs = ArrayList<Msg>()
            val a = o.getJSONArray("msgs")
            for (i in 0 until a.length()) { val m = a.getJSONObject(i); msgs.add(Msg(m.getString("r"), m.getString("t"))) }
            Conv(o.getString("id"), o.optString("title", "محادثة"), o.optLong("updated", 0L), msgs)
        } catch (e: Exception) { null }
    }

    fun list(): List<Conv> {
        val out = ArrayList<Conv>()
        val files = dir.listFiles() ?: return out
        for (f in files) if (f.name.endsWith(".json")) { val c = load(f); if (c != null) out.add(c) }
        return out.sortedByDescending { c -> c.updated }
    }

    fun delete(id: String) { File(dir, "$id.json").delete() }

    fun deleteAll() { dir.listFiles()?.forEach { f -> f.delete() } }
}
