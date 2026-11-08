package ai.nuwaa

import android.content.Context
import android.media.MediaRouter

/** Detects the SAME "Cast" the user already uses from Android Settings > Connected devices > Cast
 *  (or the quick-settings "Smart View"/"Screen cast" tile): this is Android's built-in wireless-display
 *  route, not the paid/registered Google Cast developer SDK. No new Gradle dependency, no API key,
 *  no Google account — android.media.MediaRouter has shipped in every Android version since API 16.
 *
 *  What this gives you: the exact TV name once the user picks it from Settings, and a live flag for
 *  "a TV is connected right now" that other code (e.g. ScreenShareService, MainActivity) can read and
 *  use as a signal/path — e.g. to automatically favour a TV-friendly layout while mirroring is active.
 *
 *  What this does NOT do: it does not open the Cast picker itself (Settings already has that), and it
 *  does not send anything to the TV beyond what system mirroring already mirrors — the app's own screen.
 *  If you later want the APP to open the picker itself (instead of going through Settings) and/or send
 *  specific content to the TV instead of mirroring the whole screen, that needs the real Google Cast SDK
 *  (androidx.mediarouter + com.google.android.gms:play-services-cast-framework). That IS also free — no
 *  payment — but it is a bigger, separate addition (new Gradle deps, a CastOptionsProvider, a receiver
 *  app id). Say the word if you want that version instead of/alongside this one. */
object CastManager {
    @Volatile var connectedDisplayName: String? = null
        private set
    @Volatile var isConnected: Boolean = false
        private set

    private var router: MediaRouter? = null
    private var listener: ((connected: Boolean, name: String?) -> Unit)? = null

    private val callback = object : MediaRouter.SimpleCallback() {
        override fun onRouteSelected(r: MediaRouter, type: Int, info: MediaRouter.RouteInfo) {
            update(r)
        }
        override fun onRouteUnselected(r: MediaRouter, type: Int, info: MediaRouter.RouteInfo) {
            update(r)
        }
        override fun onRouteChanged(r: MediaRouter, info: MediaRouter.RouteInfo) {
            update(r)
        }
    }

    /** Call once, e.g. from MainActivity.onCreate or onResume. onChange is optional UI hook. */
    fun start(context: Context, onChange: ((connected: Boolean, name: String?) -> Unit)? = null) {
        listener = onChange
        val r = context.applicationContext.getSystemService(Context.MEDIA_ROUTER_SERVICE) as? MediaRouter ?: return
        router = r
        @Suppress("DEPRECATION")
        r.addCallback(
            MediaRouter.ROUTE_TYPE_LIVE_VIDEO or MediaRouter.ROUTE_TYPE_LIVE_AUDIO,
            callback
        )
        update(r)   // pick up a route that was already selected before start() was called
    }

    fun stop() {
        router?.let {
            @Suppress("DEPRECATION")
            it.removeCallback(callback)
        }
        router = null
        listener = null
    }

    @Suppress("DEPRECATION")
    private fun update(r: MediaRouter) {
        val selected = r.getSelectedRoute(MediaRouter.ROUTE_TYPE_LIVE_VIDEO)
        val isDefault = selected == null || selected == r.defaultRoute
        isConnected = !isDefault
        connectedDisplayName = if (isDefault) null else selected?.name?.toString()
        listener?.invoke(isConnected, connectedDisplayName)
    }
}
