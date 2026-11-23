"""Qidiruv yordamchilari: apostrof variantlari, kirill -> lotin, tarjima orqali qidirish."""
import re

from django.db.models import Q

APOS = ["'", "‘", "’", "ʻ", "ʼ", "`"]
_CYR2LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "ғ": "g'", "д": "d", "е": "e", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "қ": "q", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ў": "o'", "ф": "f", "х": "x", "ҳ": "h",
    "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ы": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def cyr_to_lat(text):
    out = []
    for ch in text:
        low = ch.lower()
        if low in _CYR2LAT:
            lat = _CYR2LAT[low]
            out.append(lat.capitalize() if ch != low and lat else lat)
        else:
            out.append(ch)
    return "".join(out)


def apostrophe_variants(text):
    """'bo'linma' -> bo'linma, bo‘linma, boʻlinma ... (bazada turli belgilar uchraydi)."""
    if not any(a in text for a in APOS):
        return [text]
    base = re.sub("[" + "".join(APOS) + "]", "\x00", text)
    return list(dict.fromkeys(base.replace("\x00", a) for a in APOS))


def query_terms(q, lang="uz"):
    """Foydalanuvchi so'rovidan bazada qidiriladigan o'zbekcha (lotin) variantlar ro'yxati."""
    q = q.strip()
    terms = [q]
    if re.search("[А-Яа-яЁёЎўҚқҒғҲҳ]", q):
        terms.append(cyr_to_lat(q))
    if lang in ("ru", "en") or re.search("[А-Яа-яЁё]", q) or re.search(r"^[A-Za-z\s-]+$", q):
        # ruscha/inglizcha so'rov: tarjimalar jadvalidan o'zbekcha manbani topamiz
        from core.models import Translation

        field = "ru" if re.search("[А-Яа-яЁё]", q) else "en"
        for src in Translation.objects.filter(**{f"{field}__icontains": q}).values_list("source", flat=True)[:15]:
            if len(src) <= 120:
                terms.append(src)
    out = []
    for t in terms:
        out += apostrophe_variants(t)
        out += [v.lower() for v in apostrophe_variants(t)] + [v.capitalize() for v in apostrophe_variants(t)]
    return list(dict.fromkeys(x for x in out if x))


def search_q(fields, q, lang="uz"):
    cond = Q()
    for term in query_terms(q, lang):
        for f in fields:
            cond |= Q(**{f"{f}__icontains": term})
    return cond
