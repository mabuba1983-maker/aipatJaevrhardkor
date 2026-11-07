package ai.nuwaa

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Typeface
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.net.Uri
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.os.Environment
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.*
import kotlin.concurrent.thread

class MainActivity : Activity() {
    private lateinit var brain: Brain
    private lateinit var store: ChatStore
    private var conv: Conv? = null
    private lateinit var pages: FrameLayout
    private lateinit var chatPage: LinearLayout
    private lateinit var histPage: LinearLayout
    private lateinit var screenPage: ScrollView
    private lateinit var codePage: LinearLayout
    private lateinit var titleView: TextView
    private lateinit var status: TextView
    private lateinit var log: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var input: EditText
    private lateinit var histList: LinearLayout
    private lateinit var preview: ImageView
    private lateinit var shareInfo: TextView
    private lateinit var adviceView: TextView
    private lateinit var shareBtn: TextView
    private lateinit var goalInput: EditText
    private lateinit var editor: EditText
    private lateinit var codeIdea: EditText
    private val REQ_CAPTURE = 41
    private val REQ_NOTIF = 42
    private val REQ_PICK = 43
    private val REQ_CREATE = 44
    private var pendingFile: String = ""
    private var pendingBytes: ByteArray? = null
    private lateinit var devPage: LinearLayout
    private lateinit var trainPage: LinearLayout
    private lateinit var discoverPage: LinearLayout
    private lateinit var discoverResult: TextView
    private lateinit var growPage: LinearLayout
    private lateinit var growResult: TextView
    private var titleTaps = 0; private var titleTapsAt = 0L
    private var revealedGrowMenu = false
    private lateinit var trainInfo: TextView
    private lateinit var trainBtn: TextView
    private lateinit var pctLabel: TextView
    private var trainerObj: Trainer? = null
    private var fileMode = false
    private lateinit var fileBtn: TextView
    private lateinit var modeBar: TextView
    private fun trainer(): Trainer = trainerObj ?: Trainer(this, brain).also { trainerObj = it }
    private lateinit var devReport: TextView
    private val MAX_READ = 8_000_000
    private var attached: Attached? = null
    private lateinit var attachBar: LinearLayout
    private lateinit var attachLabel: TextView

