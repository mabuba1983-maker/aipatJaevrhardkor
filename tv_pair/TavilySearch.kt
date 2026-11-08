package ai.nuwaa

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Tavily web search client.
 *
 * NOTE: The API key is embedded here at the owner's explicit request.
 * Anyone who can read this source or decompile the APK can extract it.
 */
object TavilySearch {
    private const val API_KEY = "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"
    private const val ENDPOINT = "https://api.tavily.com/search"

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(35, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .build()

    /**
     * Runs a web search and returns a compact Arabic-friendly text summary
     * containing Tavily's answer and source snippets.
     */
    @JvmStatic
    fun search(query: String, maxResults: Int = 5): String {
        require(query.isNotBlank()) { "Search query is empty" }
        val payload = JSONObject()
            .put("api_key", API_KEY)
            .put("query", query)
            .put("search_depth", "basic")
            .put("max_results", maxResults.coerceIn(1, 8))
            .put("include_answer", true)
            .put("include_raw_content", false)

        val body = payload.toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder()
            .url(ENDPOINT)
            .post(body)
            .header("Accept", "application/json")
            .build()

        client.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IllegalStateException("Tavily HTTP ${response.code}: ${raw.take(500)}")
            }
            val json = JSONObject(raw)
            val out = StringBuilder()
            val answer = json.optString("answer")
            if (answer.isNotBlank()) out.append("خلاصة البحث: ").append(answer).append("\n\n")

            val results = json.optJSONArray("results")
            if (results != null) {
                for (i in 0 until results.length()) {
                    val item = results.optJSONObject(i) ?: continue
                    val title = item.optString("title")
                    val url = item.optString("url")
                    val snippet = item.optString("content")
                    if (title.isBlank() && snippet.isBlank()) continue
                    out.append("• ").append(title).append("\n")
                    if (snippet.isNotBlank()) out.append(snippet).append("\n")
                    if (url.isNotBlank()) out.append(url).append("\n")
                    out.append("\n")
                }
            }
            return out.toString().trim().ifBlank { "لم يُعثر على نتائج مفيدة." }
        }
    }
}
