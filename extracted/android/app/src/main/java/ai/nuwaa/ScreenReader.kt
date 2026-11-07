package ai.nuwaa

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/** Reads the visible TEXT of the foreground app (labels, buttons, messages). It never clicks or types anything. */
class ScreenReader : AccessibilityService() {
    companion object {
        @Volatile var instance: ScreenReader? = null
        fun enabled(): Boolean = instance != null
        fun readText(): String { val s = instance ?: return ""; return s.collect() }
    }

    override fun onServiceConnected() { instance = this }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}
    override fun onUnbind(intent: Intent?): Boolean { instance = null; return super.onUnbind(intent) }

    private fun collect(): String {
        val root = rootInActiveWindow ?: return ""
        if (root.packageName?.toString() == packageName) return ""   // do not read our own screen
        val sb = StringBuilder()
        fun walk(n: AccessibilityNodeInfo?, depth: Int) {
            if (n == null || depth > 25 || sb.length > 4000) return
            val t: String? = n.text?.toString() ?: n.contentDescription?.toString()
            if (!t.isNullOrBlank()) sb.append(t.trim()).append('\n')
            for (i in 0 until n.childCount) walk(n.getChild(i), depth + 1)
        }
        walk(root, 0)
        return sb.toString()
    }
}
