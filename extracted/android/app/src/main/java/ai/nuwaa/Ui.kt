package ai.nuwaa

import android.content.Context
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.widget.TextView

object Ui {
    val PRIMARY: Int = Color.parseColor("#0E7C86")
    val DARK: Int = Color.parseColor("#0B1F2A")
    val BG: Int = Color.parseColor("#F3F6F8")
    val CODE_BG: Int = Color.parseColor("#14202B")
    val MUTED: Int = Color.parseColor("#5B6B78")

    fun dp(c: Context, v: Int): Int = (v * c.resources.displayMetrics.density + 0.5f).toInt()

    fun bg(c: Context, color: Int, radiusDp: Int): GradientDrawable {
        val g = GradientDrawable()
        g.setColor(color)
        g.cornerRadius = dp(c, radiusDp).toFloat()
        return g
    }

    fun btn(c: Context, text: String, color: Int, onClick: () -> Unit): TextView {
        val t = TextView(c)
        t.text = text
        t.setTextColor(Color.WHITE)
        t.textSize = 15f
        t.gravity = Gravity.CENTER
        t.setPadding(dp(c, 16), dp(c, 10), dp(c, 16), dp(c, 10))
        t.background = bg(c, color, 20)
        t.setOnClickListener { onClick() }
        return t
    }

    fun label(c: Context, text: String, size: Float, color: Int, bold: Boolean): TextView {
        val t = TextView(c)
        t.text = text
        t.textSize = size
        t.setTextColor(color)
        if (bold) t.setTypeface(t.typeface, android.graphics.Typeface.BOLD)
        return t
    }
}
