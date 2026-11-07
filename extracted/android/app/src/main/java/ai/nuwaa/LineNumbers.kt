package ai.nuwaa

/** Removes line numbers copied together with code (mirror of nuwaa/skills/linenums.py). Shared cases: data/linenums_cases.json.
 *  Strips only when the text really looks numbered; otherwise returns it untouched with count 0. */
object LineNumbers {
    private val blank = Regex("[ \\t]*([0-9\u0660-\u0669]{1,6})[ \\t\\r]*")
    private val pre = Regex("^[ \\t]*([0-9\u0660-\u0669]{1,6})(?:(\\t)|[ \\t]*([:|.)\\]])[ ]?|( ))")
    private const val NOT_CODE = "+*/=%<>,)"

    private class Row(val kind: Char, val num: Int, val end: Int, val style: String)

    private fun toInt(s: String): Int {
        var v = 0
        for (c in s) v = v * 10 + (if (c in '\u0660'..'\u0669') c - '\u0660' else c - '0')
        return v
    }

    fun strip(text: String): Pair<String, Int> {
        val lines = text.split("\n")
        val rows = ArrayList<Row?>()
        var nonempty = 0
        var code = 0
        for (ln in lines) {
            if (ln.isBlank()) { rows.add(null); continue }
            nonempty++
            val b = blank.matchEntire(ln)
            if (b != null) { rows.add(Row('b', toInt(b.groupValues[1]), 0, "")); continue }
            val m = pre.find(ln)
            if (m != null) {
                val end = m.range.last + 1
                val rest = ln.substring(end).trimStart()
                val style = if (m.groups[2] != null) "tab" else if (m.groups[3] != null) "punct" else "space"
                val c = if (rest.isEmpty()) ' ' else rest[0]
                val bad = (rest.isNotEmpty() && NOT_CODE.indexOf(c) >= 0) || (rest.isNotEmpty() && c == '-' && style == "space")
                if (rest.isNotEmpty() && !bad) { rows.add(Row('p', toInt(m.groupValues[1]), end, style)); code++; continue }
            }
            rows.add(Row('x', 0, 0, ""))
        }
        val nums = ArrayList<Int>()
        for (r in rows) if (r != null && (r.kind == 'b' || r.kind == 'p')) nums.add(r.num)
        if (code < 2 || nums.size < 0.8 * nonempty) return Pair(text, 0)
        for (i in 1 until nums.size) if (nums[i] <= nums[i - 1]) return Pair(text, 0)
        val steps = nums.size - 1
        if (steps > 0) {
            var seq = 0
            for (i in 1 until nums.size) if (nums[i] == nums[i - 1] + 1) seq++
            if (seq < 0.5 * steps) return Pair(text, 0)
        }
        val out = ArrayList<String>()
        var changed = 0
        for ((i, ln) in lines.withIndex()) {
            val r = rows[i]
            if (r == null || r.kind == 'x') out.add(ln)
            else if (r.kind == 'b') { out.add(""); changed++ }
            else { out.add(ln.substring(r.end)); changed++ }
        }
        var spaceOnly = true
        for (r in rows) if (r != null && r.kind == 'p' && r.style != "space") spaceOnly = false
        if (spaceOnly) {
            var k = Int.MAX_VALUE
            for ((i, o) in out.withIndex()) {
                val r = rows[i]
                if (r != null && r.kind == 'p' && o.isNotBlank()) k = minOf(k, o.length - o.trimStart(' ').length)
            }
            if (k != Int.MAX_VALUE && k > 0) {
                for (i in out.indices) {
                    val r = rows[i]
                    if (r != null && r.kind == 'p' && out[i].isNotBlank()) out[i] = out[i].substring(k)
                }
            }
        }
        return Pair(out.joinToString("\n"), changed)
    }
}
