package ai.nuwaa

import org.json.JSONArray
import java.io.Reader
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Memory of what follows each context (orders 1..8), learned instantly. Mirror of NGram in nuwaa/lm/gru.py.
 *  Used twice: the long-term memory (kept on the phone) and a short-term memory that lives inside one NlmSession. */
class NMem {
    private val t = HashMap<String, HashMap<Char, Int>>()
    private val activeTexts = java.util.ArrayDeque<String>()
    private var budgetProvider: (() -> Long)? = null
    private var estimatedBytes = 0L
    var chars = 0
        private set
    var archivedFromRam = 0L
        private set

    /** The caller supplies a live heap-based budget. No fixed memory-item count is imposed. */
    fun setBudgetProvider(provider: () -> Long) {
        budgetProvider = provider
        enforceBudget()
    }

    private fun addToIndex(text: String) {
        val s = "\n" + text + "\n"
        for (i in 1 until s.length) {
            for (o in 1..8) {
                if (i - o < 0) break
                val key = s.substring(i - o, i)
                var m = t[key]
                if (m == null) {
                    m = HashMap()
                    t[key] = m
                    estimatedBytes += 112L + key.length * 2L
                }
                if (!m.containsKey(s[i])) estimatedBytes += 64L
                m[s[i]] = (m[s[i]] ?: 0) + 1
            }
        }
        chars += s.length
    }

    /** Remove one archived record's exact n-gram contribution without rebuilding the whole working set. */
    private fun removeFromIndex(text: String) {
        val s = "\n" + text + "\n"
        for (i in 1 until s.length) {
            for (o in 1..8) {
                if (i - o < 0) break
                val key = s.substring(i - o, i)
                val counts = t[key] ?: continue
                val count = counts[s[i]] ?: continue
                if (count <= 1) {
                    counts.remove(s[i])
                    estimatedBytes -= 64L
                } else {
                    counts[s[i]] = count - 1
                }
                if (counts.isEmpty()) {
                    t.remove(key)
                    estimatedBytes -= 112L + key.length * 2L
                }
            }
        }
        chars = (chars - s.length).coerceAtLeast(0)
        estimatedBytes = (estimatedBytes - 48L - text.length * 2L).coerceAtLeast(0L)
    }

    /** Add only to the RAM working set. The caller must archive the original text before calling this. */
    @Synchronized fun add(text: String) = addInternal(text, newestFirst = false)

    /** During archive restore, records arrive newest-first; addFirst preserves chronological FIFO order. */
    @Synchronized fun addNewestFirst(text: String) = addInternal(text, newestFirst = true)

    private fun addInternal(text: String, newestFirst: Boolean) {
        if (text.isEmpty()) return
        if (newestFirst) activeTexts.addFirst(text) else activeTexts.addLast(text)
        addToIndex(text)
        estimatedBytes += 48L + text.length * 2L
        enforceBudget()
    }

    /** Evict oldest RAM records until the current device-derived budget is met. Evicted text remains in persistent storage. */
    @Synchronized fun enforceBudget() {
        val budget = try { budgetProvider?.invoke() ?: Long.MAX_VALUE } catch (_: Throwable) { 0L }
        while (activeTexts.isNotEmpty() && estimatedBytes > budget) {
            val oldest = activeTexts.removeFirst()
            removeFromIndex(oldest)
            archivedFromRam++
        }
    }

    @Synchronized fun activeRecordCount(): Int = activeTexts.size
    @Synchronized fun estimatedMemoryBytes(): Long = estimatedBytes

    /** Longest context that was seen: (order, counts) or null. */
    @Synchronized fun dist(ctx: String, minO: Int = 1): Pair<Int, HashMap<Char, Int>>? {
        // Re-evaluate heap pressure during generation too, not only when new text arrives.
        enforceBudget()
        var o = minOf(8, ctx.length)
        while (o >= minO) {
            val c = t[ctx.substring(ctx.length - o)]
            if (c != null) return Pair(o, HashMap(c))
            o--
        }
        return null
    }
}

/** Full optimizer checkpoint used to roll back rejected training without leaving stale Adam momentum. */
class NlmTrainingSnapshot(
    val weights: List<FloatArray>,
    val firstMoment: List<FloatArray>,
    val secondMoment: List<FloatArray>,
    val step: Int
)

/** The Nuwaa language model, written from scratch, running and LEARNING on the phone. Mirror of nuwaa/lm/gru.py (file format NLM2).
 *  Neural part: embedding -> GRU layer 1 -> GRU layer 2 -> softmax over characters. The hidden state is carried from character to character,
 *  so there is NO fixed window (the old 24-character limit is gone). Hand-written backprop through time + Adam.
 *  No pretrained or licensed weights, no network. HONEST LIMIT: small model, small data: it writes rough Arabic until it has seen more text. */
class Nlm private constructor(val e: Int, val h: Int, val chars: List<String>) {
    val v = chars.size
    private val vocab = HashMap<String, Int>().also { m -> chars.forEachIndexed { i, c -> m[c] = i } }
    private val h3 = 3 * h

    // E, Wx1, Wh1, b1, Wx2, Wh2, b2, Wo, bo (row-major, same order as the file)
    val P: List<FloatArray> = listOf(
        FloatArray(v * e), FloatArray(e * h3), FloatArray(h * h3), FloatArray(h3),
        FloatArray(h * h3), FloatArray(h * h3), FloatArray(h3), FloatArray(h * v), FloatArray(v)
    )
    private val mAdam = P.map { FloatArray(it.size) }
    private val vAdam = P.map { FloatArray(it.size) }
    private var tAdam = 0
    val long = NMem()

