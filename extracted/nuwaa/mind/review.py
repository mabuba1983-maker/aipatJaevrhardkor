# -*- coding: utf-8 -*-
"""File review. STATIC ONLY: it reads files, it never runs them. Python gets a real syntax-tree analysis; other text/code files get generic checks.
Every finding has a line, a severity and how sure we are. Honest limit: no reviewer can prove a file has zero bugs."""
import ast, builtins, io, json, re, zipfile
from pathlib import Path

MAX_FILE, MAX_FILES, MAX_ZIP_TOTAL = 300_000, 60, 3_000_000
CODE_EXT = {".py", ".js", ".ts", ".kt", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs", ".php", ".rb", ".sh", ".sql", ".html", ".css", ".json", ".md", ".txt", ".yml", ".yaml", ".kts", ".gradle"}
SEV = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SECRET = re.compile(r"""(?i)\b(api[_-]?key|secret|token|passwd|password|private[_-]?key)\b\s*[:=]\s*["'][^"'\s]{8,}["']""")
SHADOW = set(dir(builtins)) & {"list", "dict", "str", "int", "set", "id", "type", "max", "min", "sum", "len", "map", "filter", "input", "file", "open", "all", "any", "sorted"}
DANGER = {"eval": "تنفيذ نص كأنه كود", "exec": "تنفيذ نص كأنه كود", "pickle.loads": "فك pickle من مصدر غير موثوق ينفذ كود", "os.system": "أمر شِل", "yaml.load": "yaml.load بدون SafeLoader"}

def F(line, sev, rule, msg, conf="high"): return {"line": line, "severity": sev, "rule": rule, "message": msg, "confidence": conf}

def _dotted(n):
    if isinstance(n, ast.Name): return n.id
    if isinstance(n, ast.Attribute): return _dotted(n.value) + "." + n.attr
    return ""

def review_python(text):
    try: tree = ast.parse(text)
    except SyntaxError as e: return [F(e.lineno or 1, "critical", "syntax-error", f"خطأ في الصياغة: {e.msg}")]
    out = []; defined = set(dir(builtins)); imported = {}; used = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): defined.add(n.name)
        elif isinstance(n, ast.arg): defined.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): defined.add(n.id)
        elif isinstance(n, ast.ExceptHandler) and n.name: defined.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                nm = (a.asname or a.name).split(".")[0]; defined.add(nm); imported.setdefault(nm, n.lineno)
                if a.name == "*": defined.add("*")
        elif isinstance(n, (ast.Global, ast.Nonlocal)): defined.update(n.names)
    if "*" not in defined:
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                used.add(n.id)
                if n.id not in defined and n.id not in ("__file__", "__name__", "__doc__"): out.append(F(n.lineno, "high", "undefined-name", f"الاسم «{n.id}» غير معرَّف في الملف", "medium"))
    else:
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {_dotted(n).split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for nm, ln in imported.items():
        if nm not in used and not re.search(rf"__all__.*{nm}", text): out.append(F(ln, "low", "unused-import", f"الاستيراد «{nm}» غير مستخدم"))
    seen_defs = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in list(n.args.defaults) + list(n.args.kw_defaults):
                if isinstance(d, (ast.List, ast.Dict, ast.Set)): out.append(F(n.lineno, "high", "mutable-default", f"قيمة افتراضية قابلة للتعديل في «{n.name}» (تُشارَك بين الاستدعاءات)"))
            ln = (getattr(n, "end_lineno", n.lineno) or n.lineno) - n.lineno + 1
            if ln > 60: out.append(F(n.lineno, "low", "long-function", f"الدالة «{n.name}» طويلة ({ln} سطر)"))
            cx = 1 + sum(isinstance(c, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.BoolOp, ast.IfExp, ast.comprehension, ast.AsyncFor)) for c in ast.walk(n))
            if cx > 12: out.append(F(n.lineno, "medium", "complexity", f"تعقيد الدالة «{n.name}» عالي ({cx})", "medium"))
            assigned = {}; loaded = set()
            for c in ast.walk(n):
                if isinstance(c, ast.Name):
                    if isinstance(c.ctx, ast.Store): assigned.setdefault(c.id, c.lineno)
                    else: loaded.add(c.id)
            glob = {g for c in ast.walk(n) if isinstance(c, (ast.Global, ast.Nonlocal)) for g in c.names}
            for v, l in assigned.items():
                if v not in loaded and v not in glob and not v.startswith("_"): out.append(F(l, "low", "unused-variable", f"المتغير «{v}» يأخذ قيمة ولا يُستخدم", "medium"))
            key = (n.name, id(getattr(n, "parent", None)))
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module)) or hasattr(n, "body"):
            body = getattr(n, "body", None)
            if isinstance(body, list):
                names = {}
                for b in body:
                    if isinstance(b, (ast.FunctionDef, ast.ClassDef)):
                        if b.name in names and not b.decorator_list: out.append(F(b.lineno, "medium", "duplicate-def", f"«{b.name}» معرَّفة مرتين (الثانية تلغي الأولى؛ الأولى في سطر {names[b.name]})"))
                        names[b.name] = b.lineno
                for i, b in enumerate(body[:-1]):
                    if isinstance(b, (ast.Return, ast.Raise, ast.Continue, ast.Break)): out.append(F(body[i + 1].lineno, "medium", "unreachable", "كود بعد return/raise/break ما يتنفذ أبدا"))
        if isinstance(n, ast.ExceptHandler):
            if n.type is None: out.append(F(n.lineno, "medium", "bare-except", "except بدون نوع يلتقط حتى إيقاف البرنامج (KeyboardInterrupt)"))
            if len(n.body) == 1 and isinstance(n.body[0], ast.Pass): out.append(F(n.lineno, "medium", "swallowed-error", "الخطأ يُبلَع بصمت (except: pass) فتضيع الأعطال", "medium"))
        elif isinstance(n, ast.Compare):
            for op, c in zip(n.ops, n.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(c, ast.Constant) and c.value is None: out.append(F(n.lineno, "low", "none-compare", "قارن مع None بـ is / is not"))
                if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(c, ast.Constant) and isinstance(c.value, (int, str, bytes)) and not isinstance(c.value, bool): out.append(F(n.lineno, "medium", "is-literal", "is مع قيمة ثابتة؛ المقصود غالبا =="))
        elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod)) and isinstance(n.right, ast.Constant) and n.right.value == 0:
            out.append(F(n.lineno, "critical", "div-zero", "قسمة على صفر ثابت"))
        elif isinstance(n, ast.Call):
            d = _dotted(n.func)
            if d in DANGER: out.append(F(n.lineno, "high", "dangerous-call", f"{d}: {DANGER[d]}", "medium"))
            if d.startswith("subprocess.") and any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords): out.append(F(n.lineno, "high", "shell-true", "subprocess مع shell=True عرضة لحقن الأوامر"))
            if d == "open" and not any(isinstance(p, ast.withitem) for p in [getattr(n, "_in_with", None)]): pass
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id in SHADOW: out.append(F(n.lineno, "low", "shadow-builtin", f"الاسم «{t.id}» يغطي دالة مدمجة"))
    with_calls = {id(i.context_expr) for w in ast.walk(tree) if isinstance(w, (ast.With, ast.AsyncWith)) for i in w.items}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _dotted(n.func) == "open" and id(n) not in with_calls: out.append(F(n.lineno, "low", "open-without-with", "open() بدون with: الملف قد ما يُغلق عند الخطأ", "medium"))
    return out

