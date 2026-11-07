package ai.nuwaa

import android.content.Context
import java.net.HttpURLConnection
import java.net.URL

/** Optional: an external teacher model (Google Gemini) that keeps feeding Nuwaa small, fresh programming/Arabic examples, which are mixed into
 *  training under the SAME regression-rollback safety Trainer.kt already has (nothing here bypasses it).
 *  HONEST LIMITS:
 *   - Needs the internet and the user's OWN Gemini API key. No key ships with the app or is hidden anywhere in this code.
 *   - Default model is `gemini-3.5-flash-lite` (the GA, cost-optimized model the user asked for, confirmed via Google's own docs — not guessed).
 *     An advanced field lets the user type a different exact model id instead if they ever want another one.
 *   - Gemini's answers are NOT run or checked the way Nuwaa's own training data is (every example elsewhere in this project is executed before
 *     it is trusted) — a phone cannot run arbitrary Python safely. They are only scope-filtered (Scope.inScope) and length-checked, then trained
 *     under the existing rollback-if-it-gets-worse protection. Treat it as a noisy teacher, not a verified one.
 *   - This costs the user's own Gemini quota/money on every call. There is a rate slider (messages per minute) with no server-side cap here;
 *     the user sets it and owns the cost. */
object GeminiTeacher {
    private const val PREFS = "nuwaa_gemini"
    private const val KEY_API = "api_key"
    private const val KEY_MODEL = "model"
    const val DEFAULT_MODEL = "gemini-3.5-flash-lite"

    fun configured(ctx: Context): Boolean = !apiKey(ctx).isNullOrBlank()
    fun apiKey(ctx: Context): String? = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_API, null)
    fun model(ctx: Context): String = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_MODEL, null)?.takeIf { it.isNotBlank() } ?: DEFAULT_MODEL

    fun setCredentials(ctx: Context, key: String, model: String) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_API, key.trim()).putString(KEY_MODEL, model.trim()).apply()
    }
    fun clearCredentials(ctx: Context) { ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply() }

    private val TOPICS = listOf(
        "سؤال قصير عن بايثون مع الجواب (أقل من 40 كلمة)", "خطأ شائع في كود بايثون وتصحيحه", "قاعدة نحو أو إملاء عربية مع مثال",
        "ترجمة جملة برمجية قصيرة من الإنجليزية للعربية", "شرح مصطلح برمجي بجملة أو جملتين بالعربي")

    /** Asks Gemini for ONE short teaching example and returns (question, answer) in Nuwaa's own "س:.. / ج:.." training shape, or null if the
     *  call failed, the reply could not be parsed, or it fell outside Nuwaa's specialization (Scope.inScope — applied here too, so a teacher
     *  model cannot smuggle in off-topic material any more than the user's own messages can). Runs on the CALLING thread: call off the UI thread. */
    fun fetchExample(ctx: Context, rnd: java.util.Random = java.util.Random()): Pair<String, String>? {
        val key = apiKey(ctx) ?: return null
        val topic = TOPICS[rnd.nextInt(TOPICS.size)]
        val prompt = "اكتب $topic، تخصصي البرمجة واللغة العربية والإنجليزية فقط. أجب بصيغة JSON فقط بلا أي نص آخر: " +
            "{\"سؤال\": \"...\", \"جواب\": \"...\"} والجواب لا يتجاوز 400 حرف."
        val body = org.json.JSONObject().put("contents", org.json.JSONArray().put(
            org.json.JSONObject().put("parts", org.json.JSONArray().put(org.json.JSONObject().put("text", prompt)))))
        val url = URL("https://generativelanguage.googleapis.com/v1beta/models/" + model(ctx) + ":generateContent")
        val conn = url.openConnection() as HttpURLConnection
        conn.requestMethod = "POST"; conn.setRequestProperty("Content-Type", "application/json"); conn.setRequestProperty("x-goog-api-key", key)
        conn.doOutput = true; conn.connectTimeout = 15000; conn.readTimeout = 20000
        try {
            conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            val text = (if (code in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader(Charsets.UTF_8)?.readText() ?: return null
            if (code !in 200..299) return null
            val root = org.json.JSONObject(text)
            val parts = root.optJSONArray("candidates")?.optJSONObject(0)?.optJSONObject("content")?.optJSONArray("parts") ?: return null
            var raw = parts.optJSONObject(0)?.optString("text") ?: return null
            raw = raw.trim().removePrefix("```json").removePrefix("```").removeSuffix("```").trim()
            val obj = try { org.json.JSONObject(raw) } catch (e: Exception) { return null }
            val q = (obj.optString("سؤال").ifBlank { obj.optString("question") }).trim()
            val a = (obj.optString("جواب").ifBlank { obj.optString("answer") }).trim()
            if (q.isBlank() || a.isBlank() || q.length > 300 || a.length > 500) return null
            if (!Scope.inScope(q)) return null                      // the teacher stays inside the same specialization as everything else
            return Pair(q, a)
        } catch (e: Exception) { return null } finally { conn.disconnect() }
    }
}