    fun cid(c: Char): Int = vocab[c.toString()] ?: 1
    fun encode(s: String): IntArray = IntArray(s.length) { cid(s[it]) }
    fun paramCount(): Int = P.sumOf { it.size }

    private fun sig(x: Float): Float = (1.0 / (1.0 + Math.exp(-x.toDouble()))).toFloat()

    // ---------------------------------------------------------------- one GRU cell for ONE sequence position
    /** gx = x@Wx + b (3h). Writes the new state into out and the values needed by backprop into r, z, n, rh. */
    private fun cellFwd(gx: FloatArray, hp: FloatArray, wh: FloatArray, out: FloatArray, r: FloatArray, z: FloatArray, n: FloatArray, rh: FloatArray) {
        val tmp = FloatArray(2 * h)
        for (j in 0 until 2 * h) tmp[j] = gx[j]
        for (q in 0 until h) {
            val hv = hp[q]
            if (hv == 0f) continue
            val o = q * h3
            for (j in 0 until 2 * h) tmp[j] += hv * wh[o + j]
        }
        for (j in 0 until h) { r[j] = sig(tmp[j]); z[j] = sig(tmp[h + j]); rh[j] = r[j] * hp[j] }
        val an = FloatArray(h)
        for (j in 0 until h) an[j] = gx[2 * h + j]
        for (q in 0 until h) {
            val rv = rh[q]
            if (rv == 0f) continue
            val o = q * h3 + 2 * h
            for (j in 0 until h) an[j] += rv * wh[o + j]
        }
        for (j in 0 until h) {
            n[j] = Math.tanh(an[j].toDouble()).toFloat()
            out[j] = (1f - z[j]) * hp[j] + z[j] * n[j]
        }
    }

    /** Backward of one cell. dhn = gradient of the new state. Adds into dwh; writes dgx (3h) and dhp (gradient of the previous state). */
    private fun cellBwd(dhn: FloatArray, r: FloatArray, z: FloatArray, n: FloatArray, hp: FloatArray, rh: FloatArray, wh: FloatArray, dwh: FloatArray, dgx: FloatArray, dhp: FloatArray) {
        val dz = FloatArray(h); val dan = FloatArray(h)
        for (j in 0 until h) {
            dz[j] = dhn[j] * (n[j] - hp[j])
            dan[j] = dhn[j] * z[j] * (1f - n[j] * n[j])
            dhp[j] = dhn[j] * (1f - z[j])
        }
        val drh = FloatArray(h)
        for (q in 0 until h) {
            val o = q * h3 + 2 * h
            val rv = rh[q]
            var s = 0f
            for (j in 0 until h) { dwh[o + j] += rv * dan[j]; s += dan[j] * wh[o + j] }
            drh[q] = s
        }
        val dar = FloatArray(h); val daz = FloatArray(h)
        for (j in 0 until h) {
            dhp[j] += drh[j] * r[j]
            dar[j] = drh[j] * hp[j] * r[j] * (1f - r[j])
            daz[j] = dz[j] * z[j] * (1f - z[j])
        }
        for (q in 0 until h) {
            val o = q * h3
            val hv = hp[q]
            var s = 0f
            for (j in 0 until h) {
                dwh[o + j] += hv * dar[j]
                dwh[o + h + j] += hv * daz[j]
                s += dar[j] * wh[o + j] + daz[j] * wh[o + h + j]
            }
            dhp[q] += s
        }
        for (j in 0 until h) { dgx[j] = dar[j]; dgx[h + j] = daz[j]; dgx[2 * h + j] = dan[j] }
    }

    private fun gx1(id: Int, out: FloatArray) {
        for (j in 0 until h3) out[j] = P[3][j]
        for (q in 0 until e) {
            val ev = P[0][id * e + q]
            val o = q * h3
            for (j in 0 until h3) out[j] += ev * P[1][o + j]
        }
    }

    private fun gx2(h1: FloatArray, out: FloatArray) {
        for (j in 0 until h3) out[j] = P[6][j]
        for (q in 0 until h) {
            val hv = h1[q]
            if (hv == 0f) continue
            val o = q * h3
            for (j in 0 until h3) out[j] += hv * P[4][o + j]
        }
    }

    private fun softmaxOf(h2: FloatArray): FloatArray {
        val p = FloatArray(v)
        for (j in 0 until v) p[j] = P[8][j]
        for (q in 0 until h) {
            val hv = h2[q]
            if (hv == 0f) continue
            val o = q * v
            for (j in 0 until v) p[j] += hv * P[7][o + j]
        }
        var mx = -1e30f
        for (j in 0 until v) if (p[j] > mx) mx = p[j]
        var s = 0f
        for (j in 0 until v) { val x = Math.exp((p[j] - mx).toDouble()).toFloat(); p[j] = x; s += x }
        for (j in 0 until v) p[j] /= s
        return p
    }

    // ---------------------------------------------------------------- inference: one character at a time, the state is carried by the caller
    /** Reads one character. s1 and s2 are the two hidden states and are UPDATED in place. Returns the probabilities of the next character. */
    fun stepChar(id: Int, s1: FloatArray, s2: FloatArray): FloatArray {
        val g1 = FloatArray(h3); gx1(id, g1)
        val n1 = FloatArray(h); val r = FloatArray(h); val z = FloatArray(h); val nn = FloatArray(h); val rh = FloatArray(h)
        cellFwd(g1, s1, P[2], n1, r, z, nn, rh)
        val g2 = FloatArray(h3); gx2(n1, g2)
        val n2 = FloatArray(h)
        cellFwd(g2, s2, P[5], n2, r, z, nn, rh)
        System.arraycopy(n1, 0, s1, 0, h); System.arraycopy(n2, 0, s2, 0, h)
        return softmaxOf(n2)
    }

