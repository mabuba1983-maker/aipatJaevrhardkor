package ai.nuwaa

/** Exact arithmetic (mirror of nuwaa/skills/calc.py). Returns null if the text is not purely a calculation. */
object Skills {
    private val filler = listOf("كم يساوي", "كم ناتج", "كم حاصل", "احسب لي", "احسب", "ناتج", "ما هو", "ما هي", "؟", "?", "=", "يساوي")
    private val words = listOf("مقسوم على" to "/", "زائد" to "+", "ناقص" to "-", "ضرب" to "*", "تقسيم" to "/", "×" to "*", "÷" to "/", "^" to "**")

    private fun digits(s: String): String {
        val sb = StringBuilder()
        for (c in s) sb.append(if (c in '٠'..'٩') ('0' + (c - '٠')) else if (c == '٫') '.' else c)
        return sb.toString()
    }

    private class P(val t: String) {
        var i = 0
        fun eat(c: String): Boolean { if (t.startsWith(c, i)) { i += c.length; return true }; return false }
        fun expr(): Double { var v = term(); while (true) { if (eat("+")) v += term() else if (eat("-")) v -= term() else return v } }
        fun term(): Double {
            var v = pw()
            while (true) {
                if (t.startsWith("**", i)) throw IllegalArgumentException()
                if (eat("*")) v *= pw()
                else if (eat("/")) { val d = pw(); if (d == 0.0) throw ArithmeticException(); v /= d }
                else if (eat("%")) v %= pw()
                else return v
            }
        }
        fun pw(): Double {
            val b = unary()
            if (eat("**")) { val e = pw(); if (Math.abs(e) > 100 || Math.abs(b) > 1e6) throw ArithmeticException("big"); return Math.pow(b, e) }
            return b
        }
        fun unary(): Double {
            if (eat("-")) return -unary()
            if (eat("+")) return unary()
            if (eat("(")) { val v = expr(); if (!eat(")")) throw IllegalArgumentException(); return v }
            val m = Regex("\\d+(\\.\\d+)?").find(t, i)
            if (m == null || m.range.first != i) throw IllegalArgumentException()
            i = m.range.last + 1; return m.value.toDouble()
        }
    }

    private fun fmt(v: Double): String = if (v == Math.floor(v) && Math.abs(v) < 1e15) v.toLong().toString() else String.format(java.util.Locale.US, "%.6g", v).trimEnd('0').trimEnd('.')

    fun tryMath(text: String): String? {
        var t = digits(text)
        for (f in filler) t = t.replace(f, " ")
        for ((w, o) in words) t = t.replace(w, " $o ")
        t = t.replace(Regex("\\s+"), "")
        if (t.isEmpty() || !Regex("[0-9+\\-*/().%]+").matches(t) || !Regex("\\d.*[+\\-*/%].*\\d").containsMatchIn(t)) return null
        val p = P(t)
        val v = try { val r = p.expr(); if (p.i != t.length) return null; r }
        catch (e: ArithmeticException) { return if (e.message == "big") "الرقم كبير جدا." else "لا يمكن القسمة على صفر." }
        catch (e: Exception) { return null }
        var shown = digits(text)
        for (f in filler) shown = shown.replace(f, " ")
        for ((w, o) in words.dropLast(1)) shown = shown.replace(w, " $o ")
        return shown.replace(Regex("\\s+"), " ").trim() + " = " + fmt(v)
    }
}