def review_generic(text, ext):
    out = []; lines = text.split("\n"); stack = []; pairs = {")": "(", "]": "[", "}": "{"}
    if ext == ".json":
        try: json.loads(text)
        except json.JSONDecodeError as e: out.append(F(e.lineno, "critical", "invalid-json", f"JSON غير صالح: {e.msg}"))
        return out + _common(lines)
    if ext in (".js", ".ts", ".kt", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".php", ".kts", ".gradle"):
        s = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S); s = re.sub(r'"(\\.|[^"\\\n])*"|\'(\\.|[^\'\\\n])*\'', '""', s); ln = 1
        for ch in s:
            if ch == "\n": ln += 1
            elif ch in "([{": stack.append((ch, ln))
            elif ch in pairs:
                if not stack or stack[-1][0] != pairs[ch]: out.append(F(ln, "high", "bracket-mismatch", f"قوس «{ch}» ما له مقابل صحيح", "medium")); stack = []; break
                stack.pop()
        for ch, l in stack[:1]: out.append(F(l, "high", "bracket-unclosed", f"القوس «{ch}» ما انغلق", "medium"))
        for i, l in enumerate(lines, 1):
            if re.search(r"\beval\s*\(|innerHTML\s*=", l): out.append(F(i, "high", "dangerous-call", "eval/innerHTML: خطر حقن كود", "medium"))
            if re.search(r"==\s*null|!=\s*null", l) and ext in (".js", ".ts"): out.append(F(i, "low", "loose-null", "استخدم === للمقارنة", "low"))
    return out + _common(lines)