    // ---------------------------------------------------------------- training: backprop through time over one sequence (batch of 1)
    private class Trace(val t: Int, h: Int) {
        val h1 = Array(t) { FloatArray(h) }; val h2 = Array(t) { FloatArray(h) }
        val r1 = Array(t) { FloatArray(h) }; val z1 = Array(t) { FloatArray(h) }; val n1 = Array(t) { FloatArray(h) }; val rh1 = Array(t) { FloatArray(h) }
        val r2 = Array(t) { FloatArray(h) }; val z2 = Array(t) { FloatArray(h) }; val n2 = Array(t) { FloatArray(h) }; val rh2 = Array(t) { FloatArray(h) }
        val p = arrayOfNulls<FloatArray>(t)
    }

    /** x: inputs, y: targets (same length). s1/s2: starting states (updated to the final states). Returns (loss in nats/char, gradients), or just the loss when grads is false. */
    private fun run(x: IntArray, y: IntArray, s1: FloatArray, s2: FloatArray, grads: Boolean): Pair<Float, List<FloatArray>?> {
        val t = x.size
        val tr = Trace(t, h)
        var h1p = s1.copyOf(); var h2p = s2.copyOf()
        val g1 = FloatArray(h3); val g2 = FloatArray(h3)
        var loss = 0f
        for (i in 0 until t) {
            gx1(x[i], g1)
            cellFwd(g1, h1p, P[2], tr.h1[i], tr.r1[i], tr.z1[i], tr.n1[i], tr.rh1[i])
            gx2(tr.h1[i], g2)
            cellFwd(g2, h2p, P[5], tr.h2[i], tr.r2[i], tr.z2[i], tr.n2[i], tr.rh2[i])
            val p = softmaxOf(tr.h2[i]); tr.p[i] = p
            loss -= Math.log((p[y[i]] + 1e-9f).toDouble()).toFloat()
            h1p = tr.h1[i]; h2p = tr.h2[i]
        }
        loss /= t
        if (!grads) { System.arraycopy(h1p, 0, s1, 0, h); System.arraycopy(h2p, 0, s2, 0, h); return Pair(loss, null) }
        val g = P.map { FloatArray(it.size) }
        val dH2 = Array(t) { FloatArray(h) }
        for (i in 0 until t) {
            val d = tr.p[i]!!
            d[y[i]] -= 1f
            for (j in 0 until v) d[j] /= t.toFloat()
            for (j in 0 until v) g[8][j] += d[j]
            for (q in 0 until h) {
                val hv = tr.h2[i][q]; val o = q * v
                var s = 0f
                for (j in 0 until v) { g[7][o + j] += hv * d[j]; s += d[j] * P[7][o + j] }
                dH2[i][q] = s
            }
        }
        var dh1c = FloatArray(h); var dh2c = FloatArray(h)
        val dgx2 = FloatArray(h3); val dgx1 = FloatArray(h3)
        for (i in t - 1 downTo 0) {
            val d2 = FloatArray(h)
            for (j in 0 until h) d2[j] = dH2[i][j] + dh2c[j]
            val h2prev = if (i > 0) tr.h2[i - 1] else s2
            val nh2 = FloatArray(h)
            cellBwd(d2, tr.r2[i], tr.z2[i], tr.n2[i], h2prev, tr.rh2[i], P[5], g[5], dgx2, nh2)
            dh2c = nh2
            val d1 = FloatArray(h)
            for (q in 0 until h) {
                val o = q * h3
                var s = dh1c[q]
                val hv = tr.h1[i][q]
                for (j in 0 until h3) { s += dgx2[j] * P[4][o + j]; g[4][o + j] += hv * dgx2[j] }
                d1[q] = s
            }
            for (j in 0 until h3) g[6][j] += dgx2[j]
            val h1prev = if (i > 0) tr.h1[i - 1] else s1
            val nh1 = FloatArray(h)
            cellBwd(d1, tr.r1[i], tr.z1[i], tr.n1[i], h1prev, tr.rh1[i], P[2], g[2], dgx1, nh1)
            dh1c = nh1
            for (j in 0 until h3) g[3][j] += dgx1[j]
            val id = x[i]
            for (q in 0 until e) {
                val o = q * h3
                val ev = P[0][id * e + q]
                var s = 0f
                for (j in 0 until h3) { g[1][o + j] += ev * dgx1[j]; s += dgx1[j] * P[1][o + j] }
                g[0][id * e + q] += s
            }
        }
        System.arraycopy(h1p, 0, s1, 0, h); System.arraycopy(h2p, 0, s2, 0, h)
        return Pair(loss, g)
    }

    private fun adam(g: List<FloatArray>, lr: Float) {
        var nrm = 0.0
        for (a in g) for (x in a) nrm += (x * x).toDouble()
        val sc = if (nrm > 1.0) (1.0 / Math.sqrt(nrm)).toFloat() else 1f
        tAdam++
        val b1 = 0.9f; val b2 = 0.999f
        val c1 = 1f - Math.pow(b1.toDouble(), tAdam.toDouble()).toFloat()
        val c2 = 1f - Math.pow(b2.toDouble(), tAdam.toDouble()).toFloat()
        for (k in P.indices) {
            val w = P[k]; val m = mAdam[k]; val vv = vAdam[k]; val gk = g[k]
            for (i in w.indices) {
                val gi = gk[i] * sc
                m[i] = b1 * m[i] + (1f - b1) * gi
                vv[i] = b2 * vv[i] + (1f - b2) * gi * gi
                w[i] -= lr * (m[i] / c1) / (Math.sqrt((vv[i] / c2).toDouble()).toFloat() + 1e-8f)
            }
        }
    }

