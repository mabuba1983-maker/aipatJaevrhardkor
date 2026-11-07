package ai.nuwaa

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.label.ImageLabeling
import com.google.mlkit.vision.label.defaults.ImageLabelerOptions
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * Offline visual front-end for Nuwaa's current text-only GRU.
 * Image labels + Latin OCR become grounded text observations for the language model.
 * This is an adapter, not an end-to-end multimodal neural model: Nuwaa's GRU never receives pixels.
 */
class VisionEngine {
    fun analyzeBlocking(bytes: ByteArray, timeoutMs: Long = 25000): String {
        val latch = CountDownLatch(1)
        var result = "انتهت مهلة تحليل الصورة."
        analyze(bytes) {
            result = it
            latch.countDown()
        }
        try { latch.await(timeoutMs, TimeUnit.MILLISECONDS) }
        catch (_: InterruptedException) { Thread.currentThread().interrupt() }
        return result
    }

    fun analyze(bytes: ByteArray, callback: (String) -> Unit) {
        val bitmap = try {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
                callback("تعذر فك الصورة أو أن الملف ليس صورة مدعومة.")
                return
            }
            var sample = 1
            while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 1280) sample *= 2
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inSampleSize = sample })
        } catch (_: Throwable) { null }
        if (bitmap == null) {
            callback("تعذر تحميل الصورة.")
            return
        }
        analyze(bitmap) { result ->
            if (!bitmap.isRecycled) bitmap.recycle()
            callback(result)
        }
    }

    fun analyze(source: Bitmap, callback: (String) -> Unit) {
        val maxSide = maxOf(source.width, source.height)
        val imageBitmap = if (maxSide > 1280) {
            val scale = 1280f / maxSide
            Bitmap.createScaledBitmap(source, (source.width * scale).toInt().coerceAtLeast(1),
                (source.height * scale).toInt().coerceAtLeast(1), true)
        } else source
        val input = InputImage.fromBitmap(imageBitmap, 0)
        val labeler = ImageLabeling.getClient(
            ImageLabelerOptions.Builder().setConfidenceThreshold(0.35f).build()
        )
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        val remaining = AtomicInteger(2)
        var labelsText = "لم يحدد محلل العناصر شيئا واضحا."
        var ocrText = "لم يُعثر على نص مقروء."
        fun finishOne() {
            if (remaining.decrementAndGet() == 0) {
                callback(
                    "مؤشرات العناصر: " + labelsText +
                    "\nالنص المقروء (OCR؛ دعم النص هنا للخط اللاتيني): " + ocrText
                )
                labeler.close()
                recognizer.close()
                if (imageBitmap !== source && !imageBitmap.isRecycled) imageBitmap.recycle()
            }
        }
        try {
            labeler.process(input)
                .addOnSuccessListener { labels ->
                    val top = labels.sortedByDescending { it.confidence }.take(12)
                    labelsText = if (top.isEmpty()) "لم يحدد محلل العناصر شيئا واضحا." else
                        top.joinToString("؛ ") { it.text + " (" + (it.confidence * 100).toInt() + "%)" }
                    finishOne()
                }
                .addOnFailureListener { error ->
                    labelsText = "تعذر تصنيف العناصر: " + (error.message ?: error.javaClass.simpleName)
                    finishOne()
                }
            recognizer.process(input)
                .addOnSuccessListener { result ->
                    ocrText = result.text.replace(Regex("\\s+"), " ").trim().take(1800).ifEmpty { "لم يُعثر على نص مقروء." }
                    finishOne()
                }
                .addOnFailureListener { error ->
                    ocrText = "تعذر استخراج النص: " + (error.message ?: error.javaClass.simpleName)
                    finishOne()
                }
        } catch (error: Throwable) {
            labeler.close()
            recognizer.close()
            if (imageBitmap !== source && !imageBitmap.isRecycled) imageBitmap.recycle()
            callback("تعذر تشغيل الرؤية المحلية: " + (error.message ?: error.javaClass.simpleName))
        }
    }
}
