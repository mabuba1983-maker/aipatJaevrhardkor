# -*- coding: utf-8 -*-
"""Real self-correction (text-only, no vision): the engine writes Python, the sandbox actually RUNS it,
and the real traceback (if any) is fed back to the engine as the next turn, up to max_retries times.
This is honest and buildable today — unlike the 'sees its own 3D output and fixes it' idea, nothing here
is faked: every 'error' shown to the model came from a real subprocess that really executed the code.
"""
from ..sandbox.snippet import run_snippet


def _extract_code(reply: str) -> str:
    """Pull the first ```python ... ``` or ``` ... ``` fenced block out of a reply; else use the whole reply."""
    if "```" not in reply:
        return reply.strip()
    parts = reply.split("```")
    # parts: [before, lang+code, after, ...] — take the first fenced block
    block = parts[1]
    lines = block.split("\n", 1)
    if lines and lines[0].strip().lower() in ("python", "py", ""):
        return lines[1] if len(lines) > 1 else ""
    return block


def generate_with_feedback(engine, prompt: str, max_retries: int = 3, max_new: int = 400, log=print):
    """engine: a nuwaa.core.engine.Engine instance (or anything with .reply(text, **kwargs)).
    Returns {"code": str, "ok": bool, "attempts": int, "last_result": dict, "history": [...]}.
    """
    history = []
    current_prompt = prompt
    last_result = None
    code = ""
    for attempt in range(1, max_retries + 1):
        reply = engine.reply(current_prompt, max_new=max_new)
        code = _extract_code(reply)
        result = run_snippet(code)
        history.append({"attempt": attempt, "code": code, "result": result})
        log(f"[self_correct] attempt {attempt}: ok={result['ok']}")
        last_result = result
        if result["ok"]:
            return {"code": code, "ok": True, "attempts": attempt, "last_result": result, "history": history}
        # Build the NEXT prompt from the REAL error, not a guess.
        err = result["stderr"].strip() or "(no stderr, but exit code != 0)"
        current_prompt = (
            f"{prompt}\n\n"
            f"الكود اللي كتبته قبل شوي طلع فيه خطأ فعلي عند التشغيل:\n{err}\n"
            f"صلّح الكود وأعد كتابته كامل داخل ```python ... ``` بدون أي كلام إضافي."
        )
    return {"code": code, "ok": False, "attempts": max_retries, "last_result": last_result, "history": history}
