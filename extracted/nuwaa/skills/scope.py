# -*- coding: utf-8 -*-
"""Nuwaa is specialized: programming (any language, concepts, debugging, algorithms), Arabic language (grammar, spelling, vocabulary, literature),
and English language (grammar, vocabulary, translation) — nothing else. This is a RULE-BASED guard, not the model judging itself (the model cannot be
trusted to know what it does not know): a fixed keyword check that runs BEFORE the model is asked, so it never even attempts an answer it was not
built for. Deliberately conservative: it only refuses on a strong off-topic signal, never on an ambiguous one, because wrongly refusing a real
programming or language question is worse than occasionally answering something borderline."""
import re

IN_SCOPE = [
    "بايثون", "python", "كود", "برنام", "خوارزم", "دالة", "متغير", "حلقة", "مصفوفة", "قائمة", "قاموس", "كلاس", "class", "function",
    "javascript", "kotlin", "java", "html", "css", "sql", "git", "api", "json", "csv", "ملف", "مشروع", "تطبيق", "سيرفر", "server",
    "bug", "error", "خطأ", "اصلاح", "صحح", "راجع", "تتبع", "trace", "compile", "debug", "نحو", "صرف", "اعراب", "إعراب", "بلاغة",
    "همزة", "تاء مربوطة", "املاء", "إملاء", "لغة عربية", "قواعد عربية", "arabic grammar", "english grammar", "ترجم", "translate",
    "grammar", "vocabulary", "tense", "verb", "noun", "sentence",
]
OUT_OF_SCOPE = [
    "ابني بيت", "بناء بيت", "اعمار", "مقاول", "وصفة", "طبخة", "طبخ", "اكلة", "كبسة", "عاصمة", "تاريخ الدولة", "حرب عالمية",
    "تشخيص مرض", "تشخيص", "جرعة دواء", "اعراض مرض", "مرض", "تصليح سيارة", "صيانة سيارة", "محرك سيارة", "فلك", "تنجيم", "ابراج",
    "حكم شرعي", "فتوى", "تفسير سورة", "وزن طفل", "رجيم", "تمارين رياضية", "رياضة كرة", "دوري كرة", "نتيجة مباراة",
    "سعر الذهب", "سعر العملة", "اسهم", "بورصة", "عقار للبيع", "حجز فندق", "تذكرة طيران",
]

def _norm(t):
    t = t.lower()
    t = re.sub(r"[إأآا]", "ا", t); t = t.replace("ى", "ي").replace("ة", "ه")
    t = re.sub(r"(?<=\s)ال(?=\w)|^ال(?=\w)", "", t)      # drop the definite article "ال" so "محرك السيارة" matches "محرك سيارة"
    return re.sub(r"\s+", " ", t).strip()

REFUSAL_AR = ("أنا متخصص فقط في البرمجة واللغة العربية والإنجليزية، وهذا السؤال خارج تخصصي، فلن أعطيك جوابا قد يكون غير دقيق. "
              "اسألني عن كود، أو خطأ برمجي، أو قاعدة نحوية أو إملائية، أو ترجمة، وسأساعدك.")

def in_scope(q):
    """True = let the model answer. False = refuse with REFUSAL_AR instead of risking a made-up answer outside the model's training."""
    n = _norm(q)
    if any(_norm(k) in n for k in IN_SCOPE): return True
    if any(_norm(k) in n for k in OUT_OF_SCOPE): return False
    return True   # ambiguous or unmatched: default to answering rather than over-refusing

def guard(q):
    """Returns REFUSAL_AR if out of scope, else None (meaning: proceed to the model as normal)."""
    return None if in_scope(q) else REFUSAL_AR
