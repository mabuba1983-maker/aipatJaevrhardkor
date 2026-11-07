package ai.nuwaa

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.PowerManager

enum class Level { FAST, NORMAL, THINK }

/** What one reply will cost: how long it may be, how many separate attempts the model makes, and why. */
class Plan(val level: Level, val maxChars: Int, val temp: Float, val tries: Int, val note: String)

/** Adaptive effort. An easy message is answered at once and briefly; a hard one gets a longer reply and, in thinking mode, several attempts of which
 *  the most confident is kept. The phone's own state caps it: battery saver, low battery, heat, and memory all push it toward the cheap modes,
 *  so the model never keeps the phone busy when the phone is struggling. */
object Effort {
    /** Measured speed of THIS phone with THIS model (milliseconds per generated character); 0 = not measured yet. Brain updates it after every reply, so a
     *  bigger model (10M..100M weights) or a slower phone automatically gets shorter replies / fewer attempts instead of making the phone wait for minutes. */
    @Volatile var msPerChar = 0.0
    private val hardWords = listOf("اشرح", "شرح", "لماذا", "ليش", "قارن", "الفرق", "اكتب دالة", "اكتب لي", "اكتب كود", "برنامج", "خوارزمية", "حلل", "سبب", "صحح", "اصلح", "مثال", "كيف")
    private val codeWords = listOf("كود", "دال", "برنام", "مشروع", "سكربت", "خوارزم", "راجع", "صحح", "اصلح", "ملف")
    private val ramSoftLimit = 1_200_000_000L          // the app should stay under about 1.2 GB; real use is far below (model + a file in memory)

    /** 0 easy, 1 normal, 2 hard. kbScore = how close the message is to a verified example (known things are easy). */
    fun difficulty(q: String, kbScore: Double): Int {
        val words = q.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        var score = 0
        if (kbScore >= Kb.HIGH) score -= 2
        if (words.size >= 14) score += 2 else if (words.size >= 7) score += 1
        if (words.size <= 3) score -= 1
        if (q.contains("\n") || q.contains("```") || q.contains("def ") || q.contains("{") || q.contains("(")) score += 2
        val nq = Nlp.norm(q)
        if (hardWords.any { nq.contains(Nlp.norm(it)) }) score += 1
        if (q.count { it == '؟' || it == '?' } >= 2 || q.contains(" ثم ")) score += 1
        if (codeWords.any { nq.contains(it) }) score += 3            // programming asks always get the thinking mode: the answer matters more than the speed
        return if (score <= 0) 0 else if (score <= 2) 1 else 2
    }

    /** The highest level the device allows right now (0 FAST .. 2 THINK) and the reason when it is lower than 2. */
    fun deviceCap(ctx: Context): Pair<Int, String> {
        var cap = 2; var why = ""
        fun lower(to: Int, reason: String) { if (to < cap) { cap = to; why = reason } }
        try {
            val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
            if (pm.isPowerSaveMode) lower(1, "وضع توفير الطاقة في الجوال مفعّل")
            if (Build.VERSION.SDK_INT >= 29) {
                val th = pm.currentThermalStatus
                if (th >= 3) lower(0, "الجوال ساخن جدا") else if (th >= 2) lower(1, "الجوال ساخن")
            }
        } catch (e: Throwable) { /* no power info: no cap from it */ }
        try {
            val bi = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            if (bi != null) {
                val level = bi.getIntExtra(BatteryManager.EXTRA_LEVEL, -1); val scale = bi.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
                val plugged = bi.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) != 0
                if (level >= 0 && !plugged) {
                    val pct = level * 100 / maxOf(1, scale)
                    if (pct <= 15) lower(0, "البطارية $pct%") else if (pct <= 30) lower(1, "البطارية $pct%")
                }
            }
        } catch (e: Throwable) { /* no battery info */ }
        try {
            val rt = Runtime.getRuntime()
            val used = rt.totalMemory() - rt.freeMemory()
            val limit = minOf(rt.maxMemory(), ramSoftLimit)
            if (used > limit * 0.85) lower(0, "الذاكرة ممتلئة") else if (used > limit * 0.65) lower(1, "الذاكرة مشغولة")
        } catch (e: Throwable) { }
        return Pair(cap, why)
    }

    fun plan(ctx: Context, q: String, kbScore: Double): Plan {
        val want = difficulty(q, kbScore)
        val dev = deviceCap(ctx)
        val lvl = minOf(want, dev.first)
        val capped = lvl < want
        val note = if (capped) "وضع التوفير (" + dev.second + ")" else ""
        val per = msPerChar
        fun chars(base: Int, budgetMs: Double): Int = if (per <= 0.0) base else minOf(base, maxOf(60, (budgetMs / per).toInt()))
        return when (lvl) {
            0 -> Plan(Level.FAST, chars(180, 8000.0), 0.55f, 1, note)
            1 -> Plan(Level.NORMAL, chars(450, 25000.0), 0.7f, 1, note)
            else -> {
                // Long writing/code requests get more room; measured device speed still caps the work.
                val longOutput = q.length >= 500 || Regex("طويل|بالتفصيل|كامل|جدول|مشروع|عدة ملفات|صفحات").containsMatchIn(Nlp.norm(q))
                val c = chars(if (longOutput) 1800 else 900, if (longOutput) 90000.0 else 45000.0)
                val tries = if (per > 0.0 && per * c * 4 > 180000.0) 2 else 4
                Plan(Level.THINK, c, 0.7f, tries, note)
            }
        }
    }
}
