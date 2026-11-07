package ai.nuwaa

/** The model's self-review: tasks whose right answer the APP knows exactly (a file with a given name and given lines), so no Python is needed on the phone.
 *  The model answers each one with memory off; only an answer with the asked file name and EXACTLY the asked lines counts. The ones that pass become extra
 *  training text (the model learns from what it got right, in its own words). The ones that fail teach nothing wrong. */
object SelfCheck {
    private val items = listOf("خبز", "حليب", "بيض", "تمر", "قهوة", "شاي", "رز", "جبن", "عسل", "ماء", "تفاح", "موز", "لبن", "زيت", "ملح", "سكر")
    class Task(val ask: String, val name: String, val body: String)

    fun makeTasks(n: Int, rnd: java.util.Random): List<Task> {
        val out = ArrayList<Task>()
        for (i in 0 until n) {
            val pick = items.shuffled(rnd).take(3 + rnd.nextInt(3))
            val name = "t" + (100 + rnd.nextInt(900)) + ".txt"
            out.add(Task("أنشئ ملف نصي فيه قائمة مشتريات: " + pick.joinToString("، ") + " باسم " + name, name, pick.joinToString("\n")))
        }
        return out
    }

    fun passes(t: Task, reply: String): Boolean {
        val f = FileTools.fromModel(reply) ?: return false
        return f.name == t.name && String(f.bytes, Charsets.UTF_8).trim() == t.body
    }
}
