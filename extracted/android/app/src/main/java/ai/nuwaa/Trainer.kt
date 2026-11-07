package ai.nuwaa

import android.content.Context
import java.util.Random as JRandom

/** «Raise understanding»: trains the model ON THE PHONE, a little at a time, at the CPU share the user picks.
 *  - One window of ~100 characters per step; after each step the thread sleeps so that its average share of ONE core equals `percent`
 *    (a weak phone simply goes slower: it never stops making progress and never takes more than the user allowed).
 *  - Every 40 steps the model is measured on a fixed held-out text. Better: that state is kept and saved. Clearly worse: it goes back to the best
 *    state and the learning rate is halved. On stop it goes back to the best state, so pressing the button can never leave the model worse.
 *  - Pauses itself when the phone is hot, the battery is low (and not charging), or memory is tight (Effort.deviceCap).
 *  - Chat keeps working: the model is locked for one step at a time only. */
class Trainer(private val ctx: Context, private val brain: Brain) {
    @Volatile var running = false
    @Volatile var percent = 40
    @Volatile var selfReview = true
    @Volatile var teacherOn = false
    @Volatile var teacherPerMinute = 5
    @Volatile private var last = "ما بدأ التدريب بعد."
    private var thread: Thread? = null

    private var steps = 0
    private var lossEma = 0f
    private var startHeld = 0f
    private var bestHeld = 0f
    private var rollbacks = 0
    private var stepMs = 0L
    private var windowsPerPass = 1
    private var reviewPass = 0
    private var reviewTotal = 0
    private var learnedFromSelf = 0
    private val selfPairs = ArrayList<String>()
    private val teacherPairs = ArrayList<String>()
    private var teacherFetched = 0; private var teacherKept = 0; private var lastTeacherFetch = 0L

    fun summary(): String = last

    fun stop() { running = false }
    fun stopAndWait(ms: Long) { running = false; try { thread?.join(ms) } catch (e: InterruptedException) { } }

