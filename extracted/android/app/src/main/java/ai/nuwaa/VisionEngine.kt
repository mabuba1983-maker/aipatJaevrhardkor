package ai.nuwaa

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.label.ImageLabeling
import com.google.mlkit.vision.label.defaults.ImageLabelerOptions

/**
 * Offline visual front-end for Nuwaa's current text-only GRU.
 * ML Kit supplies image concepts; Nuwaa's language model receives the resulting
 * grounded description. This is not an end-to-end multimodal neural model.
 */
class VisionEngine {
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
        val image = if (maxSide > 1280) {
            val scale = 1280f / maxSide
            Bitmap.createScaledBitmap(source, (source.width * scale).toInt().coerceAtLeast(1),
                (source.height * scale).toInt().coerceAtLeast(1), true)
        } else source
        val labeler = ImageLabeling.getClient(
            ImageLabelerOptions.Builder().setConfidenceThreshold(0.35f).build()
        )
        try {
            labeler.process(InputImage.fromBitmap(image, 0))
                .addOnSuccessListener { labels ->
                    val top = labels.sortedByDescending { it.confidence }.take(12)
                    val description = if (top.isEmpty()) {
                        "لم يستطع محلل الرؤية تحديد عناصر بثقة كافية."
                    } else {
                        "العناصر والسمات التي اكتشفها محلل الصورة محليا (اسم التصنيف بالإنجليزية، والثقة تقريبية): " +
                            top.joinToString("؛ ") { it.text + " (" + (it.confidence * 100).toInt() + "%)" }
                    }
                    callback(description)
                    labeler.close()
                    if (image !== source && !image.isRecycled) image.recycle()
                }
                .addOnFailureListener { error ->
                    callback("فشل تحليل الصورة محليا: " + (error.message ?: error.javaClass.simpleName))
                    labeler.close()
                    if (image !== source && !image.isRecycled) image.recycle()
                }
        } catch (error: Throwable) {
            callback("تعذر تشغيل محلل الصورة: " + (error.message ?: error.javaClass.simpleName))
            labeler.close()
            if (image !== source && !image.isRecycled) image.recycle()
        }
    }
}
