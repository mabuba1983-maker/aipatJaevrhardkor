package ai.nuwaa

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.ln

class KbItem(val id: String, val qs: List<String>, val a: String, val v: Int) {
    var phr: List<Set<String>> = emptyList()
    var lang: Set<String> = emptySet()
}

class Hit(val score: Double, val item: KbItem)

/** Arabic text normalisation. Mirror of nuwaa/memory/kb.py (same rules, same data file syn.json). */
object Nlp {
    private val tash = Regex("[\u064b-\u0652\u0670\u0640]")
    private val tok = Regex("[a-z0-9_#+]+|[\u0600-\u06ff]+")
    private val apunct = Regex("[\u060c\u061b\u061f\u066a-\u066d\u06d4]")   // Arabic ، ؛ ؟ sit inside the letter range: without this "المفتاح؟" became one token
    private val prefixes = listOf("وال", "بال", "كال", "فال", "لل", "ال")
    private var phrases: Map<String, String> = emptyMap()
    private var words: Map<String, String> = emptyMap()
    private var stop: Set<String> = emptySet()
    var langs: Set<String> = emptySet()
        private set

    fun norm(s: String): String {
        val sb = StringBuilder()
        for (c0 in apunct.replace(tash.replace(s.lowercase(java.util.Locale.ROOT), ""), " ")) {
            val c: Char = when (c0) {
                'أ', 'إ', 'آ', 'ٱ' -> 'ا'
                'ى' -> 'ي'
                'ة' -> 'ه'
                'ؤ' -> 'و'
                'ئ' -> 'ي'
                in '٠'..'٩' -> '0' + (c0 - '٠')
                else -> c0
            }
            sb.append(c)
        }
        return sb.toString()
    }

    private fun key(x: String): String = norm(x).trim()

    fun load(json: String) {
        val o = JSONObject(json)
        val ph = LinkedHashMap<String, String>()
        val p = o.getJSONObject("phrases")
        val pk = p.keys()
        while (pk.hasNext()) { val k = pk.next(); ph[key(k)] = key(p.getString(k)) }
        val wd = HashMap<String, String>()
        val w = o.getJSONObject("words")
        val wk = w.keys()
        while (wk.hasNext()) { val k = wk.next(); wd[key(k)] = key(w.getString(k)) }
        val st = HashSet<String>()
        val sa: JSONArray = o.getJSONArray("stop")
        for (i in 0 until sa.length()) st.add(key(sa.getString(i)))
        val lg = HashSet<String>()
        val la: JSONArray = o.getJSONArray("langs")
        for (i in 0 until la.length()) lg.add(key(la.getString(i)))
        phrases = ph; words = wd; stop = st; langs = lg
    }

    private fun stem(w: String): String {
        for (p in prefixes) if (w.startsWith(p) && w.length - p.length >= 3) return w.substring(p.length)
        return w
    }

    private fun stripA(w: String): String =
        if (w.length >= 4 && w[0] == 'ا' && w[1] != 'ل') w.substring(1) else w

    /** Mirror of kb.py MEANING/is_meaning: the word dictionary is consulted only for questions about a word's meaning, synonym or antonym. */
    private val meaning = setOf("معني", "تعني", "يعني", "مرادف", "مرادفات", "ضد", "عكس", "اضداد", "متضاد")
    fun isMeaning(q: String): Boolean = tok.findAll(norm(q)).any { m -> m.value in meaning }

    fun tokens(s: String): Set<String> {
        var t = norm(s)
        for ((a, b) in phrases) t = t.replace(a, " $b ")
        val out = LinkedHashSet<String>()
        for (m in tok.findAll(t)) {
            var w = stem(m.value)
            if (w.length > 3 && "بولف".indexOf(w[0]) >= 0 && !words.containsKey(w) && words.containsKey(w.substring(1))) w = w.substring(1)
            w = words[w] ?: w
            w = stripA(w)
            w = words[w] ?: w
            if (w.isNotEmpty() && !stop.contains(w)) out.add(w)
        }
        return out
    }
}

/** Knowledge base: IDF-weighted harmonic-mean match between the question and each stored phrasing. */
class Kb {
    companion object {
        const val HIGH = 0.50   // answer directly
        const val LOW = 0.30    // below HIGH but above LOW: only ask "did you mean ...?"
    }

    val items = ArrayList<KbItem>()
    private var idf = HashMap<String, Double>()
    private var maxIdf = 1.0

    private fun prepare(it: KbItem): KbItem {
        val ph = it.qs.map { q -> Nlp.tokens(q) }
        it.phr = ph
        val all = HashSet<String>()
        for (p in ph) all.addAll(p)
        all.retainAll(Nlp.langs)
        it.lang = all
        return it
    }

    fun reindex() {
        val df = HashMap<String, Int>()
        var n = 0
        for (it in items) for (p in it.phr) { n++; for (t in p) df[t] = (df[t] ?: 0) + 1 }
        val m = HashMap<String, Double>()
        for ((t, c) in df) m[t] = ln(1.0 + n.toDouble() / (1.0 + c))
        idf = m
        maxIdf = if (n > 0) ln(1.0 + n) else 1.0
    }

    /** front = true puts user-taught items first so they win ties. */
    fun add(id: String, qs: List<String>, a: String, v: Int, front: Boolean = false, reindex: Boolean = true) {
        val it = prepare(KbItem(id, qs, a, v))
        if (front) items.add(0, it) else items.add(it)
        if (reindex) reindex()
    }

    fun loadJsonl(text: String) {
        for (line in text.lineSequence()) {
            if (line.isBlank()) continue
            try {
                val o = JSONObject(line)
                if (o.has("q")) {
                    val qa = o.getJSONArray("q")
                    val qs = ArrayList<String>()
                    for (i in 0 until qa.length()) qs.add(qa.getString(i))
                    add(o.optString("id", ""), qs, o.getString("a"), o.optInt("v", -1), false, false)
                } else if (o.has("user")) {
                    add("", listOf(o.getString("user")), o.getString("bot"), -1, false, false)
                }
            } catch (e: Exception) { /* skip a broken line, keep the rest */ }
        }
        reindex()
    }

    private fun w(ts: Collection<String>): Double {
        var s = 0.0
        for (t in ts) s += (idf[t] ?: maxIdf)    // words the KB has never seen count against the match
        return s
    }

    fun search(q: String, k: Int): List<Hit> {
        val qt = Nlp.tokens(q)
        if (qt.isEmpty()) return emptyList()
        val wq = w(qt)
        val ql = HashSet<String>(qt)
        ql.retainAll(Nlp.langs)
        val res = ArrayList<Hit>()
        for (it in items) {
            var best = 0.0
            for (p in it.phr) {
                if (p.isEmpty()) continue
                val inter = HashSet<String>(qt)
                inter.retainAll(p)
                if (inter.isEmpty()) continue
                val wi = w(inter)
                val pq = wi / wq
                val pp = wi / w(p)
                val s = 2.0 * pq * pp / (pq + pp)
                if (s > best) best = s
            }
            if (best > 0 && ql.isNotEmpty() && it.lang.isNotEmpty() && ql.intersect(it.lang).isEmpty()) best *= 0.5
            if (best > 0) res.add(Hit(best, it))
        }
        return res.sortedByDescending { h -> h.score }.take(k)
    }
}