    /** Bits per character of a text, read with ONE state from start to end (this is what unbounded context means). */
    fun bpc(ids: IntArray, chunk: Int = 128): Float {
        if (ids.size < 3) return 0f
        val s1 = FloatArray(h); val s2 = FloatArray(h)
        var tot = 0.0; var n = 0
        var i = 0
        while (i < ids.size - 1) {
            val end = minOf(i + chunk, ids.size - 1)
            val x = ids.copyOfRange(i, end); val y = ids.copyOfRange(i + 1, end + 1)
            val res = run(x, y, s1, s2, false)
            tot += res.first.toDouble() * x.size; n += x.size
            i = end
        }
        return (tot / n / Math.log(2.0)).toFloat()
    }

    /** Learn from one thing the user said: long-term memory only (n-grams). The weights are NOT trained here: a few gradient steps on every raw
     *  message made the model collapse and echo the user's words (the repetition bug). Weights change only in develop(), with rehearsal and rollback. */
    fun observe(text: String) { long.add(text) }

    private fun trainOn(ids: IntArray, epochs: Int, lr: Float, chunk: Int) {
        for (ep in 0 until epochs) {
            val s1 = FloatArray(h); val s2 = FloatArray(h)
            var i = 0
            while (i < ids.size - 1) {
                val end = minOf(i + chunk, ids.size - 1)
                if (end - i >= 2) {
                    val res = run(ids.copyOfRange(i, end), ids.copyOfRange(i + 1, end + 1), s1, s2, true)
                    val g = res.second
                    if (g != null) adam(g, lr)
                }
                i = end
            }
        }
    }

    /** ONE gradient step on one window of text (fresh state at its start). Returns bits per character of that window before the step. Used by Trainer. */
    fun trainWindow(text: String, lr: Float): Float {
        val ids = encode(text)
        if (ids.size < 8) return 0f
        val res = run(ids.copyOfRange(0, ids.size - 1), ids.copyOfRange(1, ids.size), FloatArray(h), FloatArray(h), true)
        val g = res.second
        if (g != null) adam(g, lr)
        return (res.first / Math.log(2.0)).toFloat()
    }
    fun snapshot(): List<FloatArray> = P.map { it.copyOf() }
    fun restoreSnapshot(s: List<FloatArray>) { for (k in P.indices) System.arraycopy(s[k], 0, P[k], 0, P[k].size) }

    /** Capture weights AND Adam state so a rejected experiment can be rolled back exactly. */
    fun trainingSnapshot(): NlmTrainingSnapshot = NlmTrainingSnapshot(
        P.map { it.copyOf() }, mAdam.map { it.copyOf() }, vAdam.map { it.copyOf() }, tAdam
    )

    fun restoreTrainingSnapshot(s: NlmTrainingSnapshot) {
        require(s.weights.size == P.size && s.firstMoment.size == mAdam.size && s.secondMoment.size == vAdam.size) {
            "training snapshot shape mismatch"
        }
        for (k in P.indices) {
            require(s.weights[k].size == P[k].size && s.firstMoment[k].size == mAdam[k].size && s.secondMoment[k].size == vAdam[k].size) {
                "training snapshot parameter mismatch"
            }
            System.arraycopy(s.weights[k], 0, P[k], 0, P[k].size)
            System.arraycopy(s.firstMoment[k], 0, mAdam[k], 0, mAdam[k].size)
            System.arraycopy(s.secondMoment[k], 0, vAdam[k], 0, vAdam[k].size)
        }
        tAdam = s.step
    }

    /**
     * Prepare a later self-development pass from a bounded sample spanning the archive.
     * The newest portion is held out for evaluation: training is accepted only when unseen
     * held-out text improves and the original rehearsal text does not regress materially.
     * This method trains only when explicitly called by the user-facing training action.
     */
    fun develop(
        texts: List<String>,
        epochs: Int,
        lr: Float,
        rehearse: String = "",
        maxTrainingChars: Int = (Effort.trainingSampleBudgetBytes() / 2L).coerceAtMost(Int.MAX_VALUE.toLong()).toInt(),
        chunk: Int = 96
    ): Pair<Float, Float> {
        val totalBudget = maxTrainingChars.coerceAtLeast(128)
        val trainBudget = (totalBudget * 4L / 5L).toInt().coerceAtLeast(64)
        val validationBudget = (totalBudget - trainBudget).coerceAtLeast(32)
        val training = StringBuilder()
        val validation = StringBuilder()

        fun appendBounded(target: StringBuilder, value: String, budget: Int) {
            val remaining = budget - target.length
            if (remaining <= 0 || value.isEmpty()) return
            val record = "س:" + value + "\n"
            if (record.length <= remaining) target.append(record)
            else if (remaining >= 48) {
                val head = remaining / 2
                target.append(record.take(head))
                target.append(record.takeLast(remaining - head))
            } else target.append(record.take(remaining))
        }

        val splitAt = ((texts.size.toLong() * 4L) / 5L).toInt().coerceIn(0, texts.size)
        for (index in texts.indices) {
            if (index < splitAt) appendBounded(training, texts[index], trainBudget)
            else appendBounded(validation, texts[index], validationBudget)
        }
        if (training.length < 8 || validation.length < 8) return Pair(0f, 0f)

        val heard = training.toString()
        val validationIds = encode(validation.toString())
        if (validationIds.size < 8) return Pair(0f, 0f)

        val rehearsalBudget = minOf(rehearse.length, (trainBudget / 4).coerceAtLeast(0))
        val reh = if (rehearse.length <= rehearsalBudget) rehearse else {
            val side = rehearsalBudget / 2
            rehearse.take(side) + rehearse.takeLast(rehearsalBudget - side)
        }
        val rehearsalIds = if (reh.length > 8) encode(reh) else null
        val before = bpc(validationIds)
        val rehearsalBefore = if (rehearsalIds != null) bpc(rehearsalIds) else 0f
        val checkpoint = trainingSnapshot()

        trainOn(encode(heard + reh), epochs, lr, chunk)

        val after = bpc(validationIds)
        val rehearsalAfter = if (rehearsalIds != null) bpc(rehearsalIds) else 0f
        if (after > before || (rehearsalIds != null && rehearsalAfter > rehearsalBefore * 1.03f)) {
            restoreTrainingSnapshot(checkpoint)
            return Pair(before, before)
        }
        return Pair(before, after)
    }

