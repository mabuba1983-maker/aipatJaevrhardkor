package ai.nuwaa

import okhttp3.*
import okio.ByteString
import org.json.JSONObject

/** The phone is the "controller" (same role/protocol as server.ts already uses for the game):
 *  it connects to the pairing server with the code shown on the TV website, and from then on just
 *  SENDS — the TV is a dumb display that receives controller_command messages and renders them.
 *  All real work (Brain.answer, file creation) still happens on the phone; the TV never runs the model.
 */
object TvLink {
    @Volatile var connected: Boolean = false
        private set
    @Volatile var tvName: String? = null
        private set

    private var ws: WebSocket? = null
    private val client = OkHttpClient()

    /** onTvText: called when someone TYPES ON THE TV ITSELF and it reaches the phone (needs the
     *  server.ts "tv_input" relay patch in the README — without it, nothing ever calls this). */
    fun connect(serverUrl: String, code: String, onConnected: (String) -> Unit, onError: (String) -> Unit,
                onDisconnected: () -> Unit, onTvText: (String) -> Unit = {}) {
        val req = Request.Builder().url(serverUrl).build()
        ws = client.newWebSocket(req, object : WebSocketListener() {
            override fun onOpen(w: WebSocket, response: Response) {
                val msg = JSONObject().put("type", "connect_controller").put("code", code).put("controllerName", "جوال نواة")
                w.send(msg.toString())
            }
            override fun onMessage(w: WebSocket, text: String) {
                try {
                    val data = JSONObject(text)
                    when (data.optString("type")) {
                        "controller_connected" -> { connected = true; tvName = data.optString("tvName"); onConnected(tvName ?: "") }
                        "error" -> onError(data.optString("message", "خطأ غير معروف"))
                        "tv_disconnected" -> { connected = false; onDisconnected() }
                        "tv_command" -> {
                            val cmd = data.optJSONObject("command")
                            if (cmd != null && cmd.optString("action") == "chat_text") onTvText(cmd.optString("text"))
                        }
                    }
                } catch (e: Exception) { /* malformed frame from the server: ignore, don't crash the app over it */ }
            }
            override fun onFailure(w: WebSocket, t: Throwable, response: Response?) {
                connected = false; onError(t.message ?: "فشل الاتصال")
            }
            override fun onClosed(w: WebSocket, code: Int, reason: String) { connected = false; onDisconnected() }
        })
    }

    fun disconnect() { ws?.close(1000, "bye"); ws = null; connected = false }

    private fun send(action: String, extra: Map<String, String>) {
        val w = ws ?: return
        if (!connected) return
        val cmd = JSONObject(); cmd.put("action", action); for ((k, v) in extra) cmd.put(k, v)
        val msg = JSONObject().put("type", "controller_input").put("command", cmd)
        w.send(msg.toString())
    }

    /** Call right after a chat exchange finishes (onSend() in MainActivity). */
    fun sendChat(userText: String, botReply: String) =
        send("chat", mapOf("user" to userText, "bot" to botReply))

    /** Call for each live progress line while the model is "thinking" / writing a file
     *  (e.g. from inside replyThink's retry loop, or wherever Effort/plan.tries progress is visible). */
    fun sendThinking(line: String) =
        send("thinking", mapOf("line" to line))

    /** Call once a file is actually written (createFileAnswer in MainActivity).
     *  runnable = true for .html/.js/.css (the TV can preview it live in an iframe, no server needed). */
    fun sendFileDone(name: String, content: String, runnable: Boolean) =
        send("file_done", mapOf("name" to name, "content" to content, "runnable" to runnable.toString()))
}