def _common(lines):
    out = []; tabs = any(l.startswith("\t") for l in lines); spaces = any(l.startswith("  ") for l in lines)
    if tabs and spaces: out.append(F(1, "low", "mixed-indent", "خلط بين Tab ومسافات في المسافة البادئة"))
    for i, l in enumerate(lines, 1):
        if SECRET.search(l): out.append(F(i, "critical", "hardcoded-secret", "يبدو أن فيه مفتاح/كلمة سر مكتوبة داخل الملف. لا ترفعها لأي مكان وغيّرها", "medium"))
        if len(l) > 200: out.append(F(i, "low", "long-line", f"سطر طويل ({len(l)} حرف)"))
        if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", l): out.append(F(i, "low", "todo", "علامة عمل غير منتهي"))
    return out

def review_text(name, text):
    ext = Path(name).suffix.lower(); text = text.replace("\r\n", "\n")
    fs = (review_python(text) if ext == ".py" else review_generic(text, ext)) + (_common(text.split("\n")) if ext == ".py" else [])
    seen, uniq = set(), []
    for f in sorted(fs, key=lambda f: (SEV[f["severity"]], f["line"])):
        k = (f["line"], f["rule"], f["message"])
        if k not in seen: seen.add(k); uniq.append(f)
    return {"file": name, "lines": text.count("\n") + 1, "findings": uniq, "counts": {s: sum(1 for f in uniq if f["severity"] == s) for s in SEV}}

def review_files(files):
    """files = [(name, text)]. Returns a report."""
    reps = [review_text(n, t) for n, t in files[:MAX_FILES] if len(t) <= MAX_FILE]
    skipped = [n for n, t in files if len(t) > MAX_FILE] + [n for n, _ in files[MAX_FILES:]]
    total = {s: sum(r["counts"][s] for r in reps) for s in SEV}
    return {"files": reps, "total": total, "skipped": skipped,
            "note": "مراجعة ثابتة (ما تم تشغيل أي ملف). غياب الملاحظات لا يعني أن الملف خالٍ من الأخطاء: ما أقدر أثبت ذلك."}

def read_zip(data):
    """Safe zip reading: size caps, no path tricks, only known text/code extensions. Returns [(name, text)]."""
    out, total = [], 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for i in z.infolist():
            nm = i.filename
            if i.is_dir() or nm.startswith("/") or ".." in Path(nm).parts or Path(nm).suffix.lower() not in CODE_EXT or i.file_size > MAX_FILE: continue
            total += i.file_size
            if total > MAX_ZIP_TOTAL or len(out) >= MAX_FILES: break
            try: out.append((nm, z.read(i).decode("utf-8")))
            except UnicodeDecodeError: pass
    return out

def format_report(rep):
    lines = []
    for r in rep["files"]:
        lines.append(f"📄 {r['file']} — {r['lines']} سطر — " + "، ".join(f"{k}:{v}" for k, v in r["counts"].items() if v) if any(r["counts"].values()) else f"📄 {r['file']} — {r['lines']} سطر — ما لقيت ملاحظات")
        for f in r["findings"][:40]: lines.append(f"  سطر {f['line']} [{f['severity']}] {f['message']}" + ("" if f["confidence"] == "high" else f" (ثقتي {f['confidence']})"))
    return "\n".join(lines + ["", rep["note"]])

if __name__ == "__main__":
    import sys
    files = []
    for p in map(Path, sys.argv[1:]):
        if p.suffix == ".zip": files += read_zip(p.read_bytes())
        elif p.is_dir(): files += [(str(f), f.read_text(encoding="utf-8", errors="ignore")) for f in sorted(p.rglob("*")) if f.is_file() and f.suffix.lower() in CODE_EXT and "__pycache__" not in f.parts][:MAX_FILES]
        elif p.is_file(): files.append((str(p), p.read_text(encoding="utf-8", errors="ignore")))
    print(format_report(review_files(files)))