    // ---------------------------------------------------------------- files (NLM2)
    /** magic NLM2, int32 E H V, int32 length of the chars JSON, the chars JSON (UTF-8), then float32 little-endian E Wx1 Wh1 b1 Wx2 Wh2 b2 Wo bo. */
    fun toBytes(): ByteArray {
        val ch = JSONArray(chars).toString().toByteArray(Charsets.UTF_8)
        var floats = 0
        for (a in P) floats += a.size
        val bb = ByteBuffer.allocate(4 + 12 + 4 + ch.size + 4 * floats).order(ByteOrder.LITTLE_ENDIAN)
        bb.put(byteArrayOf(0x4E.toByte(), 0x4C.toByte(), 0x4D.toByte(), 0x32.toByte()))
        bb.putInt(e); bb.putInt(h); bb.putInt(v); bb.putInt(ch.size); bb.put(ch)
        for (a in P) for (x in a) bb.putFloat(x)
        return bb.array()
    }

    companion object {
        /** Builds a BIGGER model that behaves EXACTLY like `old` before any further training: every weight that reaches a new, bigger unit is
         *  zero (so the extra room changes nothing yet), every weight that only touches old units is copied over unchanged. Exact index-for-index
         *  mirror of GRULM.widened() in nuwaa/lm/gru.py (tested there: tests/test_scale.py — identical bits/char before vs after). Needs newE >= old.e
         *  and newH >= old.h. Long-term memory (old.long) is NOT carried over: it is small compared to retraining and keeping it correct across a
         *  size change is not worth the risk of a subtle bug; it simply starts empty on the bigger model. */
        fun grow(old: Nlm, newE: Int, newH: Int): Nlm {
            require(newE >= old.e && newH >= old.h) { "grow only makes the model bigger, never smaller" }
            val n = Nlm(newE, newH, old.chars)
            val oe = old.e; val oh = old.h; val oh3 = 3 * oh; val nh3 = 3 * newH; val v = old.v
            // E: (V, e) row-major -> copy the first oe columns of every row
            for (row in 0 until v) for (col in 0 until oe) n.P[0][row * newE + col] = old.P[0][row * oe + col]
            // Wx1 (oe x 3*oh -> newE x 3*newH), Wh1/Wx2/Wh2 (oh x 3*oh -> newH x 3*newH): copied gate-block by gate-block (r | z | n)
            fun copyGated(dst: FloatArray, src: FloatArray, oldRows: Int, newCols: Int, oldCols3: Int) {
                val oldH = oldCols3 / 3
                for (row in 0 until oldRows) for (g in 0 until 3) for (col in 0 until oldH)
                    dst[row * newCols + g * (newCols / 3) + col] = src[row * oldCols3 + g * oldH + col]
            }
            copyGated(n.P[1], old.P[1], oe, nh3, oh3)       // Wx1
            copyGated(n.P[2], old.P[2], oh, nh3, oh3)       // Wh1
            copyGated(n.P[4], old.P[4], oh, nh3, oh3)       // Wx2
            copyGated(n.P[5], old.P[5], oh, nh3, oh3)       // Wh2
            for (g in 0 until 3) for (col in 0 until oh) { n.P[3][g * newH + col] = old.P[3][g * oh + col]; n.P[6][g * newH + col] = old.P[6][g * oh + col] }   // b1, b2
            for (row in 0 until oh) for (col in 0 until v) n.P[7][row * v + col] = old.P[7][row * v + col]   // Wo: (oh x V) -> (newH x V), first oh rows
            for (col in 0 until v) n.P[8][col] = old.P[8][col]                                                 // bo: unchanged size, copy fully
            return n
        }
        fun load(b: ByteArray): Nlm {
            require(b.size > 20 && b[0] == 0x4E.toByte() && b[1] == 0x4C.toByte() && b[2] == 0x4D.toByte() && b[3] == 0x32.toByte()) { "not an NLM2 file" }
            val bb = ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN)
            bb.position(4)
            val e = bb.int; val h = bb.int; val v = bb.int; val n = bb.int
            val raw = ByteArray(n); bb.get(raw)
            val arr = JSONArray(String(raw, Charsets.UTF_8))
            val chars = ArrayList<String>()
            for (i in 0 until arr.length()) chars.add(arr.getString(i))
            require(chars.size == v) { "vocabulary size mismatch" }
            val m = Nlm(e, h, chars)
            for (a in m.P) for (i in a.indices) a[i] = bb.float
            return m
        }
    }
}

