package ai.nuwaa

import android.content.Context
import java.security.MessageDigest

/** A PIN-gated panel so growing the model (heavy, irreversible-until-regrown, uses a lot of RAM) isn't one accidental tap away. The PIN is set
 *  BY THE USER the first time (never a shipped default, never stored in plain text — only its SHA-256 hash). This is a speed-bump against
 *  accidental taps and curious children, not real security: anyone with the phone unlocked can reset it the same way the user set it. */
object SecretGrowth {
    private const val PREFS = "nuwaa_secret"
    private const val KEY_HASH = "pin_hash"

    private fun sha256(s: String): String = MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }

    fun isSet(ctx: Context): Boolean = !ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_HASH, null).isNullOrBlank()
    fun setPin(ctx: Context, pin: String) { ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_HASH, sha256(pin)).apply() }
    fun verify(ctx: Context, pin: String): Boolean = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_HASH, null) == sha256(pin)
    fun clear(ctx: Context) { ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply() }

    /** The largest (emb, hid) this PHONE can safely hold right now, based on the heap it actually got (Runtime.maxMemory — adaptive per device,
     *  exactly as large as largeHeap + this device + this moment allow, never a fixed guess). Budget: building needs old+new resident at once,
     *  and a grown model that will later be TRAINED needs ~3x its own size (weights + Adam m + Adam v), so this is deliberately conservative. */
    fun maxSafeParams(ctx: Context): Long {
        val heap = Runtime.getRuntime().maxMemory()
        val used = Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()
        val budget = ((heap - used) * 0.5).coerceAtLeast(0.0)
        return (budget / (4.0 * 3.0)).toLong()                         // 4 bytes/float, x3 for weights+Adam m+Adam v
    }

    /** Picks hidden size for a target parameter count at emb=96 (a modest embedding bump that still fits comfortably on phones), mirroring
     *  tools/scale_up.py's formula so "how big a file this makes" matches what the desktop tools report. */
    fun pickHidden(targetParams: Long, emb: Int, vocab: Int): Int {
        var h = 64
        fun count(e: Int, hh: Int): Long = vocab.toLong() * e + (e.toLong() * 3 * hh + hh.toLong() * 3 * hh + 3L * hh) * 1 +
            (hh.toLong() * 3 * hh + hh.toLong() * 3 * hh + 3L * hh) + hh.toLong() * vocab + vocab
        while (count(emb, h + 16) <= targetParams) h += 16
        return h
    }
}
