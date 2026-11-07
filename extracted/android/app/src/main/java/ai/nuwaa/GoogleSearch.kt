package ai.nuwaa

import android.content.Context
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** Optional: lets the user search Google from inside the chat, so Nuwaa can "go find out" instead of guessing.
 *  HONEST LIMITS, by necessity, not by choice:
 *   - This NEEDS the internet. Nuwaa's core promise (works with no internet, no account, no API key) does not apply to this one feature.
 *   - It needs the USER'S OWN Google Custom Search API key and Search Engine ID (free tier: 100 queries/day). No key ships with the app, and none
 *     is hidden anywhere in this code — shipping a real key inside an APK means anyone who decompiles it can steal and abuse it.
 *   - It only runs when the user explicitly asks for it (a search button, never automatically), and results are clearly labelled as coming from
 *     Google, not from the model: Nuwaa does not pretend search results are its own knowledge.
 *   - The model is never asked to write or guess a query that gets silently sent anywhere; the user's own typed text is what gets searched. */
object GoogleSearch {
    private const val PREFS = "nuwaa_google"
    private const val KEY_API = "api_key"
    private const val KEY_CX = "cx"

    fun configured(ctx: Context): Boolean {
        val p = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return !p.getString(KEY_API, "").isNullOrBlank() && !p.getString(KEY_CX, "").isNullOrBlank()
    }

    fun setCredentials(ctx: Context, apiKey: String, cx: String) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_API, apiKey.trim()).putString(KEY_CX, cx.trim()).apply()
    }

    fun clearCredentials(ctx: Context) { ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply() }

    class Result(val title: String, val snippet: String, val link: String)

    /** Runs on the CALLING thread: callers must invoke it off the UI thread (a background Thread), exactly like Nlm.reply. Throws on any
     *  network or API error; callers show that message to the user rather than silently failing. */
    fun search(ctx: Context, query: String, n: Int = 5): List<Result> {
        if (!configured(ctx)) throw IllegalStateException("ابحث يحتاج مفتاح Google Custom Search الخاص بك أولا (القائمة ← اكتشاف من الإنترنت).")
        val p = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val key = p.getString(KEY_API, "")!!; val cx = p.getString(KEY_CX, "")!!
        val url = "https://www.googleapis.com/customsearch/v1?key=" + URLEncoder.encode(key, "UTF-8") +
            "&cx=" + URLEncoder.encode(cx, "UTF-8") + "&num=" + n.coerceIn(1, 10) + "&q=" + URLEncoder.encode(query, "UTF-8")
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 10000; conn.readTimeout = 10000
        try {
            val code = conn.responseCode
            val body = (if (code in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader(Charsets.UTF_8)?.readText() ?: ""
            if (code !in 200..299) {
                val msg = try { org.json.JSONObject(body).optJSONObject("error")?.optString("message") } catch (e: Exception) { null }
                throw IllegalStateException("خطأ من جوجل (" + code + "): " + (msg ?: body.take(200)))
            }
            val items = org.json.JSONObject(body).optJSONArray("items") ?: return emptyList()
            return (0 until items.length()).map { i -> val o = items.getJSONObject(i); Result(o.optString("title"), o.optString("snippet"), o.optString("link")) }
        } finally { conn.disconnect() }
    }

    /** Formats results for the chat: clearly NOT the model's own words, with sources so the user can verify. Nuwaa does not read or act on the
     *  linked pages itself — only titles and the short snippets Google already returned are shown. */
    fun format(query: String, results: List<Result>): String {
        if (results.isEmpty()) return "🔍 نتائج بحث جوجل (من الإنترنت، ليست من النموذج):\nما وجدت نتائج لـ«" + query + "»."
        val sb = StringBuilder("🔍 نتائج بحث جوجل عن «" + query + "» (من الإنترنت، ليست من النموذج):\n")
        for ((i, r) in results.withIndex()) sb.append("\n").append(i + 1).append(") ").append(r.title).append("\n").append(r.snippet).append("\n").append(r.link).append("\n")
        return sb.toString().trim()
    }
}