/** One active conversation state. Brain archives the complete transcript and replays it in chunks if this session is evicted or recreated.
 *  The in-memory n-gram helper is deliberately limited to the latest 12 exchanges. */
class NlmSession(private val m: Nlm, seed: Long) {
    private val s1 = FloatArray(m.h); private val s2 = FloatArray(m.h)
    private var p: FloatArray = FloatArray(m.v)
    private val contextTail = StringBuilder(8)
    private var short = NMem()
    private val rng = java.util.Random(seed)
    private val replies = ArrayList<Pair<String, String>>()      // (normalised question, reply) of this conversation
    private val minOrder = 4        // a memory may speak only when it matches >= 4 characters of context: it completes words but can never hijack the START of a reply
    private val ngSelf = 10         // inside one reply no 10-character piece is written twice
    private val ngPrev = 8          // against earlier replies of this chat: no 8-character piece (unless the user asked the same thing again)

    /** Keep the n-gram helper small; the complete conversation is archived and replayed from disk. */
    private fun refreshShortMemory() {
        short = NMem()
        for ((question, answer) in replies) {
            short.add("س:$question")
            short.add("ج:$answer")
        }
    }

    init { feed("\n") }      // every pair in training follows a line end: a fresh conversation starts the same way

    fun feed(s: String) { for (ch in s) feedChar(ch) }

    /** Stream a long source in bounded chunks while preserving the GRU state. Caller closes Reader. */
    fun feed(reader: Reader, chunkChars: Int = 4096): Long {
        require(chunkChars > 0) { "chunkChars must be positive" }
        val buffer = CharArray(chunkChars)
        var total = 0L
        while (true) {
            val n = reader.read(buffer, 0, buffer.size)
            if (n < 0) break
            for (i in 0 until n) feedChar(buffer[i])
            total += n.toLong()
        }
        return total
    }

    private fun feedChar(ch: Char) {
        p = m.stepChar(m.cid(ch), s1, s2)
        contextTail.append(ch)
        if (contextTail.length > 8) contextTail.delete(0, contextTail.length - 8)
    }

    fun retainedContextChars(): Int = contextTail.length

    /** Mixes the neural distribution with the long-term and the short-term memory. Always returns a NEW array. */
    private fun mix(p0: FloatArray, gainLong: Float, gainShort: Float): FloatArray {
        var q0 = p0.copyOf()
        val ctx = contextTail.toString()
        val mems = listOf(Pair(m.long, gainLong), Pair(short, gainShort))
        for (item in mems) {
            if (item.second <= 0f) continue
            val d = item.first.dist(ctx, minOrder) ?: continue
            val o = d.first; val cnt = d.second
            var tot = 0
            for (c in cnt.values) tot += c
            val lam = item.second * tot / (tot + 0.1f) * minOf(1f, (o - minOrder + 1) / 4f)
            val q = FloatArray(m.v)
            for ((ch, k) in cnt) q[m.cid(ch)] += k.toFloat() / tot
            val r = FloatArray(m.v)
            for (j in 0 until m.v) r[j] = (1f - lam) * q0[j] + lam * q[j]
            q0 = r
        }
        return q0
    }

    private fun grams(t: String, n: Int): HashSet<String> {
        val g = HashSet<String>()
        if (t.length >= n) for (i in 0..t.length - n) g.add(t.substring(i, i + n))
        return g
    }

    /** Drops a sentence or line that repeats one already written. */
    private fun dedupe(t: String): String {
        val seen = HashSet<String>(); val sb = StringBuilder()
        var start = 0
        for (i in t.indices) {
            val c = t[i]
            if (c == '.' || c == '!' || c == '?' || c == '؟' || c == '\n' || i == t.length - 1) {
                val part = t.substring(start, i + 1); start = i + 1
                val k = part.trim()
                if (k.length >= 6 && !seen.add(k)) continue
                sb.append(part)
            }
        }
        return sb.toString().trim()
    }

