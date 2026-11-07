package ai.nuwaa

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.SystemClock

/** Screen sharing: captures ONE frame per second (the app never processes more), measures how much the screen changed,
 *  reads the on-screen text through ScreenReader (if enabled) and shows advice in the notification and in the app. */
class ScreenShareService : Service() {
    companion object {
        @Volatile var running = false
        @Volatile var goal = ""
        @Volatile var frameListener: ((Bitmap, Double) -> Unit)? = null
        @Volatile var adviceListener: ((String) -> Unit)? = null
        @Volatile var stopListener: (() -> Unit)? = null
        @Volatile var lastScreenText = ""
        const val CHANNEL = "nuwaa_screen"
        const val NOTE_ID = 77
        const val ACTION_STOP = "ai.nuwaa.STOP_SHARE"
    }

    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var thread: HandlerThread? = null
    private var lastFrame = 0L
    private var lastAdvice = 0L
    private var lastAdviceText = ""
    private var prev: IntArray? = null
    private var stopped = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null) { shutdown(); return START_NOT_STICKY }
        if (intent.action == ACTION_STOP) { shutdown(); return START_NOT_STICKY }
        startForegroundNow()
        val code = intent.getIntExtra("code", 0)
        val data = readData(intent)
        if (data == null) { shutdown(); return START_NOT_STICKY }
        try { begin(code, data) } catch (e: Throwable) { shutdown() }
        return START_NOT_STICKY
    }

    @Suppress("DEPRECATION")
    private fun readData(i: Intent): Intent? =
        if (Build.VERSION.SDK_INT >= 33) i.getParcelableExtra("data", Intent::class.java) else i.getParcelableExtra<Intent>("data")

    @Suppress("DEPRECATION")
    private fun legacyBuilder(): Notification.Builder = Notification.Builder(this)

    private fun buildNote(text: String): Notification {
        val b: Notification.Builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL) else legacyBuilder()
        return b.setContentTitle("نواة تشاهد الشاشة (إطار كل ثانية)")
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setSmallIcon(android.R.drawable.ic_menu_view)
            .setOngoing(true)
            .build()
    }

    private fun startForegroundNow() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) nm.createNotificationChannel(NotificationChannel(CHANNEL, "مشاركة الشاشة", NotificationManager.IMPORTANCE_LOW))
        val n = buildNote("جاري المراقبة. افتح التطبيق لإيقاف المشاركة.")
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTE_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION) else startForeground(NOTE_ID, n)
    }

    private fun begin(code: Int, data: Intent) {
        val mpm = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val p = mpm.getMediaProjection(code, data)
        projection = p
        val th = HandlerThread("nuwaa-capture")
        th.start()
        thread = th
        val h = Handler(th.looper)
        p.registerCallback(object : MediaProjection.Callback() { override fun onStop() { shutdown() } }, h)   // required on Android 14
        val dm = resources.displayMetrics
        val scale = 540f / maxOf(dm.widthPixels, dm.heightPixels).toFloat()
        val w = maxOf(64, (dm.widthPixels * scale).toInt())
        val hh = maxOf(64, (dm.heightPixels * scale).toInt())
        val r = ImageReader.newInstance(w, hh, PixelFormat.RGBA_8888, 2)
        reader = r
        display = p.createVirtualDisplay("nuwaa", w, hh, dm.densityDpi, DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, r.surface, null, h)
        r.setOnImageAvailableListener({ rd -> onFrame(rd) }, h)
        running = true
    }

    private fun onFrame(rd: ImageReader) {
        val img: Image? = try { rd.acquireLatestImage() } catch (e: Exception) { null }
        if (img == null) return
        try {
            val now = SystemClock.elapsedRealtime()
            if (now - lastFrame < 1000) return          // one frame per second, the rest are dropped
            lastFrame = now
            val pl = img.planes[0]
            val rowPixels = pl.rowStride / pl.pixelStride
            val full = Bitmap.createBitmap(rowPixels, img.height, Bitmap.Config.ARGB_8888)
            full.copyPixelsFromBuffer(pl.buffer)
            val bmp = if (rowPixels == img.width) full else Bitmap.createBitmap(full, 0, 0, img.width, img.height)
            val change = changeScore(bmp)
            frameListener?.invoke(bmp, change)
            maybeAdvise(now)
        } catch (e: Throwable) {
            /* a bad frame must never kill the service */
        } finally {
            img.close()
        }
    }

    private fun changeScore(b: Bitmap): Double {
        val cur = IntArray(256)
        for (gy in 0 until 16) for (gx in 0 until 16) {
            val px = b.getPixel(gx * b.width / 16 + b.width / 32, gy * b.height / 16 + b.height / 32)
            cur[gy * 16 + gx] = (Color.red(px) * 3 + Color.green(px) * 6 + Color.blue(px)) / 10
        }
        val old = prev
        prev = cur
        if (old == null) return 0.0
        var d = 0
        for (i in 0 until 256) d += Math.abs(cur[i] - old[i])
        return d / (256.0 * 255.0)
    }

    private fun maybeAdvise(now: Long) {
        if (now - lastAdvice < 3000) return
        lastAdvice = now
        val text = ScreenReader.readText()
        lastScreenText = text
        if (text.isEmpty() || text == lastAdviceText) return
        lastAdviceText = text
        val advice = Brain.get(this).adviseScreen(text, goal)
        adviceListener?.invoke(advice)
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTE_ID, buildNote(advice.take(600)))
    }

    private fun shutdown() {
        if (stopped) return
        stopped = true
        running = false
        try { display?.release() } catch (e: Throwable) {}
        try { reader?.close() } catch (e: Throwable) {}
        val p = projection
        projection = null; display = null; reader = null
        try { p?.stop() } catch (e: Throwable) {}
        try { thread?.quitSafely() } catch (e: Throwable) {}
        thread = null
        stopListener?.invoke()
        try { stopForeground(true) } catch (e: Throwable) {}
        stopSelf()
    }

    override fun onDestroy() { shutdown(); super.onDestroy() }
}
