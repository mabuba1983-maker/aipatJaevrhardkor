# -*- coding: utf-8 -*-
"""Static checks for the Android project. They do NOT replace compiling it (no Android toolchain in this environment); they catch the mistakes
that are cheap to catch: unbalanced brackets, a manifest entry without a class, assets out of sync with data/, missing resources."""
import sys, re, unittest, xml.dom.minidom as minidom
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MAIN = ROOT / "android/app/src/main"
KT = sorted((MAIN / "java/ai/nuwaa").glob("*.kt"))

_TOK = re.compile(r'''"""(?:.|\n)*?"""|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])'|//[^\n]*|/\*(?:.|\n)*?\*/''')
def strip_kotlin(s):
    """Strings and comments are read in ONE pass, in source order (a string such as "*/*" must not start a comment)."""
    def f(m):
        t = m.group(0)
        return "" if t.startswith("//") or t.startswith("/*") else ("''" if t.startswith("'") else '""')
    return _TOK.sub(f, s)

class Static(unittest.TestCase):
    def test_brackets_balanced(self):
        for f in KT:
            s = strip_kotlin(f.read_text(encoding="utf-8")); st = []
            for ch in s:
                if ch in "([{": st.append(ch)
                elif ch in ")]}":
                    self.assertTrue(st and "([{".index(st.pop()) == ")]}".index(ch), f.name)
            self.assertEqual(st, [], f.name)
    def test_manifest_classes_and_resources_exist(self):
        d = minidom.parse(str(MAIN / "AndroidManifest.xml")); names = []
        for tag in ("activity", "service"):
            names += [e.getAttribute("android:name") for e in d.getElementsByTagName(tag)]
        self.assertTrue(names)
        for n in names:
            f = MAIN / "java/ai/nuwaa" / (n.lstrip(".") + ".kt"); self.assertTrue(f.exists(), n)
            self.assertRegex(f.read_text(encoding="utf-8"), r"class\s+" + n.lstrip("."))
        for e in d.getElementsByTagName("meta-data"):
            r = e.getAttribute("android:resource"); self.assertTrue((MAIN / "res" / r.replace("@xml/", "xml/")).with_suffix(".xml").exists(), r)
        perms = {e.getAttribute("android:name") for e in d.getElementsByTagName("uses-permission")}
        self.assertIn("android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION", perms)   # required on Android 14
        self.assertIn("android.permission.FOREGROUND_SERVICE", perms)
        svc = {e.getAttribute("android:name"): e for e in d.getElementsByTagName("service")}
        self.assertEqual(svc[".ScreenShareService"].getAttribute("android:foregroundServiceType"), "mediaProjection")
        self.assertEqual(svc[".ScreenReader"].getAttribute("android:permission"), "android.permission.BIND_ACCESSIBILITY_SERVICE")
    def test_string_resources_referenced_exist(self):
        strings = (MAIN / "res/values/strings.xml").read_text(encoding="utf-8")
        for f in (MAIN / "res/xml").glob("*.xml"):
            for ref in re.findall(r"@string/(\w+)", f.read_text(encoding="utf-8")): self.assertIn(f'name="{ref}"', strings)
    def test_assets_in_sync_with_data(self):
        for a, b in (("kb.jsonl", "data/kb/kb.jsonl"), ("syn.json", "data/kb/syn.json")):
            self.assertEqual((MAIN / "assets" / a).read_bytes(), (ROOT / b).read_bytes(), a + " is stale: copy it from data/kb/")
    def test_gradle_keeps_model_uncompressed_and_declares_rtl(self):
        self.assertIn('noCompress += "bin"', (ROOT / "android/app/build.gradle.kts").read_text(encoding="utf-8"))   # openFd() on model.bin needs it
        self.assertIn('supportsRtl="true"', (MAIN / "AndroidManifest.xml").read_text(encoding="utf-8"))
    def test_kotlin_uses_the_same_thresholds_as_python(self):
        from nuwaa.memory.kb import HIGH, LOW
        k = (MAIN / "java/ai/nuwaa/Kb.kt").read_text(encoding="utf-8")
        self.assertIn(f"HIGH = {HIGH}", k); self.assertIn(f"LOW = {LOW}", k)
    def test_app_sets_no_fixed_ram_budget(self):
        br = (MAIN / "java/ai/nuwaa/Brain.kt").read_text(encoding="utf-8"); ui = (MAIN / "java/ai/nuwaa/MainActivity.kt").read_text(encoding="utf-8")
        self.assertNotIn("RAM_BUDGET_MB", br + ui); self.assertIn("maxMemory()", br)          # the only limit left is the real heap the phone gives the app
    def test_self_development_button_is_visible_in_menu_and_bar_and_app_stays_offline(self):
        ui = (MAIN / "java/ai/nuwaa/MainActivity.kt").read_text(encoding="utf-8"); br = (MAIN / "java/ai/nuwaa/Brain.kt").read_text(encoding="utf-8")
        self.assertIn('"🧠  تطوير النفس"', ui); self.assertIn("buildDevPage()", ui); self.assertIn("ابدأ التطوير الآن", ui); self.assertIn("fun develop()", br); self.assertIn("rehearsal", br)
        self.assertLess(ui.index('"🧠  تطوير النفس"'), ui.index('"🗂  المحادثات السابقة"'))        # first group of the menu, not buried
        for bad in ("showDevelopDialog", "HttpURLConnection", "api.github.com"): self.assertNotIn(bad, ui)
        manifest = (MAIN / "AndroidManifest.xml").read_text(encoding="utf-8")
        # the app is offline except for the one explicit, opt-in Google-search feature; the manifest must say so right next to the permission
        self.assertIn("android.permission.INTERNET", manifest); self.assertIn("ONLY by the optional Google-search feature", manifest)
    def test_plus_button_sends_files_read_only_and_creates_files_only_through_the_system_picker(self):
        ui = (MAIN / "java/ai/nuwaa/MainActivity.kt").read_text(encoding="utf-8"); br = (MAIN / "java/ai/nuwaa/Brain.kt").read_text(encoding="utf-8")
        self.assertIn("ACTION_OPEN_DOCUMENT", ui); self.assertIn("pickFile()", ui); self.assertIn("answerAbout", br); self.assertIn("showPlus()", ui)
        self.assertIn("ACTION_CREATE_DOCUMENT", ui); self.assertIn("إنشاء ملف", ui); self.assertIn("إرسال ملف", ui)
        # writing: writeCreated() (user picked a place) and saveToDownloads() (the user typed «أنشئ ملف ...»: MediaStore Downloads/Nuwaa, re-read and compared)
        self.assertEqual(ui.count("openOutputStream"), 2); self.assertIn("saveToDownloads", ui); self.assertIn("contentEquals", ui)
        for bad in ("FileOutputStream", "WRITE_EXTERNAL_STORAGE"): self.assertNotIn(bad, ui + br)
    def test_no_real_model_is_claimed_when_none_is_shipped(self):
        # the shipped APK must not contain random weights: model.bin is only copied by CI after the benchmark gate
        self.assertFalse((MAIN / "assets/model.bin").exists())