    /** Writes a reply to `user`, character by character, until the model ends the line. No gate, no canned phrase: it always answers.
     *  A no-repeat sampler keeps it from repeating itself or its earlier replies. Returns the reply and the probability the model gave each character. */
    fun reply(user: String, maxChars: Int = 700, temp: Float = 0.7f, topk: Int = 8, minP: Float = 0.15f, commit: Boolean = true, memGain: Float = 0.6f, shortGain: Float = 0.6f, allowMultiline: Boolean = false): Pair<String, List<Float>> {
        val u = user.replace("\n", " ¶ ").trim()
        val nq = u.split(Regex("\\s+")).joinToString(" ")
        feed("س:" + u + "\nج:")
        val sameAsk = replies.any { it.first == nq }
        val prev = HashSet<String>()
        if (!sameAsk) for (r in replies.takeLast(6)) prev.addAll(grams(r.second, ngPrev))
        val selfG = HashSet<String>()
        val out = StringBuilder(); val track = ArrayList<Float>()
        val nl = m.cid('\n')
        val src = copySource(u); val cst = intArrayOf(-1)
        for (step in 0 until maxChars) {
            val pm = mix(p, memGain, shortGain)
            pm[0] = 0f
            val cc = copyNext(src, out, cst)                  // inside a file block: copy the user's own names, items and numbers
            if (cc != null) { val ci = m.cid(if (cc == '\n') '¶' else cc); for (j in 0 until m.v) pm[j] *= (1f - COPY_GAIN); pm[ci] += COPY_GAIN }
            val outNow = out.toString()
            val fileMode = outNow.contains("<<ملف:")           // code legitimately repeats itself: the anti-repetition rules are off inside a file reply
            val openBlock = outNow.lastIndexOf("<<ملف:") > outNow.lastIndexOf("<<نهاية>>")
            if (out.length < 3 || openBlock) pm[nl] = 0f     // a reply cannot end before it began, nor inside an open file block
            if (out.endsWith("\n")) pm[nl] = 0f             // avoid endless blank lines in multiline mode
            run { var tot = 0f; for (j in 0 until m.v) tot += pm[j]; if (tot <= 0f) pm[nl] = 1f }       // nothing left to write: end the reply
            if (!fileMode && out.length >= ngPrev - 1) {
                var any = false
                val tail = if (out.length > ngSelf - 1) out.substring(out.length - (ngSelf - 1)) else out.toString()      // only the last characters matter: no copy of the whole reply per candidate
                for (j in 0 until m.v) {
                    if (pm[j] <= 0f || j == nl) { if (pm[j] > 0f) any = true; continue }
                    val cand = tail + m.chars[j]
                    val bad = (cand.length >= ngSelf && selfG.contains(cand.substring(cand.length - ngSelf))) ||
                              (cand.length >= ngPrev && prev.contains(cand.substring(cand.length - ngPrev)))
                    if (bad) pm[j] = 0f else any = true
                }
                if (!any) { for (j in 0 until m.v) pm[j] = 0f; pm[nl] = 1f }     // every continuation repeats: finish the reply here
            }
            var mx = 0f; var best = 1
            for (j in 0 until m.v) if (pm[j] > mx) { mx = pm[j]; best = j }
            for (j in 0 until m.v) if (pm[j] < minP * mx) pm[j] = 0f
            for (j in 0 until m.v) if (pm[j] > 0f) pm[j] = Math.pow(pm[j].toDouble(), 1.0 / temp).toFloat()
            if (topk >= 1 && topk < m.v) {
                val sorted = pm.copyOf(); java.util.Arrays.sort(sorted)
                val cut = sorted[m.v - topk]
                for (j in 0 until m.v) if (pm[j] < cut) pm[j] = 0f
            }
            var sum = 0f
            for (j in 0 until m.v) sum += pm[j]
            var pick = best
            if (sum > 0f) {
                var r = rng.nextFloat() * sum
                for (j in 0 until m.v) { r -= pm[j]; if (r <= 0f && pm[j] > 0f) { pick = j; break } }
            }
            track.add(p[pick])
            val ch = m.chars[pick]
            feed(ch)
            if (ch == "\n") {
                if (allowMultiline) { out.append('\n'); continue }
                break
            }
            out.append(ch)
            if (out.length >= ngSelf) selfG.add(out.substring(out.length - ngSelf))
            if (!fileMode && out.length >= 48 && out.substring(0, out.length - 24).contains(out.substring(out.length - 24))) { out.setLength(out.length - 24); break }   // a loop: cut it off and stop
        }
        val raw = out.toString().replace("¶", "\n")
        val fin = (if (raw.contains("<<ملف:")) raw else dedupe(raw)).trim()           // dedupe would delete the second «<<نهاية>>»
        if (commit) { replies.add(Pair(nq, fin)); while (replies.size > 12) replies.removeAt(0); refreshShortMemory() }
        return Pair(fin, track)
    }

    private val COPY_GAIN = 0.9f
    private fun copySource(u: String): String = u.replace(Regex("\\s*،\\s*"), "\n").replace("باسم ", "\u0001ملف:").replace("مجلد ", "\u0001ملف:").replace(Regex("(\u0001ملف:)+"), "\u0001ملف:")

    /** Pointer copy, inside a «<<ملف:» block only. A run starts when the last 3+ characters written also occur in the request, after an opening bracket,
     *  after the first «: » of the request, or at the file name the user asked for; it then follows the request letter by letter and stops at a space
     *  (except after a comma) and at the end of the list. st[0] = next index in src, -1 = no run. Same logic as GRU Session._copy_dist in Python. */
    private fun copyNext(src: String, out: StringBuilder, st: IntArray): Char? {
        val outS = out.toString()
        if (outS.lastIndexOf("<<ملف:") <= outS.lastIndexOf("<<نهاية>>")) { st[0] = -1; return null }
        val o = outS.replace("¶", "\n").replace("<<ملف:", "\u0001ملف:")
        var p = st[0]
        if (p >= 0 && (p >= src.length || p == 0 || o.isEmpty() || o.last() != src[p - 1])) p = -1
        if (p < 0) {
            val opener = "\u0001ملف:"
            if (o.endsWith(opener)) { val k = src.indexOf(opener); p = if (k >= 0) k + opener.length else -1 }
            else if (o.endsWith("= [") && src.indexOf('[') >= 0) p = src.indexOf('[') + 1                 // a list literal being assigned: copy the user's list
            else if (o.endsWith(">>\n") && src.contains(": ") && isListFile(o)) p = src.indexOf(": ") + 2
            else {
                var len = minOf(12, o.length)
                while (len >= 3) { val pos = src.indexOf(o.substring(o.length - len)); if (pos >= 0) { p = pos + len; break }; len-- }
            }
        }
        if (p < 0 || p >= src.length) { st[0] = -1; return null }
        val ch = src[p]
        if (ch == '\u0001' || (ch == ' ' && (o.isEmpty() || o.last() != ','))) { st[0] = -1; return null }
        st[0] = p + 1
        return ch
    }