    fun start(onUpdate: (String) -> Unit) {
        if (running) return
        val m = brain.trainModel()
        val pairs = brain.trainPairs()
        if (m == null) { last = "النموذج غير محمّل."; onUpdate(last); return }
        if (pairs.size < 100) { last = "ملف التدريب غير موجود داخل التطبيق."; onUpdate(last); return }
        running = true
        thread = Thread {
            try { android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND) } catch (e: Throwable) { }
            val rnd = java.util.Random(System.nanoTime())
            val heldPairs = pairs.filterIndexed { i, _ -> i % 53 == 7 }
            val trainPairs = pairs.filterIndexed { i, _ -> i % 53 != 7 }
            val heldIds = m.encode("\n" + heldPairs.take(10).joinToString(""))
            windowsPerPass = maxOf(1, trainPairs.sumOf { it.length } / 100)
            var best = synchronized(brain.modelLock) { m.bpc(heldIds) }
            var snap = synchronized(brain.modelLock) { m.trainingSnapshot() }
            startHeld = best; bestHeld = best; steps = 0; rollbacks = 0; lossEma = 0f
            var lr = 1e-3f
            while (running) {
                val cap = Effort.deviceCap(ctx)
                if (cap.first == 0) { last = "⏸ توقفت مؤقتا: " + cap.second + ". أكمل تلقائيا لما يتحسن الوضع."; onUpdate(report()); sleepSafe(8000); continue }
                val t0 = System.nanoTime()
                val sb = StringBuilder("\n")
                while (sb.length < 100) sb.append(
                    if (teacherPairs.isNotEmpty() && rnd.nextInt(6) == 0) teacherPairs[rnd.nextInt(teacherPairs.size)]
                    else if (selfPairs.isNotEmpty() && rnd.nextInt(5) == 0) selfPairs[rnd.nextInt(selfPairs.size)]
                    else trainPairs[rnd.nextInt(trainPairs.size)])
                val text = sb.substring(0, minOf(sb.length, 128))
                val bits = synchronized(brain.modelLock) { m.trainWindow(text, lr) }
                steps++
                lossEma = if (steps == 1) bits else 0.98f * lossEma + 0.02f * bits
                val busy = (System.nanoTime() - t0) / 1_000_000
                stepMs = if (stepMs == 0L) busy else (stepMs * 9 + busy) / 10
                if (steps % 40 == 0) {
                    val now = synchronized(brain.modelLock) { m.bpc(heldIds) }
                    if (now <= best) { best = now; bestHeld = now; synchronized(brain.modelLock) { snap = m.trainingSnapshot() }; brain.saveTrained() }
                    else if (now > best * 1.03f) { synchronized(brain.modelLock) { m.restoreTrainingSnapshot(snap) }; lr = maxOf(lr * 0.5f, 1e-4f); rollbacks++ }
                }
                if (teacherOn && GeminiTeacher.configured(ctx) && running) {
                    val gapMs = (60000.0 / teacherPerMinute.coerceIn(1, 60)).toLong()
                    if (System.currentTimeMillis() - lastTeacherFetch >= gapMs) {
                        lastTeacherFetch = System.currentTimeMillis(); teacherFetched++
                        val ex = GeminiTeacher.fetchExample(ctx, JRandom())
                        if (ex != null) { teacherKept++; teacherPairs.add("س:" + ex.first + "\nج:" + ex.second.replace("\n", "¶") + "\n"); if (teacherPairs.size > 300) teacherPairs.removeAt(0) }
                    }
                }
                if (selfReview && steps % 120 == 0) {                     // self-review: tasks whose answer the app knows; learn from the ones passed
                    for (task in SelfCheck.makeTasks(3, rnd)) {
                        if (!running) break
                        val reply = brain.selfAttempt(task.ask); reviewTotal++
                        if (SelfCheck.passes(task, reply)) { reviewPass++; learnedFromSelf++; selfPairs.add("س:" + task.ask + "\nج:" + reply.replace("\n", "¶") + "\n"); if (selfPairs.size > 60) selfPairs.removeAt(0) }
                    }
                }
                last = "⚡ شغّال"
                if (steps % 3 == 0) onUpdate(report())
                val pct = percent.coerceIn(5, 100)
                val work = (System.nanoTime() - t0) / 1_000_000
                if (pct < 100) sleepSafe(work * (100 - pct) / pct)       // average share of one core = pct; everything counts (measurement and self-review too)
            }
            synchronized(brain.modelLock) { m.restoreTrainingSnapshot(snap) }       // always end on the best state: the button can never make the model worse
            brain.saveTrained()
            last = "⏹ توقفت وحفظت أفضل حالة. القياس: " + f(startHeld) + " ← " + f(bestHeld) + " بت/حرف (الأقل أفضل)."
            onUpdate(report())
        }
        thread!!.start()
    }

    private fun f(x: Float): String = String.format(java.util.Locale.US, "%.3f", x)

    private fun sleepSafe(ms: Long) { try { Thread.sleep(ms) } catch (e: InterruptedException) { } }

    private fun report(): String {
        val sb = StringBuilder(last).append("\n\n")
        sb.append("• الخطوات: ").append(steps).append(" (كل خطوة ~100 حرف)\n")
        sb.append("• خطأ التدريب الحالي: ").append(f(lossEma)).append(" بت/حرف\n")
        sb.append("• قياسي على نص ثابت لم أتدرب عليه: ").append(f(startHeld)).append(" ← ").append(f(bestHeld)).append(" (الأقل أفضل)\n")
        sb.append("• رجوع للأفضل لما ساء القياس: ").append(rollbacks).append(" مرة\n")
        if (selfReview) sb.append("• مراجعتي لنفسي (مهام ملفات أعرف جوابها): نجحت في ").append(reviewPass).append(" من ").append(reviewTotal).append("، وتعلمت من ").append(learnedFromSelf).append(" جواب صحيح لي\n")
        if (teacherOn) sb.append("• معلّم Gemini: طلبت ").append(teacherFetched).append(" مثالا، قُبل منها (ضمن التخصص) ").append(teacherKept).append("، وأحفظها كمادة تدريب غير مُتحقَّق بتشغيلها (محمية بنفس قاعدة التراجع)\n")
        if (stepMs > 0) {
            val pct = percent.coerceIn(5, 100)
            val perStep = stepMs * 100 / pct
            val remain = (windowsPerPass - steps).coerceAtLeast(0).toLong() * perStep / 1000
            sb.append("• سرعة الخطوة: ").append(stepMs).append(" ملّي ثانية شغل، وبالاستهلاك المختار ~").append(perStep / 1000.0).append(" ثانية للخطوة\n")
            sb.append("• تقدير مرور واحد على كل بياناتي: ").append(if (remain > 3600) (remain / 3600).toString() + " ساعة تقريبا" else (remain / 60).toString() + " دقيقة تقريبا").append("\n")
        }
        sb.append("\nمهم: التدريب على الجوال بطيء بطبيعته. يتقدم بالتدريج ويُحفظ كل ما يتحسن، ويمكنك إيقافه وإكماله في أي وقت. لا يعمل إذا أغلقت التطبيق.")
        return sb.toString()
    }
}