class AdaptiveEffort(unittest.TestCase):
    """The Kotlin cannot be compiled here, so these only guard the wiring: the modes exist, the device limits exist, and Brain really uses them."""
    def read(self, n):
        return (ROOT / "android/app/src/main/java/ai/nuwaa" / n).read_text(encoding="utf-8")
    def test_modes_and_device_limits(self):
        e = self.read("Effort.kt")
        for k in ("FAST", "NORMAL", "THINK", "isPowerSaveMode", "currentThermalStatus", "EXTRA_LEVEL", "maxMemory", "fun plan("):
            self.assertIn(k, e)
    def test_brain_uses_them(self):
        b = self.read("Brain.kt")
        for k in ("Effort.plan(", "replyThink(", "plan.maxChars"):
            self.assertIn(k, b)
    def test_think_keeps_only_the_winner(self):
        n = self.read("Nlm.kt")
        self.assertIn("commit: Boolean = true", n); self.assertIn("fun replyThink(", n); self.assertIn("restore(bestEnd", n)
    def test_model_builds_files_itself(self):
        ft = self.read("FileTools.kt"); br = self.read("Brain.kt")
        for k in ("fun fromModel(", "fun cleanName(", "<<نهاية>>", "okExt"): self.assertIn(k, ft)
        self.assertIn("FileTools.fromModel(written)", br)
        self.assertIn("FileTools.display(", br)
        n = self.read("Nlm.kt"); self.assertIn("fun copyNext(", n); self.assertIn("COPY_GAIN", n)
    def test_train_button_with_cpu_share(self):
        t = self.read("Trainer.kt"); m = self.read("MainActivity.kt"); n = self.read("Nlm.kt"); b = self.read("Brain.kt")
        for k in ("percent", "sleepSafe(", "restoreSnapshot(snap)", "Effort.deviceCap(ctx)", "THREAD_PRIORITY_BACKGROUND", "steps % 40 == 0", "pct < 100"):
            self.assertIn(k, t)
        for k in ("buildTrainPage", "SeekBar", "toggleTrain", "FLAG_KEEP_SCREEN_ON", "onDestroy"): self.assertIn(k, m)
        for k in ("fun trainWindow(", "fun snapshot(", "fun restoreSnapshot("): self.assertIn(k, n)
        self.assertIn("fun trainPairs(", b)
        self.assertTrue((ROOT / "android/app/src/main/assets/train.txt").exists())
    def test_projects_and_cheap_check(self):
        ft = self.read("FileTools.kt"); m = self.read("MainActivity.kt"); br = self.read("Brain.kt"); n = self.read("Nlm.kt")
        for k in ("fun cleanPath(", "fun sanityOk(", "fun allSane(", "findAll(text)"): self.assertIn(k, ft)
        self.assertIn("val more: List<MadeFile>", ft)
        self.assertIn("substringBeforeLast('/', \"\")", m); self.assertIn("f.more.isNotEmpty()", m)
        self.assertIn("allSane(it)", br); self.assertIn("accept: ((String) -> Boolean)?", n)
        self.assertIn("codeWords", self.read("Effort.kt"))
    def test_speed_governor_for_big_models(self):
        e = self.read("Effort.kt"); b = self.read("Brain.kt")
        self.assertIn("var msPerChar", e); self.assertIn("per * c * 4 > 180000.0", e); self.assertIn("Effort.msPerChar =", b)
    def test_file_button_presets_selfreview_restart(self):
        m = self.read("MainActivity.kt"); br = self.read("Brain.kt"); ft = self.read("FileTools.kt"); t = self.read("Trainer.kt")
        for k in ("toggleFileMode", "#1565C0", "&& fileMode) brain.fileRequest(q, c.id, lastBot, true)", "restartApp", "stopAndWait(5000)", "CheckBox", "توفير 15%", "قوي 100%"): self.assertIn(k, m)
        self.assertIn("forced: Boolean = false", ft); self.assertIn("if (!forced)", ft); self.assertIn("forced: Boolean = false", br); self.assertIn("fun selfAttempt(", br)
        sc = self.read("SelfCheck.kt"); self.assertIn("fun passes(", sc); self.assertIn("SelfCheck.passes(task, reply)", t); self.assertIn("selfPairs", t)
        # nothing creates a file from chat words when the button is off
        self.assertNotIn("brain.fileRequest(q, c.id, lastBot) else null", m)
    def test_no_prewritten_replies(self):
        ft = self.read("FileTools.kt"); br = self.read("Brain.kt"); m = self.read("MainActivity.kt")
        self.assertNotIn("kb.search(req", ft); self.assertNotIn("المحتوى من آخر رد لي", ft); self.assertNotIn("قد يفيدك", ft)
        self.assertNotIn("last resort", br)
        self.assertIn("رسالة من التطبيق (ليست من النموذج)", m); self.assertIn('"lm" -> a.text', m)
        t = self.read("Trainer.kt"); self.assertIn("val work = (System.nanoTime() - t0)", t)
    def test_screen_share_is_real_capture_not_fake(self):
        s = self.read("ScreenShareService.kt")
        for k in ("MediaProjectionManager", "createVirtualDisplay", "ImageReader", "acquireLatestImage", "now - lastFrame < 1000"): self.assertIn(k, s)
        r = self.read("ScreenReader.kt"); self.assertIn("AccessibilityService", r); self.assertIn("rootInActiveWindow", r)
        b = self.read("Brain.kt"); self.assertIn("📱 قراءة آلية للشاشة (ليست من النموذج)", b); self.assertNotIn("قد يفيدك", b)
    def test_scope_guard_wired_in_kotlin(self):
        sc = self.read("Scope.kt"); b = self.read("Brain.kt")
        for k in ("fun inScope(", "IN_SCOPE", "OUT_OF_SCOPE", "البرمجة"): self.assertIn(k, sc)
        self.assertIn("Scope.inScope(q)", b); self.assertIn("Scope.REFUSAL", b)
    def test_google_search_is_opt_in_user_key_only_and_labelled(self):
        g = self.read("GoogleSearch.kt"); m = self.read("MainActivity.kt"); mf = (ROOT / "android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
        for k in ("fun configured(", "fun setCredentials(", "fun clearCredentials(", "customsearch/v1", "ليست من النموذج"): self.assertIn(k, g)
        self.assertNotIn("AIza", g)                                   # no hardcoded-looking Google API key literal
        import re
        self.assertFalse(re.search(r'(apiKey|API_KEY|key)\s*=\s*"[A-Za-z0-9_\-]{20,}"', g), "a real-looking key literal must never be hardcoded")
        self.assertIn("buildDiscoverPage", m); self.assertIn("GoogleSearch.search(this, q)", m); self.assertIn("Thread {", m)
        self.assertIn("android.permission.INTERNET", mf); self.assertIn("ONLY by the optional Google-search feature", mf)
    def test_secret_growth_panel_is_pin_gated_device_adaptive_and_real(self):
        sg = self.read("SecretGrowth.kt"); m = self.read("MainActivity.kt"); br = self.read("Brain.kt")
        for k in ("fun isSet(", "fun setPin(", "fun verify(", "SHA-256", "fun maxSafeParams(", "Runtime.getRuntime().maxMemory()"): self.assertIn(k, sg)
        self.assertNotIn('KEY_HASH, "', sg)                               # no hardcoded/default pin hash literal
        for k in ("onTitleTap", "buildGrowPage", "openGrowPage", "SecretGrowth.isSet(this)", "SecretGrowth.verify(this", "brain.growModel("): self.assertIn(k, m)
        self.assertIn("fun growModel(", br); self.assertIn("Runtime.getRuntime().maxMemory()", br); self.assertIn("كرت الشاشة: غير متاح للتدريب على الجوال", m)
    def test_grow_preserves_old_behaviour_by_construction(self):
        n = self.read("Nlm.kt")
        self.assertIn("fun grow(old: Nlm, newE: Int, newH: Int): Nlm", n)
        self.assertIn("require(newE >= old.e && newH >= old.h)", n)
    def test_gemini_teacher_is_opt_in_user_key_only_scope_filtered_and_unverified_label(self):
        g = self.read("GeminiTeacher.kt"); t = self.read("Trainer.kt"); m = self.read("MainActivity.kt")
        for k in ("fun configured(", "fun setCredentials(", "fun clearCredentials(", "generativelanguage.googleapis.com", "Scope.inScope(q)", "DEFAULT_MODEL"): self.assertIn(k, g)
        self.assertNotIn("AIza", g)
        import re
        self.assertFalse(re.search(r'(apiKey|API_KEY|key)\s*=\s*"[A-Za-z0-9_\-]{20,}"', g), "no real-looking Gemini key literal")
        for k in ("teacherOn", "teacherPerMinute", "GeminiTeacher.fetchExample(", "teacherPairs"): self.assertIn(k, t)
        for k in ("GeminiTeacher.setCredentials(", "trainer().teacherOn = on", "gRateBar"): self.assertIn(k, m)
    def test_file_request_never_fires_on_attachments_or_definite_word(self):
        self.assertIn("att == null", self.read("MainActivity.kt"))
        self.assertIn("ملفا?", self.read("FileTools.kt"))


if __name__ == "__main__": unittest.main()