    /** True when the file block being written is a plain list (.txt / .md): only there the first item is taken from «قائمة ...: items». */
    private fun isListFile(o: String): Boolean {
        val i = o.lastIndexOf("\u0001ملف:"); if (i < 0) return false
        val j = o.indexOf(">>", i); if (j <= i) return false
        val nm = o.substring(i + 5, j).trim().lowercase(java.util.Locale.ROOT)
        return nm.endsWith(".txt") || nm.endsWith(".md")
    }

    private class Snap(val p: FloatArray, val a: FloatArray, val b: FloatArray, val tail: String)
    private fun snap() = Snap(p.copyOf(), s1.copyOf(), s2.copyOf(), contextTail.toString())
    private fun restore(x: Snap) { p = x.p.copyOf(); System.arraycopy(x.a, 0, s1, 0, s1.size); System.arraycopy(x.b, 0, s2, 0, s2.size); contextTail.setLength(0); contextTail.append(x.tail) }

    /** Agreement is a stability signal, NOT proof that an answer is true. */
    private fun lexicalAgreement(a: String, b: String): Float {
        fun words(s: String): Set<String> = Nlp.norm(s)
            .split(Regex("[^\\p{L}\\p{N}_]+"))
            .filter { it.length >= 2 }
            .toSet()
        val x = words(a); val y = words(b)
        if (x.isEmpty() && y.isEmpty()) return 1f
        if (x.isEmpty() || y.isEmpty()) return 0f
        return x.intersect(y).size.toFloat() / x.union(y).size.toFloat()
    }

    /** Scores visible writing quality only; it cannot determine whether claims are true. */
    private fun draftQuality(text: String): Float {
        val t = Nlp.norm(text).trim()
        if (t.isEmpty()) return 0f
        var score = 1f
        val words = t.split(Regex("[^\\p{L}\\p{N}_]+")).filter { it.isNotBlank() }
        if (words.size < 3) score -= 0.18f
        if (words.size >= 6) {
            val counts = words.groupingBy { it }.eachCount()
            val repeated = counts.values.sumOf { maxOf(0, it - 2) }
            score -= (repeated.toFloat() / words.size * 0.30f).coerceAtMost(0.30f)
        }
        val sentences = t.split(Regex("[.!؟?\n]+")).map { it.trim() }.filter { it.length >= 12 }
        if (sentences.isNotEmpty()) {
            val duplicateCount = sentences.size - sentences.toSet().size
            score -= (duplicateCount.toFloat() / sentences.size * 0.35f).coerceAtMost(0.35f)
        }
        if (Regex("(.)\\1{4,}").containsMatchIn(t)) score -= 0.15f
        if (t.endsWith(" و") || t.endsWith(" أو") || t.endsWith(" من") ||
            t.endsWith(" لأن") || t.endsWith(":") || t.endsWith(",")) score -= 0.12f
        val useful = t.count { it.isLetterOrDigit() }
        if (t.isNotEmpty() && useful.toFloat() / t.length < 0.45f) score -= 0.20f
        return score.coerceIn(0f, 1f)
    }

    /** Samples independent drafts and ranks them by likelihood, agreement and writing quality.
     *  All three are heuristics, never factual verification. */
    fun replyThink(user: String, maxChars: Int, tries: Int, accept: ((String) -> Boolean)? = null): Pair<String, List<Float>> {
        val start = snap()
        val multiline = user.length >= 500 || Regex("طويل|بالتفصيل|كامل|جدول|مشروع|عدة ملفات|صفحات|اسطر|سطور").containsMatchIn(Nlp.norm(user))
        val temps = floatArrayOf(0.55f, 0.7f, 0.85f, 0.65f, 0.75f)
        val attempts = ArrayList<Triple<Pair<String, List<Float>>, Snap, Float>>()
        for (i in 0 until minOf(tries, temps.size)) {
            restore(start)
            val r = reply(user, maxChars, temps[i], 8, 0.15f, false, allowMultiline = multiline)
            var likelihood = if (r.second.isEmpty()) 0f else r.second.sum() / r.second.size
            if (r.first.length < 8) likelihood -= 0.2f
            if (accept != null && !accept(r.first)) likelihood -= 1f
            attempts.add(Triple(r, snap(), likelihood))
            Thread.yield()
        }
        if (attempts.isEmpty()) return reply(user, maxChars)
        var bestIndex = 0
        var bestScore = -Float.MAX_VALUE
        for (i in attempts.indices) {
            var agreement = 0f
            var compared = 0
            for (j in attempts.indices) if (j != i) {
                agreement += lexicalAgreement(attempts[i].first.first, attempts[j].first.first)
                compared++
            }
            if (compared > 0) agreement /= compared.toFloat()
            val quality = draftQuality(attempts[i].first.first)
            // Consensus is not dominant: identical low-quality drafts must not win on agreement alone.
            val score = 0.30f * attempts[i].third + 0.25f * agreement + 0.45f * quality
            if (score > bestScore) { bestScore = score; bestIndex = i }
        }
        val fin = attempts[bestIndex].first
        restore(attempts[bestIndex].second)
        val u = user.replace("\n", " ¶ ").trim()
        replies.add(Pair(u.split(Regex("\\s+")).joinToString(" "), fin.first)); while (replies.size > 12) replies.removeAt(0)
        refreshShortMemory()
        return fin
    }
}
