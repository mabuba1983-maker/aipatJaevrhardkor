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
            val limit = rt.maxMemory()
            if (used > limit * 0.85) lower(0, "الذاكرة ممتلئة") else if (used > limit * 0.65) lower(1, "الذاكرة مشغولة")
        } catch (e: Throwable) { }
        return Pair(cap, why)
    }

    /** Live budget for the long-memory RAM working set. It shrinks as heap pressure rises and
     *  never claims storage is unlimited; older memory is already persisted in NuwaaStorage. */
    fun memoryWorkingSetBytes(): Long {
        val rt = Runtime.getRuntime()
        val used = rt.totalMemory() - rt.freeMemory()
        val available = (rt.maxMemory() - used).coerceAtLeast(0L)
        val heapShare = (rt.maxMemory() * 0.08).toLong()
        val pressureShare = (available * 0.15).toLong()
        return minOf(heapShare, pressureShare).coerceAtLeast(0L)
    }

    /** A small, live-heap-derived budget for preparing later training samples; this does not start training. */
    fun trainingSampleBudgetBytes(): Long {
        val rt = Runtime.getRuntime()
        val available = (rt.maxMemory() - (rt.totalMemory() - rt.freeMemory())).coerceAtLeast(0L)
        return minOf(available / 40L, rt.maxMemory() / 50L).coerceAtLeast(0L)
    }

    /**
     * Derive the safety ceiling from the heap this process actually has available now.
     * There is no fixed character/line ceiling; this estimate changes with heap pressure
     * and with the number of draft attempts retained in memory.
     */
    fun outputCharBudget(tries: Int = 1): Int {
        val rt = Runtime.getRuntime()
        val used = rt.totalMemory() - rt.freeMemory()
        val available = (rt.maxMemory() - used).coerceAtLeast(0L)
        // Keep 35% of currently available heap free for the model, Android and UI.
        // Account for StringBuilder, probability trace, sampler arrays and retained drafts.
        val usable = (available * 0.65).toLong()
        val estimatedBytesPerCharPerDraft = 24L
        val safe = usable / (estimatedBytesPerCharPerDraft * maxOf(1, tries))
        return safe.coerceIn(1L, Int.MAX_VALUE.toLong()).toInt()
    }

    fun plan(ctx: Context, q: String, kbScore: Double): Plan {
        val want = difficulty(q, kbScore)
        val dev = deviceCap(ctx)
        val lvl = minOf(want, dev.first)
        val capped = lvl < want
        val note = if (capped) "وضع التوفير (" + dev.second + ")" else ""
        val longOutput = q.length >= 500 || Regex("طويل|بالتفصيل|كامل|جدول|مشروع|عدة ملفات|صفحات|اسطر|سطور").containsMatchIn(Nlp.norm(q))
        return when (lvl) {
            0 -> Plan(Level.FAST, outputCharBudget(1), 0.55f, 1, note)
            1 -> Plan(Level.NORMAL, outputCharBudget(1), 0.7f, 1, note)
            else -> {
                val tries = if (longOutput) 2 else 4
                Plan(Level.THINK, outputCharBudget(tries), 0.7f, tries, note)
            }
        }
    }
}