    private fun dp(v: Int) = Ui.dp(this, v)

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        window.statusBarColor = Ui.DARK
        store = ChatStore(java.io.File(filesDir, "chats"))
        brain = Brain.get(this)
        buildUi()
        setContentView(rootView)
        conv = store.list().firstOrNull() ?: store.create()
        renderConv()
        showPage(chatPage)
        status.text = "جاري تجهيز النموذج..."
        thread {
            brain.loadModel()
            conv?.let { c -> if (c.msgs.isNotEmpty()) brain.resume(c.id, c.msgs.toList()) }      // the open conversation gets its short-term memory back
            runOnUiThread { status.text = brain.modelStatus }
        }
    }

    private lateinit var rootView: LinearLayout

    private fun buildUi() {
        rootView = LinearLayout(this)
        rootView.orientation = LinearLayout.VERTICAL
        rootView.layoutDirection = View.LAYOUT_DIRECTION_RTL
        rootView.setBackgroundColor(Ui.BG)
        rootView.fitsSystemWindows = true

        val bar = LinearLayout(this)
        bar.orientation = LinearLayout.HORIZONTAL
        bar.gravity = Gravity.CENTER_VERTICAL
        bar.setBackgroundColor(Ui.DARK)
        bar.setPadding(dp(8), dp(8), dp(8), dp(8))
        val menu = TextView(this)
        menu.text = "☰"; menu.textSize = 26f; menu.setTextColor(Color.WHITE); menu.setPadding(dp(12), 0, dp(12), 0)
        menu.setOnClickListener { showMenu() }
        val dev = TextView(this); dev.text = "🧠"; dev.textSize = 22f; dev.setTextColor(Color.WHITE); dev.setPadding(dp(10), 0, dp(10), 0)
        dev.setOnClickListener { showPage(devPage) }
        val tcol = LinearLayout(this); tcol.orientation = LinearLayout.VERTICAL
        titleView = Ui.label(this, "نواة", 20f, Color.WHITE, true)
        titleView.setOnClickListener { onTitleTap() }
        status = Ui.label(this, "", 11f, Color.parseColor("#9FB3C0"), false)
        tcol.addView(titleView); tcol.addView(status)
        bar.addView(menu)
        bar.addView(tcol, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        bar.addView(dev)
        rootView.addView(bar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        pages = FrameLayout(this)
        rootView.addView(pages, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        buildChatPage(); buildHistPage(); buildScreenPage(); buildCodePage(); buildDevPage(); buildTrainPage(); buildDiscoverPage(); buildGrowPage()
    }

    // ---------------- pages ----------------
    private fun showPage(p: View) {
        pages.removeAllViews()
        pages.addView(p, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        if (p === histPage) refreshHistory()
    }

    private fun showMenu() {
        val base = arrayOf("💬  محادثة جديدة", "🧠  تطوير النفس", "🗂  المحادثات السابقة", "📱  مشاركة الشاشة", "💻  كتابة الأكواد", "🗑  حذف كل المحادثات", "ℹ️  عن التطبيق", "⚡  رفع الفهم (تدريب)", "🔍  اكتشاف من الإنترنت")
        val items = if (revealedGrowMenu) base + "⚙  تطوير متقدم" else base
        AlertDialog.Builder(this).setItems(items) { _, i ->
            when (i) {
                0 -> newChat()
                1 -> showPage(devPage)
                2 -> showPage(histPage)
                3 -> { showPage(screenPage); refreshShareUi() }
                4 -> showPage(codePage)
                5 -> confirmDeleteAll()
                6 -> showAbout()
                7 -> showPage(trainPage)
                8 -> showPage(discoverPage)
                9 -> openGrowPage()
            }
        }.show()
    }

    private fun newChat() {
        val c = conv
        if (c != null && c.msgs.isEmpty()) { showPage(chatPage); return }
        if (c != null) brain.endConversation(c.id)                    // the conversation ended: its short-term memory ends with it
        conv = store.create(); renderConv(); showPage(chatPage)
    }

    private fun confirmDeleteAll() {
        AlertDialog.Builder(this).setMessage("حذف كل المحادثات نهائيا؟ (ما علّمتني إياه يبقى محفوظا)")
            .setPositiveButton("حذف") { _, _ -> for (x in store.list()) brain.endConversation(x.id); store.deleteAll(); conv = store.create(); renderConv(); showPage(chatPage) }
            .setNegativeButton("إلغاء", null).show()
    }

    private fun showAbout() {
        val m = brain.usedMb()
        AlertDialog.Builder(this).setTitle("نواة").setMessage(
            "نموذج عربي يعمل على جوالك بدون إنترنت.\n\n" + brain.modelStatus +
            "\nأمثلة الأكواد المختبرة في صفحة الأكواد: " + brain.kb.items.size + "." +
            "\nذاكرة التطبيق الآن: " + m.toInt() + " MB (بدون حد أقصى أضعه أنا؛ الحد هو ذاكرة جهازك)." +
            "\n\nمحدودية صادقة: أنا نموذج صغير. أكتب ردودي بنفسي حرفا بعد حرف بدون ردود جاهزة، وقد أخطئ أو أكتب كلاما ركيكا، وأتحسن كلما تحدثت معي وتدربت."
        ).setPositiveButton("حسنا", null).show()
    }

    // ---------------- chat ----------------
    private fun buildChatPage() {
        chatPage = LinearLayout(this); chatPage.orientation = LinearLayout.VERTICAL
        scroll = ScrollView(this); log = LinearLayout(this); log.orientation = LinearLayout.VERTICAL
        log.setPadding(0, dp(8), 0, dp(8)); scroll.addView(log)
        chatPage.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        attachBar = LinearLayout(this); attachBar.orientation = LinearLayout.HORIZONTAL; attachBar.gravity = Gravity.CENTER_VERTICAL
        attachBar.setBackgroundColor(Color.parseColor("#E3F1F2")); attachBar.setPadding(dp(14), dp(6), dp(8), dp(6)); attachBar.visibility = View.GONE
        attachLabel = Ui.label(this, "", 13f, Ui.DARK, false)
        val x = TextView(this); x.text = "✕"; x.textSize = 18f; x.setTextColor(Ui.MUTED); x.setPadding(dp(14), dp(2), dp(14), dp(2))
        x.setOnClickListener { attached = null; attachBar.visibility = View.GONE }
        attachBar.addView(attachLabel, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)); attachBar.addView(x)
        chatPage.addView(attachBar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        val row = LinearLayout(this); row.orientation = LinearLayout.HORIZONTAL; row.gravity = Gravity.CENTER_VERTICAL
        row.setPadding(dp(8), dp(6), dp(8), dp(6)); row.setBackgroundColor(Color.WHITE)
        input = EditText(this); input.hint = "اكتب سؤالك هنا..."; input.maxLines = 4
        input.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        input.imeOptions = EditorInfo.IME_FLAG_NO_EXTRACT_UI
        input.background = Ui.bg(this, Color.parseColor("#EEF2F5"), 22); input.setPadding(dp(16), dp(10), dp(16), dp(10))
        val send = Ui.btn(this, "إرسال", Ui.PRIMARY) { onSend() }
        fileBtn = Ui.btn(this, "📄", Color.parseColor("#8A97A0")) { toggleFileMode() }
        fileBtn.textSize = 18f
        val flp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT); flp.setMargins(0, 0, dp(6), 0)
        val plus = Ui.btn(this, "＋", Ui.DARK) { showPlus() }
        plus.textSize = 20f
        val plp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT); plp.setMargins(0, 0, dp(8), 0)
        row.addView(plus, plp)
        row.addView(fileBtn, flp)
        row.addView(input, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT); lp.setMargins(dp(8), 0, 0, 0)
        row.addView(send, lp)
        modeBar = Ui.label(this, "📄 وضع إنشاء الملفات شغّال: كل رسالة تكتبها تُعامل كوصف لملف أنشئه لك (النوع، الاسم، ماذا فيه). اضغط 📄 لإيقافه.", 13f, Color.WHITE, false)
        modeBar.setBackgroundColor(Color.parseColor("#1565C0")); modeBar.setPadding(dp(14), dp(7), dp(14), dp(7)); modeBar.visibility = View.GONE
        chatPage.addView(modeBar, chatPage.childCount - 0, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        chatPage.addView(row, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
    }

    /** Tapping the title 5 times within 2 seconds reveals the hidden "⚙ تطوير متقدم" menu item (same trick as Android's own Developer Options:
     *  not real security, just a speed bump so growing the model — heavy, resource-hungry — is never one accidental tap away). */
    private fun onTitleTap() {
        val now = System.currentTimeMillis()
        if (now - titleTapsAt > 2000) titleTaps = 0
        titleTapsAt = now; titleTaps++
        if (titleTaps >= 5 && !revealedGrowMenu) { revealedGrowMenu = true; titleTaps = 0; Toast.makeText(this, "⚙ ظهر تطوير متقدم في القائمة", Toast.LENGTH_SHORT).show() }
    }

    /** The file button. Off (gray): no file is ever created from the chat, whatever words I type. On (blue): every message is a request for a file. */
    private fun toggleFileMode() {
        fileMode = !fileMode
        fileBtn.background = Ui.bg(this, if (fileMode) Color.parseColor("#1565C0") else Color.parseColor("#8A97A0"), 20)
        modeBar.visibility = if (fileMode) View.VISIBLE else View.GONE
        input.hint = if (fileMode) "صف الملف: النوع، الاسم، وماذا فيه..." else "اكتب سؤالك هنا..."
    }

    private fun renderConv() {
        log.removeAllViews()
        val c = conv ?: return
        titleView.text = if (c.title == "محادثة جديدة") "نواة" else c.title
        if (c.msgs.isEmpty()) {
            bubble("هلا! أنا نواة 👋\nأكتب ردودي بنفسي حرفا بعد حرف، وأتعلم من كلامك بدون ما تقول لي «تعلم». أحسب لك بدقة، وأتدرب على البرمجة.\nجرّب: «كيف اكتب حلقة for في بايثون» أو «كم يساوي ٢٥ × ١٧».", false, false)
            chips()
        } else for (m in c.msgs) bubble(m.text, m.role == "u", false)
    }

    private fun chips() {
        val box = LinearLayout(this); box.orientation = LinearLayout.VERTICAL; box.setPadding(dp(12), dp(4), dp(12), 0)
        for (q in listOf("كيف اكتب دالة في بايثون", "ما الفرق بين let و const", "كيف ارفع مشروعي على github", "كيف اوسط عنصر في css")) {
            val t = TextView(this); t.text = q; t.textSize = 14f; t.setTextColor(Ui.PRIMARY); t.setPadding(dp(14), dp(8), dp(14), dp(8))
            t.background = Ui.bg(this, Color.WHITE, 16)
            val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT); lp.setMargins(0, dp(3), 0, dp(3))
            t.setOnClickListener { input.setText(q); onSend() }
            box.addView(t, lp)
        }
        log.addView(box)
    }

    /** Splits ``` blocks: code is shown in a dark monospace box (left-to-right) with a copy button. */
    private fun bubble(text: String, mine: Boolean, scrollDown: Boolean = true) {
        val wrap = LinearLayout(this); wrap.orientation = LinearLayout.VERTICAL
        wrap.setPadding(dp(14), dp(10), dp(14), dp(10))
        wrap.background = Ui.bg(this, if (mine) Ui.PRIMARY else Color.WHITE, 18)
        val parts = text.split("```")
        for ((i, p) in parts.withIndex()) {
            if (i % 2 == 0) {
                val s = p.trim('\n')
                if (s.isNotEmpty()) {
                    val tv = TextView(this); tv.text = s; tv.textSize = 16f; tv.setTextColor(if (mine) Color.WHITE else Color.parseColor("#12222D")); tv.setTextIsSelectable(true)
                    wrap.addView(tv)
                }
            } else {
                val code = p.substringAfter('\n', p).trim('\n')
                val box = LinearLayout(this); box.orientation = LinearLayout.VERTICAL; box.layoutDirection = View.LAYOUT_DIRECTION_LTR
                box.background = Ui.bg(this, Ui.CODE_BG, 10); box.setPadding(dp(10), dp(8), dp(10), dp(8))
                val hs = HorizontalScrollView(this)
                val tv = TextView(this); tv.text = code; tv.typeface = Typeface.MONOSPACE; tv.textSize = 13f; tv.setTextColor(Color.parseColor("#D7E3EA")); tv.setTextIsSelectable(true)
                tv.textDirection = View.TEXT_DIRECTION_LTR; hs.addView(tv)
                val copy = TextView(this); copy.text = "نسخ"; copy.textSize = 12f; copy.setTextColor(Color.parseColor("#7FD6DD")); copy.setPadding(0, dp(6), 0, 0)
                copy.setOnClickListener { copyText(code); Toast.makeText(this, "تم النسخ", Toast.LENGTH_SHORT).show() }
                box.addView(hs); box.addView(copy)
                val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); lp.setMargins(0, dp(6), 0, dp(6))
                wrap.addView(box, lp)
            }
        }
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        lp.setMargins(dp(12), dp(4), dp(12), dp(4)); lp.gravity = if (mine) Gravity.START else Gravity.END
        log.addView(wrap, lp)
        if (scrollDown) scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun copyText(s: String) {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("code", s))
    }

    private fun onSend() {
        val q = input.text.toString().trim()
        val att = attached
        if (q.isEmpty() && att == null) return
        input.setText("")
        val c = conv ?: store.create().also { conv = it }
        if (c.msgs.isEmpty()) log.removeAllViews()
        val shown = if (att != null && !att.announced) "📎 " + att.name + (if (q.isNotEmpty()) "\n" + q else "") else q
        if (att != null) att.announced = true
        addMsg(c, "u", shown)
        val dots = TextView(this); dots.text = "نواة تكتب..."; dots.setTextColor(Ui.MUTED); dots.setPadding(dp(16), dp(4), dp(16), dp(4)); log.addView(dots)
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
        thread {
            val lastBot = c.msgs.lastOrNull { it.role == "b" }?.text ?: ""
            val a = try {
                val fr = if (q.isNotEmpty() && att == null && fileMode) brain.fileRequest(q, c.id, lastBot, true) else null      // a sent file is being reviewed: never create files then
                if (fr != null) createFileAnswer(fr) else if (att != null) brain.answerAbout(att, q) else brain.answer(q, c.id)
            } catch (e: Throwable) { Answer("حصل خطأ داخلي: " + (e.message ?: e.javaClass.simpleName), "error") }
            // only the model's own words are shown as its reply; everything else is labelled as coming from the app (reports, notices, exact arithmetic)
            val shown = when (a.source) { "lm" -> a.text; "math" -> "🧮 حساب دقيق (من التطبيق، ليس من النموذج):\n" + a.text; else -> "⚙ رسالة من التطبيق (ليست من النموذج):\n" + a.text }
            runOnUiThread { log.removeView(dots); addMsg(c, "b", shown) }
        }
    }

    // ---------------- creating a file from the chat: really written, then re-read, then reported ----------------
    private fun mimeOf(name: String): String = when (name.substringAfterLast('.', "").lowercase(java.util.Locale.ROOT)) {
        "txt" -> "text/plain"; "json" -> "application/json"; "csv" -> "text/csv"; "html" -> "text/html"; "css" -> "text/css"
        else -> "application/octet-stream"      // keeps the real extension (.py, .kt ...): text/plain would make Android add .txt
    }

    /** Writes the file and returns where it is. Throws if it could not be written or the bytes read back do not match. */
    private fun saveToDownloads(f: MadeFile): String {
        if (Build.VERSION.SDK_INT >= 29) {
            val v = ContentValues()
            val dirPart = f.name.substringBeforeLast('/', ""); val baseName = f.name.substringAfterLast('/')
            v.put(MediaStore.MediaColumns.DISPLAY_NAME, baseName); v.put(MediaStore.MediaColumns.MIME_TYPE, mimeOf(baseName))
            v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Nuwaa" + (if (dirPart.isNotEmpty()) "/" + dirPart else ""))
            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v) ?: throw java.io.IOException("النظام رفض إنشاء الملف")
            contentResolver.openOutputStream(uri)?.use { it.write(f.bytes) } ?: throw java.io.IOException("تعذر فتح الملف للكتابة")
            val back = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: throw java.io.IOException("تعذر إعادة قراءة الملف")
            if (!back.contentEquals(f.bytes)) throw java.io.IOException("المحتوى المقروء لا يطابق ما كُتب")
            var shown = baseName
            contentResolver.query(uri, arrayOf(MediaStore.MediaColumns.DISPLAY_NAME), null, null, null)?.use { cur -> if (cur.moveToFirst()) shown = cur.getString(0) ?: shown }
            return "Download/Nuwaa/" + (if (dirPart.isNotEmpty()) dirPart + "/" else "") + shown
        }
        val out = java.io.File(java.io.File(getExternalFilesDir(null) ?: filesDir, "Nuwaa"), f.name); out.parentFile?.mkdirs()
        out.writeBytes(f.bytes)
        if (!out.readBytes().contentEquals(f.bytes)) throw java.io.IOException("المحتوى المقروء لا يطابق ما كُتب")
        return out.absolutePath
    }

    private fun createFileAnswer(fr: Pair<MadeFile?, String>): Answer {
        val f = fr.first ?: return Answer(fr.second, "file")
        if (f.more.isNotEmpty()) {                                                // a project: several files in one folder
            val all = listOf(f) + f.more; val ok = ArrayList<String>(); var err = ""
            for (x in all) { try { ok.add(saveToDownloads(x)) } catch (e: Throwable) { err = e.message ?: e.javaClass.simpleName; break } }
            val folder = f.name.substringBeforeLast('/', "")
            return Answer((if (ok.size == all.size) "✅ أنشأت المشروع فعلا: " + all.size + " ملفات وتأكدت من محتوى كل ملف بعد الكتابة." else "⚠ كتبت " + ok.size + " من " + all.size + " ملفات فقط. " + err) +
                "\nالمجلد: Download/Nuwaa" + (if (folder.isNotEmpty()) "/" + folder else "") + "\n" + ok.joinToString("\n") { "• " + it } + "\nلم أشغّل الكود، جرّبه قبل الاعتماد عليه.", "file")
        }
        return try {
            val where = saveToDownloads(f)
            Answer("✅ أنشأت الملف فعلا وتأكدت من محتواه بعد الكتابة.\nالاسم: " + f.name + "\nالمكان: " + where + "\nالحجم: " + f.bytes.size + " بايت" + (if (f.note.isNotEmpty()) "\n(" + f.note + ")" else "") + (if (f.name.endsWith(".py") || f.name.endsWith(".kt") || f.name.endsWith(".js")) "\nلم أشغّل الكود، جرّبه قبل الاعتماد عليه." else ""), "file")
        } catch (e: Throwable) {
            Answer("❌ ما قدرت أنشئ الملف: " + (e.message ?: e.javaClass.simpleName) + "\nلم يُكتب شيء. يمكنك استعمال ＋ ثم «إنشاء ملف» لاختيار مكان الحفظ بنفسك.", "file")
        }
    }

    // ---------------- the + button: send a file / create a file ----------------
    private fun showPlus() {
        AlertDialog.Builder(this).setItems(arrayOf("📎  إرسال ملف", "📝  إنشاء ملف")) { _, i ->
            if (i == 0) pickFile() else askCreateFile()
        }.show()
    }

    /** What goes into a created file: the text in the input box, else the last reply (the code inside ``` if it has some). */
    private fun contentForFile(): String {
        val typed = input.text.toString().trim()
        if (typed.isNotEmpty()) return typed
        val last = conv?.msgs?.lastOrNull { it.role == "b" }?.text ?: ""
        return if (last.contains("```")) last.substringAfter("```").substringAfter('\n').substringBefore("```").trim('\n') else last
    }

    private fun askCreateFile() {
        val text = contentForFile()
        if (text.isBlank()) { Toast.makeText(this, "اكتب النص في خانة الكتابة أولا، أو اطلب مني كودا ثم اضغط ＋", Toast.LENGTH_LONG).show(); return }
        val name = EditText(this); name.setSingleLine(true); name.setText(if (text.contains("def ") || text.contains("import ")) "nuwaa.py" else "nuwaa.txt")
        AlertDialog.Builder(this).setTitle("اسم الملف").setView(name)
            .setPositiveButton("إنشاء") { _, _ ->
                pendingFile = text; pendingBytes = null
                val n = name.text.toString().trim().ifEmpty { "nuwaa.txt" }
                val i = Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*").putExtra(Intent.EXTRA_TITLE, n)
                try { startActivityForResult(i, REQ_CREATE) } catch (e: Exception) { Toast.makeText(this, "ما لقيت تطبيق ملفات في جوالك", Toast.LENGTH_LONG).show() }
            }.setNegativeButton("إلغاء", null).show()
    }

    private fun writeCreated(uri: Uri) {
        val data = pendingBytes ?: pendingFile.toByteArray(Charsets.UTF_8)
        pendingBytes = null
        thread {
            try {
                contentResolver.openOutputStream(uri)?.use { it.write(data) } ?: throw java.io.IOException("تعذر فتح الملف للكتابة")
                runOnUiThread { Toast.makeText(this, "تم إنشاء الملف", Toast.LENGTH_SHORT).show() }
            } catch (e: Throwable) {
                runOnUiThread { Toast.makeText(this, "تعذر إنشاء الملف: " + (e.message ?: ""), Toast.LENGTH_LONG).show() }
            }
        }
    }

    // ---------------- self-development (a clear button, no codes) ----------------
    private fun buildDevPage() {
        devPage = LinearLayout(this); devPage.orientation = LinearLayout.VERTICAL; devPage.setPadding(dp(16), dp(14), dp(16), dp(10))
        devPage.addView(Ui.label(this, "تطوير النفس", 20f, Ui.DARK, true))
        devPage.addView(Ui.label(this, "اضغط الزر: أراجع كل ما سمعته منك وأتدرب عليه، وأقيس نفسي قبل وبعد. إن تحسنت أحفظ التحسن، وإن ساءت أرجع لما كنت عليه. ما أبدأ إلا بضغطتك.", 14f, Ui.MUTED, false).also { it.setPadding(0, dp(6), 0, dp(12)) })
        val go = Ui.btn(this, "🧠  ابدأ التطوير الآن", Ui.PRIMARY) { runDevelop() }
        go.textSize = 18f
        devPage.addView(go, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        val fileBtn = Ui.btn(this, "📦  ملف المطور", Ui.DARK) { askDevFile() }
        fileBtn.textSize = 16f
        val flp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); flp.setMargins(0, dp(10), 0, 0)
        devPage.addView(fileBtn, flp)
        val sv = ScrollView(this); devReport = Ui.label(this, "", 15f, Ui.DARK, false); devReport.setPadding(0, dp(14), 0, 0); devReport.setTextIsSelectable(true); sv.addView(devReport)
        devPage.addView(sv, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
    }

    // ---------------- raise understanding: training on the phone at a CPU share the user picks ----------------
    private fun buildTrainPage() {
        trainPage = LinearLayout(this); trainPage.orientation = LinearLayout.VERTICAL; trainPage.setPadding(dp(16), dp(14), dp(16), dp(10))
        trainPage.addView(Ui.label(this, "رفع الفهم", 20f, Ui.DARK, true))
        trainPage.addView(Ui.label(this, "أدرّب نفسي على بيانات البرمجة والعربية داخل جوالك، شوي شوي. أنت تحدد كم أستهلك من المعالج، حتى لو الجوال ضعيف أكمل بالتدريج وأحفظ كل تحسن. أقيس نفسي على نص ثابت، وإن ساءت النتيجة أرجع للأفضل.", 14f, Ui.MUTED, false).also { it.setPadding(0, dp(6), 0, dp(12)) })
        pctLabel = Ui.label(this, "الاستهلاك: 40% من نواة معالج واحدة", 16f, Ui.DARK, true)
        trainPage.addView(pctLabel)
        val sk = SeekBar(this); sk.max = 95; sk.progress = 35
        sk.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(s: SeekBar?, p: Int, fromUser: Boolean) { val v = p + 5; trainer().percent = v; pctLabel.text = "الاستهلاك: " + v + "% من نواة معالج واحدة" }
            override fun onStartTrackingTouch(s: SeekBar?) {}
            override fun onStopTrackingTouch(s: SeekBar?) {}
        })
        trainPage.addView(sk, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        val presets = LinearLayout(this); presets.orientation = LinearLayout.HORIZONTAL
        for ((txt, v) in listOf("🔋 توفير 15%" to 15, "⚖ متوازن 40%" to 40, "🔥 قوي 100%" to 100)) {
            val b = Ui.btn(this, txt, Ui.DARK) { sk.progress = v - 5 }
            b.textSize = 13f
            val pl = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f); pl.setMargins(dp(3), dp(8), dp(3), 0); presets.addView(b, pl)
        }
        trainPage.addView(presets)
        val sr = CheckBox(this); sr.text = "مراجعة ذاتية: أختبر نفسي بمهام أعرف جوابها وأتعلم من الصحيح"; sr.isChecked = true; sr.textSize = 14f
        sr.setOnCheckedChangeListener { _, on -> trainer().selfReview = on }
        trainPage.addView(sr)
        trainBtn = Ui.btn(this, "⚡  ابدأ رفع الفهم", Ui.PRIMARY) { toggleTrain() }
        trainBtn.textSize = 18f
        val blp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); blp.setMargins(0, dp(12), 0, 0)
        trainPage.addView(trainBtn, blp)
        val rs = Ui.btn(this, "🔄  إعادة تشغيل التطبيق (يحفظ أفضل حالة أولا)", Ui.DARK) { restartApp() }
        val rlp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); rlp.setMargins(0, dp(8), 0, 0)
        trainPage.addView(rs, rlp)
        val sv = ScrollView(this); trainInfo = Ui.label(this, "", 15f, Ui.DARK, false); trainInfo.setPadding(0, dp(14), 0, 0); sv.addView(trainInfo)
        trainPage.addView(sv, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
    }

    private fun toggleTrain() {
        val t = trainer()
        if (t.running) {
            t.stop(); trainBtn.text = "⚡  ابدأ رفع الفهم"
            window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            trainInfo.text = "أوقفت التدريب وأحفظ الآن أفضل حالة..."
            return
        }
        t.percent = pctLabel.text.toString().filter { it.isDigit() }.toIntOrNull() ?: 40
        window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)       // training stops if the app is closed: keep the screen on while it runs
        trainBtn.text = "⏹  إيقاف (يحفظ الأفضل)"
        t.start { msg -> runOnUiThread { trainInfo.text = msg } }
    }

    // ---------------- discovery: optional, needs internet + the user's own Google API key, and only runs when asked ----------------
    private fun openGrowPage() {
        if (!SecretGrowth.isSet(this)) {
            val input = EditText(this); input.inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD
            AlertDialog.Builder(this).setTitle("حدد رمزا سريا (أول مرة)")
                .setMessage("هذا الرمز يحميك من فتح هذي الصفحة بالغلط لاحقا. لا يُرسل لأي مكان ويُحفظ على جهازك فقط.")
                .setView(input).setPositiveButton("حفظ") { _, _ -> if (input.text.toString().length >= 4) { SecretGrowth.setPin(this, input.text.toString()); showPage(growPage) } }
                .setNegativeButton("إلغاء", null).show()
            return
        }
        val input = EditText(this); input.inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD
        AlertDialog.Builder(this).setTitle("أدخل الرمز السري").setView(input)
            .setPositiveButton("دخول") { _, _ -> if (SecretGrowth.verify(this, input.text.toString())) showPage(growPage) else Toast.makeText(this, "رمز خاطئ", Toast.LENGTH_SHORT).show() }
            .setNegativeButton("إلغاء", null).show()
    }

    private fun buildGrowPage() {
        growPage = LinearLayout(this); growPage.orientation = LinearLayout.VERTICAL; growPage.setPadding(dp(16), dp(14), dp(16), dp(10))
        growPage.addView(Ui.label(this, "⚙ تطوير متقدم", 20f, Ui.DARK, true))
        val heap = Runtime.getRuntime().maxMemory() / 1e6
        growPage.addView(Ui.label(this, "ذاكرة هذا الجوال المتاحة للتطبيق الآن: " + heap.toInt() + " MB (تُقاس كل مرة من جهازك، وتتغير حسب الجهاز والوضع). هذا يحدد أكبر حجم آمن تكبّر له النموذج هنا.", 14f, Ui.MUTED, false).also { it.setPadding(0, dp(6), 0, dp(10)) })
        val m = brain.trainModel()
        val curParams = m?.paramCount() ?: 0
        growPage.addView(Ui.label(this, "الحجم الحالي: " + curParams + " معامل", 15f, Ui.DARK, true))
        val maxP = SecretGrowth.maxSafeParams(this).coerceAtLeast((curParams + 1000).toLong())
        val sizeLabel = Ui.label(this, "", 15f, Ui.DARK, true); growPage.addView(sizeLabel)
        val sizeBar = android.widget.SeekBar(this); sizeBar.max = 100
        fun targetParams(progress: Int): Long = curParams + ((maxP - curParams) * progress / 100.0).toLong()
        sizeBar.setOnSeekBarChangeListener(object : android.widget.SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: android.widget.SeekBar?, p: Int, u: Boolean) { sizeLabel.text = "الهدف: " + targetParams(p) + " معامل (~" + (targetParams(p) * 4 / 1e6).toInt() + " MB)" }
            override fun onStartTrackingTouch(sb: android.widget.SeekBar?) {}
            override fun onStopTrackingTouch(sb: android.widget.SeekBar?) {}
        })
        sizeBar.progress = 0; sizeLabel.text = "الهدف: " + curParams + " معامل (~" + (curParams * 4 / 1e6).toInt() + " MB)"
        growPage.addView(sizeBar)
        growPage.addView(Ui.label(this, "⚠ كرت الشاشة: غير متاح للتدريب على الجوال في هذا التطبيق (المحرك هنا يحسب على المعالج فقط). التحكم الحقيقي بكرت الشاشة متاح فقط عبر «استوديو نواة» على الكمبيوتر (tools/studio.py)، ليس من هنا.", 13f, Ui.MUTED, false).also { it.setPadding(0, dp(12), 0, dp(4)) })
        growPage.addView(Ui.btn(this, "🔼  كبّر النموذج الآن", Ui.PRIMARY) {
            val e = m?.e ?: 64; val h = SecretGrowth.pickHidden(targetParams(sizeBar.progress), maxOf(e, 96), m?.chars?.size ?: 188)
            AlertDialog.Builder(this).setTitle("تأكيد").setMessage("هذا يكبّر النموذج فعلا الآن ويحفظه. ما يرجع صغيرا إلا بإعادة تثبيت التطبيق. يكمل؟")
                .setPositiveButton("كبّر") { _, _ -> growResult.text = brain.growModel(maxOf(e, 96), h) }.setNegativeButton("إلغاء", null).show()
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.topMargin = dp(10) })
        growPage.addView(Ui.label(this, "تدريب النموذج الأكبر يستهلك نفس استهلاك المعالج اللي تختاره في ⚡ رفع الفهم (15/40/100%)، لكن كل خطوة تصير أبطأ بزيادة الحجم.", 13f, Ui.MUTED, false).also { it.setPadding(0, dp(10), 0, dp(4)) })
        val sv = ScrollView(this); growResult = Ui.label(this, "", 15f, Ui.DARK, false); growResult.setPadding(0, dp(10), 0, 0); sv.addView(growResult)
        growPage.addView(sv, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
    }

    private fun buildDiscoverPage() {
        discoverPage = LinearLayout(this); discoverPage.orientation = LinearLayout.VERTICAL; discoverPage.setPadding(dp(16), dp(14), dp(16), dp(10))
        discoverPage.addView(Ui.label(this, "اكتشاف من الإنترنت", 20f, Ui.DARK, true))
        discoverPage.addView(Ui.label(this, "هذه الميزة الوحيدة التي تحتاج إنترنت في كل التطبيق. تبحث في جوجل بمفتاحك الخاص (Google Custom Search، مجانا حتى 100 بحث يوميا)، وما تُشغَّل إلا لما تطلبها بنفسك. النتائج من جوجل مباشرة، وليست من النموذج ولا كلامه.", 14f, Ui.MUTED, false).also { it.setPadding(0, dp(6), 0, dp(12)) })
        val keyIn = EditText(this); keyIn.hint = "API key"; keyIn.isSingleLine = true
        val cxIn = EditText(this); cxIn.hint = "Search engine ID (cx)"; cxIn.isSingleLine = true
        discoverPage.addView(keyIn); discoverPage.addView(cxIn, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.topMargin = dp(8) })
        val saveRow = LinearLayout(this); saveRow.orientation = LinearLayout.HORIZONTAL
        saveRow.addView(Ui.btn(this, "حفظ المفتاح", Ui.DARK) {
            GoogleSearch.setCredentials(this, keyIn.text.toString(), cxIn.text.toString()); keyIn.setText(""); cxIn.setText("")
            discoverResult.text = if (GoogleSearch.configured(this)) "تم الحفظ. اكتب بحثك تحت." else "أدخل المفتاح ومعرّف محرك البحث معا."
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).also { it.topMargin = dp(10); it.rightMargin = dp(6) })
        saveRow.addView(Ui.btn(this, "مسح المفتاح", Ui.DARK) { GoogleSearch.clearCredentials(this); discoverResult.text = "مُسح. هذه الميزة الآن متوقفة." },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).also { it.topMargin = dp(10); it.leftMargin = dp(6) })
        discoverPage.addView(saveRow)
        val qIn = EditText(this); qIn.hint = "ابحث عن..."
        discoverPage.addView(qIn, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.topMargin = dp(14) })
        discoverPage.addView(Ui.btn(this, "🔍  ابحث في جوجل الآن", Ui.PRIMARY) {
            val q = qIn.text.toString().trim(); if (q.isBlank()) return@btn
            discoverResult.text = "… أبحث في جوجل"
            Thread {
                val text = try { GoogleSearch.format(q, GoogleSearch.search(this, q)) } catch (e: Exception) { "تعذّر البحث: " + (e.message ?: e.javaClass.simpleName) }
                runOnUiThread { discoverResult.text = text }
            }.start()
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.topMargin = dp(10) })
        // ---- Gemini teacher: an optional external AI that keeps feeding Nuwaa fresh programming/Arabic examples while ⚡ رفع الفهم is training ----
        discoverPage.addView(Ui.label(this, "معلّم Gemini (اختياري)", 18f, Ui.DARK, true).also { it.setPadding(0, dp(20), 0, dp(4)) })
        discoverPage.addView(Ui.label(this, "يطلب من Gemini (بمفتاحك الخاص) أمثلة برمجة ولغة عربية جديدة باستمرار أثناء التدريب، ويدرّب عليها بنفس حماية التراجع — لكن بلا تحقق بالتشغيل مثل بيانات نواة نفسها، فهو معلّم غير موثَّق بقدر التحقق الذاتي.", 13f, Ui.MUTED, false).also { it.setPadding(0, dp(2), 0, dp(10)) })
        val gKeyIn = EditText(this); gKeyIn.hint = "Gemini API key"; gKeyIn.isSingleLine = true
        val gModelIn = EditText(this); gModelIn.hint = "الموديل (افتراضي: " + GeminiTeacher.DEFAULT_MODEL + ")"; gModelIn.isSingleLine = true
        discoverPage.addView(gKeyIn); discoverPage.addView(gModelIn, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.topMargin = dp(8) })
        val gSaveRow = LinearLayout(this); gSaveRow.orientation = LinearLayout.HORIZONTAL
        val gStatus = Ui.label(this, if (GeminiTeacher.configured(this)) "مفعّل." else "أدخل مفتاحك.", 13f, Ui.MUTED, false)
        gSaveRow.addView(Ui.btn(this, "حفظ مفتاح Gemini", Ui.DARK) {
            GeminiTeacher.setCredentials(this, gKeyIn.text.toString(), gModelIn.text.toString()); gKeyIn.setText(""); gStatus.text = if (GeminiTeacher.configured(this)) "تم الحفظ." else "أدخل المفتاح."
        }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).also { it.topMargin = dp(10); it.rightMargin = dp(6) })
        gSaveRow.addView(Ui.btn(this, "مسح", Ui.DARK) { GeminiTeacher.clearCredentials(this); trainer().teacherOn = false; gStatus.text = "مُسح." },
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).also { it.topMargin = dp(10); it.leftMargin = dp(6) })
        discoverPage.addView(gSaveRow); discoverPage.addView(gStatus)
        val gEnable = CheckBox(this); gEnable.text = "فعّل معلّم Gemini أثناء التدريب"; gEnable.isChecked = false; gEnable.textSize = 14f
        val gRateLabel = Ui.label(this, "المعدل: 5 رسالة/دقيقة", 14f, Ui.DARK, false)
        val gRateBar = android.widget.SeekBar(this); gRateBar.max = 59; gRateBar.progress = 4
        gEnable.setOnCheckedChangeListener { _, on -> trainer().teacherOn = on }
        gRateBar.setOnSeekBarChangeListener(object : android.widget.SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: android.widget.SeekBar?, p: Int, u: Boolean) { val v = p + 1; trainer().teacherPerMinute = v; gRateLabel.text = "المعدل: " + v + " رسالة/دقيقة (بلا حد أقصى مفروض؛ أنت تتحكم، والتكلفة على مفتاحك)" }
            override fun onStartTrackingTouch(sb: android.widget.SeekBar?) {}
            override fun onStopTrackingTouch(sb: android.widget.SeekBar?) {}
        })
        discoverPage.addView(gEnable, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.topMargin = dp(10) })
        discoverPage.addView(gRateLabel); discoverPage.addView(gRateBar)

        val sv = ScrollView(this); discoverResult = Ui.label(this, if (GoogleSearch.configured(this)) "اكتب بحثك فوق." else "أدخل مفتاحك فوق لتفعيل البحث.", 15f, Ui.DARK, false)
        discoverResult.setPadding(0, dp(14), 0, 0); sv.addView(discoverResult)
        discoverPage.addView(sv, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
    }

    override fun onDestroy() { trainerObj?.stop(); super.onDestroy() }

    /** Saves the best trained state, then really restarts the app (new process, the model is loaded again from disk). */
    private fun restartApp() {
        trainerObj?.stopAndWait(5000)
        val i = packageManager.getLaunchIntentForPackage(packageName)
        if (i != null) { i.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_CLEAR_TASK); startActivity(i) }
        finishAffinity()
        Runtime.getRuntime().exit(0)
    }

    private fun runDevelop() {
        devReport.text = "أراجع ما سمعته وأتدرب... (قد تأخذ دقيقة)"
        thread {
            val r = try { brain.develop() } catch (e: Throwable) { "تعذر التطوير: " + (e.message ?: e.javaClass.simpleName) }
            runOnUiThread { devReport.text = r }
        }
    }

    /** The developer file: weights + long-term memory + report in one zip. It is saved only where the user picks, through the system file picker. */
    private fun askDevFile() {
        devReport.text = "أجهّز ملف المطور..."
        thread {
            try {
                val bytes = brain.devFile()
                runOnUiThread {
                    pendingBytes = bytes
                    val i = Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/zip").putExtra(Intent.EXTRA_TITLE, "nuwaa-dev-" + (System.currentTimeMillis() / 1000) + ".zip")
                    try { startActivityForResult(i, REQ_CREATE); devReport.text = "اختر مكان حفظ الملف، ثم أرسله لمن يفحصه." } catch (e: Exception) { devReport.text = "ما لقيت تطبيق ملفات في جوالك" }
                }
            } catch (e: Throwable) { runOnUiThread { devReport.text = "تعذر تجهيز الملف: " + (e.message ?: e.javaClass.simpleName) } }
        }
    }

    // ---------------- attach file (read only) ----------------
    @Suppress("DEPRECATION")
    private fun pickFile() {
        val i = Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*")
        try { startActivityForResult(i, REQ_PICK) } catch (e: Exception) { Toast.makeText(this, "ما لقيت تطبيق ملفات في جوالك", Toast.LENGTH_LONG).show() }
    }

    private fun loadAttachment(uri: Uri) {
        thread {
            try {
                var name = "ملف"; var size = -1L
                contentResolver.query(uri, null, null, null, null)?.use { cur ->
                    if (cur.moveToFirst()) {
                        val ni = cur.getColumnIndex(OpenableColumns.DISPLAY_NAME); val si = cur.getColumnIndex(OpenableColumns.SIZE)
                        if (ni >= 0) name = cur.getString(ni) ?: name
                        if (si >= 0 && !cur.isNull(si)) size = cur.getLong(si)
                    }
                }
                val buf = java.io.ByteArrayOutputStream()
                var total = 0L; var truncated = false
                contentResolver.openInputStream(uri)?.use { ins ->
                    val chunk = ByteArray(16384)
                    while (true) {
                        val k = ins.read(chunk); if (k < 0) break
                        total += k
                        if (buf.size() + k > MAX_READ) { buf.write(chunk, 0, MAX_READ - buf.size()); truncated = true; break }
                        buf.write(chunk, 0, k)
                    }
                } ?: throw java.io.IOException("تعذر فتح الملف")
                val real = if (size >= 0) size else total
                val att = Attached(name, real, buf.toByteArray(), truncated)
                runOnUiThread {
                    attached = att
                    attachLabel.text = "📎 " + name + " — اكتب سؤالك عنه أو اضغط إرسال"
                    attachBar.visibility = View.VISIBLE
                }
            } catch (e: Throwable) {
                runOnUiThread { Toast.makeText(this, "تعذر قراءة الملف: " + (e.message ?: ""), Toast.LENGTH_LONG).show() }
            }
        }
    }

    private fun addMsg(c: Conv, role: String, text: String) {
        c.msgs.add(Msg(role, text)); c.updated = System.currentTimeMillis()
        if (role == "u" && c.title == "محادثة جديدة") { c.title = text.take(30); titleView.text = c.title }
        store.save(c); bubble(text, role == "u")
    }

    // ---------------- history ----------------
    private fun buildHistPage() {
        histPage = LinearLayout(this); histPage.orientation = LinearLayout.VERTICAL
        histPage.addView(Ui.label(this, "المحادثات", 18f, Ui.DARK, true).also { it.setPadding(dp(16), dp(12), dp(16), dp(4)) })
        val sv = ScrollView(this); histList = LinearLayout(this); histList.orientation = LinearLayout.VERTICAL; sv.addView(histList)
        histPage.addView(sv, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
    }

    private fun refreshHistory() {
        histList.removeAllViews()
        val all = store.list().filter { it.msgs.isNotEmpty() }
        if (all.isEmpty()) { histList.addView(Ui.label(this, "ما فيه محادثات محفوظة بعد.", 15f, Ui.MUTED, false).also { it.setPadding(dp(16), dp(16), dp(16), 0) }); return }
        for (c in all) {
            val row = LinearLayout(this); row.orientation = LinearLayout.HORIZONTAL; row.gravity = Gravity.CENTER_VERTICAL
            row.background = Ui.bg(this, Color.WHITE, 14); row.setPadding(dp(14), dp(12), dp(8), dp(12))
            val t = Ui.label(this, c.title + "\n" + c.msgs.size + " رسالة", 15f, Ui.DARK, false)
            val del = TextView(this); del.text = "🗑"; del.textSize = 20f; del.setPadding(dp(12), dp(4), dp(12), dp(4))
            row.setOnClickListener {
                val cur = conv
                if (cur != null && cur.id != c.id) { brain.endConversation(cur.id); thread { brain.resume(c.id, c.msgs.toList()) } }
                conv = c; renderConv(); showPage(chatPage); scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
            }
            del.setOnClickListener { store.delete(c.id); brain.endConversation(c.id); if (conv?.id == c.id) { conv = store.create(); renderConv() }; refreshHistory() }
            row.addView(t, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)); row.addView(del)
            val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); lp.setMargins(dp(12), dp(5), dp(12), dp(5))
            histList.addView(row, lp)
        }
    }

    // ---------------- screen share ----------------
    private fun buildScreenPage() {
        screenPage = ScrollView(this)
        val col = LinearLayout(this); col.orientation = LinearLayout.VERTICAL; col.setPadding(dp(14), dp(12), dp(14), dp(20))
        col.addView(Ui.label(this, "مشاركة الشاشة", 18f, Ui.DARK, true))
        col.addView(Ui.label(this, "أشاهد إطارا واحدا كل ثانية، وأقرأ النص الظاهر على الشاشة (بعد تفعيل قارئ الشاشة) وأنصحك بخطوة تالية. لا أضغط ولا أكتب بدلا عنك. لا أفهم الصور، فقط النص وتغيّر الشاشة.", 13f, Ui.MUTED, false).also { it.setPadding(0, dp(4), 0, dp(10)) })
        goalInput = EditText(this); goalInput.hint = "ماذا تريد أن تنجز؟ (مثال: كيف ارفع مشروعي على github)"
        goalInput.background = Ui.bg(this, Color.WHITE, 14); goalInput.setPadding(dp(14), dp(10), dp(14), dp(10))
        col.addView(goalInput)
        val b1 = Ui.btn(this, "تفعيل قارئ الشاشة (مرة واحدة)", Ui.DARK) { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)); Toast.makeText(this, "اختر «نواة» ثم فعّله", Toast.LENGTH_LONG).show() }
        shareBtn = Ui.btn(this, "ابدأ المشاركة", Ui.PRIMARY) { toggleShare() }
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); lp.setMargins(0, dp(10), 0, 0)
        col.addView(b1, lp); col.addView(shareBtn, lp)
        shareInfo = Ui.label(this, "", 13f, Ui.MUTED, false).also { it.setPadding(0, dp(10), 0, dp(4)) }
        col.addView(shareInfo)
        preview = ImageView(this); preview.adjustViewBounds = true; preview.maxHeight = dp(260); preview.background = Ui.bg(this, Color.parseColor("#D9E1E7"), 10)
        col.addView(preview, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(200)))
        adviceView = Ui.label(this, "النصيحة تظهر هنا.", 15f, Ui.DARK, false)
        adviceView.background = Ui.bg(this, Color.WHITE, 14); adviceView.setPadding(dp(14), dp(12), dp(14), dp(12)); adviceView.setTextIsSelectable(true)
        val lp2 = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT); lp2.setMargins(0, dp(10), 0, 0)
        col.addView(adviceView, lp2)
        screenPage.addView(col)
    }

    private fun refreshShareUi() {
        shareBtn.text = if (ScreenShareService.running) "إيقاف المشاركة" else "ابدأ المشاركة"
        shareInfo.text = if (ScreenReader.enabled()) "قارئ الشاشة: مفعّل ✓" else "قارئ الشاشة: غير مفعّل (بدونه أرى تغيّر الشاشة فقط)"
    }

    private fun toggleShare() {
        if (ScreenShareService.running) { startService(Intent(this, ScreenShareService::class.java).setAction(ScreenShareService.ACTION_STOP)); return }
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIF); return
        }
        launchCapture()
    }

    @Suppress("DEPRECATION")
    private fun launchCapture() {
        val mpm = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        startActivityForResult(mpm.createScreenCaptureIntent(), REQ_CAPTURE)
    }

    @Suppress("DEPRECATION")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_NOTIF) launchCapture()    // the service still works if notifications are refused, only the tip is hidden
    }

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_PICK) {
            val u = data?.data
            if (resultCode == RESULT_OK && u != null) loadAttachment(u)
            return
        }
        if (requestCode == REQ_CREATE) {
            val u = data?.data
            if (resultCode == RESULT_OK && u != null) writeCreated(u)
            return
        }
        if (requestCode != REQ_CAPTURE) return
        if (resultCode != RESULT_OK || data == null) { Toast.makeText(this, "لم تُمنح صلاحية مشاركة الشاشة", Toast.LENGTH_SHORT).show(); return }
        ScreenShareService.goal = goalInput.text.toString().trim()
        ScreenShareService.frameListener = { bmp: Bitmap, change: Double ->
            runOnUiThread { preview.setImageBitmap(bmp); shareInfo.text = "إطار كل ثانية · تغيّر الشاشة: " + (change * 100).toInt() + "%" + (if (ScreenReader.enabled()) " · قارئ الشاشة ✓" else " · قارئ الشاشة غير مفعّل") }
        }
        ScreenShareService.adviceListener = { s: String -> runOnUiThread { adviceView.text = s } }
        ScreenShareService.stopListener = { runOnUiThread { refreshShareUi(); shareInfo.text = "توقفت المشاركة." } }
        val i = Intent(this, ScreenShareService::class.java).putExtra("code", resultCode).putExtra("data", data)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
        shareBtn.text = "إيقاف المشاركة"
        Toast.makeText(this, "بدأت المشاركة. افتح التطبيق الذي تريد المساعدة فيه.", Toast.LENGTH_LONG).show()
    }

    override fun onResume() { super.onResume(); if (::shareBtn.isInitialized) refreshShareUi() }

    // ---------------- code writing ----------------
    private fun buildCodePage() {
        codePage = LinearLayout(this); codePage.orientation = LinearLayout.VERTICAL; codePage.setPadding(dp(12), dp(10), dp(12), dp(10))
        codePage.addView(Ui.label(this, "كتابة الأكواد", 18f, Ui.DARK, true))
        codeIdea = EditText(this); codeIdea.hint = "صف ما تريد: (مثال: حلقة for في بايثون)"
        codeIdea.background = Ui.bg(this, Color.WHITE, 14); codeIdea.setPadding(dp(14), dp(10), dp(14), dp(10)); codeIdea.setSingleLine(true)
        codePage.addView(codeIdea, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.setMargins(0, dp(8), 0, dp(6)) })
        val row = LinearLayout(this); row.orientation = LinearLayout.HORIZONTAL
        val suggest = Ui.btn(this, "اقترح كودا", Ui.PRIMARY) { suggestCode() }
        val copy = Ui.btn(this, "نسخ", Ui.DARK) { copyText(editor.text.toString()); Toast.makeText(this, "تم النسخ", Toast.LENGTH_SHORT).show() }
        val share = Ui.btn(this, "مشاركة", Ui.DARK) { shareCode() }
        val clear = Ui.btn(this, "مسح", Color.parseColor("#8A3B3B")) { editor.setText("") }
        for (v in listOf(suggest, copy, share, clear)) row.addView(v, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).also { it.setMargins(dp(3), 0, dp(3), 0) })
        codePage.addView(row)
        val strip = Ui.btn(this, "🔢  إزالة الأرقام الجانبية", Ui.PRIMARY) { stripNumbers() }
        codePage.addView(strip, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).also { it.setMargins(dp(3), dp(8), dp(3), 0) })
        editor = EditText(this); editor.typeface = Typeface.MONOSPACE; editor.textSize = 13f; editor.setTextColor(Color.parseColor("#D7E3EA")); editor.setHintTextColor(Color.parseColor("#6B7F8C"))
        editor.hint = "# اكتب كودك هنا أو اضغط «اقترح كودا»"; editor.gravity = Gravity.TOP or Gravity.START; editor.layoutDirection = View.LAYOUT_DIRECTION_LTR; editor.textDirection = View.TEXT_DIRECTION_LTR
        editor.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS or InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
        editor.background = Ui.bg(this, Ui.CODE_BG, 12); editor.setPadding(dp(12), dp(12), dp(12), dp(12))
        codePage.addView(editor, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f).also { it.setMargins(0, dp(8), 0, 0) })
    }

    private fun suggestCode() {
        val q = codeIdea.text.toString().trim()
        if (q.isEmpty()) { Toast.makeText(this, "اكتب وصفا أولا", Toast.LENGTH_SHORT).show(); return }
        val hit = brain.kb.search(q, 6).firstOrNull { h -> h.score >= Kb.LOW && h.item.a.contains("```") }
        if (hit == null) { Toast.makeText(this, "ما عندي كود جاهز لهذا الوصف. جرّب وصفا أبسط، أو علّمني في المحادثة.", Toast.LENGTH_LONG).show(); return }
        val code = hit.item.a.substringAfter("```").substringAfter('\n').substringBefore("```").trim('\n')
        val mark = when (hit.item.v) { 2 -> "# ✓ شُغِّل واختُبر ناتجه"; 1 -> "# ✓ شُغِّل بدون أخطاء"; 0 -> "# ✓ فُحصت صياغته فقط"; else -> "# ⚠ لم يُشغَّل هنا، جرّبه" }
        val cur = editor.text.toString()
        editor.setText((if (cur.isBlank()) "" else cur.trimEnd() + "\n\n") + mark + "\n" + code)
    }

    private fun stripNumbers() {
        val t = editor.text.toString()
        if (t.isBlank()) { Toast.makeText(this, "الصق الكود أو اكتبه أولا", Toast.LENGTH_SHORT).show(); return }
        val r = LineNumbers.strip(t)
        if (r.second == 0) { Toast.makeText(this, "ما لقيت أرقام جانبية واضحة في الكود", Toast.LENGTH_LONG).show(); return }
        editor.setText(r.first)
        Toast.makeText(this, "أزلت الأرقام من " + r.second + " سطر", Toast.LENGTH_SHORT).show()
    }

    private fun shareCode() {
        val t = editor.text.toString()
        if (t.isBlank()) return
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, t), "مشاركة الكود"))
    }

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        if (pages.childCount > 0 && pages.getChildAt(0) !== chatPage) showPage(chatPage) else super.onBackPressed()
    }
}
