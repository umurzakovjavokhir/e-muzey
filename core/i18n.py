"""Sayt tillari: O'zbekcha (lotin), Ўзбекча (кирилл), Русский, English.

Shablonlarga tegmasdan ishlaydi: tayyor HTML javobdagi matnlar
- ``ru`` / ``en`` uchun ``Translation`` jadvali (interfeys + kontent) bo'yicha tarjima qilinadi;
- ``uz-cyrl`` uchun lotin yozuvidan kirill yozuviga avtomatik o'giriladi.
"""
import html
import re
import threading

from django.utils import translation

LANGS = [
    ("uz", "O'z", "O'zbekcha"),
    ("uz-cyrl", "Ўз", "Ўзбекча"),
    ("ru", "Ру", "Русский"),
    ("en", "En", "English"),
]
LANG_CODES = {c for c, _, _ in LANGS}
COOKIE = "mg_lang"
DEFAULT = "uz"
# Django ichki lokali (sana formatlari va h.k.)
DJANGO_LOCALE = {"uz": "uz", "uz-cyrl": "uz", "ru": "ru", "en": "en"}


def get_lang(request):
    lang = getattr(request, "LANGUAGE_CODE", None)
    if lang in LANG_CODES:
        return lang
    lang = request.COOKIES.get(COOKIE)
    return lang if lang in LANG_CODES else DEFAULT


# --------------------------------------------------------------- transliteratsiya
_APOS = "'‘’ʻʼ`´"
_LAT2CYR_MULTI = [
    ("o'", "ў"), ("g'", "ғ"), ("sh", "ш"), ("ch", "ч"), ("yo", "ё"), ("yu", "ю"), ("ya", "я"),
    ("ye", "е"),
]
_LAT2CYR = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж",
    "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с",
    "t": "т", "u": "у", "v": "в", "x": "х", "y": "й", "z": "з", "c": "с", "w": "в",
}
_VOWELS = set("aeiouAEIOUаеиоуўэяюёАЕИОУЎЭЯЮЁ")
_TOKEN = re.compile(r"(https?://\S+|www\.\S+|\S+@\S+\.\S+|[A-Za-z][A-Za-z0-9]*\.(?:uz|com|org|ru|net)\b)")


def _case(src, dst):
    if src.isupper() and (len(src) > 1 or len(dst) == 1):
        return dst.upper()
    if src[:1].isupper():
        return dst[:1].upper() + dst[1:]
    return dst


def _translit_word(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        low = ch.lower()
        prev = text[i - 1] if i else ""
        word_start = not prev or (not prev.isalpha() and prev not in _APOS)
        # tutuq belgisi (unli/undoshdan keyin) -> ъ ; o' / g' alohida
        if ch in _APOS:
            if prev.lower() in ("o", "g"):
                i += 1
                continue
            if prev.isalpha() and i + 1 < n and text[i + 1].isalpha():
                out.append("ъ" if not (prev.isupper() and text[i + 1].isupper()) else "Ъ")
                i += 1
                continue
            out.append(ch)
            i += 1
            continue
        pair = text[i:i + 2]
        lp = pair.lower()
        if len(pair) == 2 and lp[1] in _APOS and lp[0] in ("o", "g"):
            dst = "ў" if lp[0] == "o" else "ғ"
            out.append(_case(pair[0], dst))
            i += 2
            continue
        matched = False
        for src, dst in _LAT2CYR_MULTI[2:]:
            if lp == src:
                # "yo'l" -> "йўл" (y + o'), "yo" emas
                if src == "yo" and i + 2 < n and text[i + 2] in _APOS:
                    break
                # "ye" faqat so'z boshida yoki unlidan keyin "е"
                if src == "ye" and not (word_start or prev in _VOWELS):
                    break
                # "sh" ichida s+h (masalan "Ishoq") ajratilmaydi — soddalashtirilgan qoida
                if pair.isupper() and (i + 2 >= n or text[i + 2].isupper() or not text[i + 2].isalpha()):
                    out.append(dst.upper())
                else:
                    out.append(_case(pair[0], dst))
                i += 2
                matched = True
                break
        if matched:
            continue
        if low == "e" and (word_start or prev in _VOWELS):
            out.append(_case(ch, "э"))
        elif low in _LAT2CYR:
            out.append(_case(ch, _LAT2CYR[low]))
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def to_cyrillic(text):
    if not text or not re.search(r"[A-Za-z]", text):
        return text
    parts = _TOKEN.split(text)
    return "".join(p if i % 2 else _translit_word(p) for i, p in enumerate(parts))


# ------------------------------------------------------------------- tarjimalar
_cache = {"version": None, "exact": {}, "num": {}, "wild": [], "prefix": []}
_lock = threading.Lock()
_version = {"value": 0}
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def bump_version(*args, **kwargs):
    _version["value"] += 1


def norm(text):
    text = re.sub(r"[‘’ʻʼ`´]", "'", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _load():
    from core.models import Translation

    exact, num, wild, prefix = {}, {}, [], []
    for src, ru, en in Translation.objects.values_list("source", "ru", "en"):
        key = norm(src)
        val = {"ru": ru, "en": en}
        if "{x}" in key:
            rx = re.escape(key).replace(re.escape("{x}"), "(.+?)")
            wild.append((re.compile("^" + rx + "$"), val))
        elif "#" in key:
            num[key] = val
        else:
            exact[key] = val
            if len(key) > 20:
                prefix.append((key, val))
    wild.sort(key=lambda w: -len(w[0].pattern))
    _cache.update(exact=exact, num=num, wild=wild, prefix=prefix, version=_version["value"])


_RELOAD_EVERY = 60  # soniya: boshqa jarayonlarda (admin, import buyrug'i) qilingan o'zgarishlarni olish uchun


def _ensure():
    import time

    now = time.monotonic()
    stale = _cache["version"] != _version["value"] or now - _cache.get("loaded_at", 0) > _RELOAD_EVERY
    if stale:
        with _lock:
            if _cache["version"] != _version["value"] or now - _cache.get("loaded_at", 0) > _RELOAD_EVERY:
                _load()
                _cache["loaded_at"] = now


def translate_text(text, lang, depth=0):
    """Bitta matn bo'lagini tarjima qiladi; topilmasa None."""
    key = norm(text)
    if not key:
        return None
    hit = _cache["exact"].get(key)
    if hit and hit.get(lang):
        return hit[lang]
    nums = _NUM.findall(key)
    if nums:
        hit = _cache["num"].get(_NUM.sub("#", key))
        if hit and hit.get(lang):
            out = hit[lang]
            for n in nums:
                out = out.replace("#", n, 1)
            return out
    if depth < 2:
        for rx, val in _cache["wild"]:
            m = rx.match(key)
            if m and val.get(lang):
                inner = m.group(1)
                inner_t = translate_text(inner, lang, depth + 1) or inner
                return val[lang].replace("{x}", inner_t)
    # truncatechars bilan qisqartirilgan matnlar
    if key.endswith("…") or key.endswith("..."):
        stem = key.rstrip(".…").rstrip()
        if len(stem) >= 12:
            for src, val in _cache["prefix"]:
                if src.startswith(stem) and val.get(lang):
                    t = val[lang]
                    return (t[: max(len(stem), 12)].rstrip() + "…") if len(t) > len(stem) + 1 else t
    return None


# -------------------------------------------------------------- HTML qayta ishlash
_SPLIT = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->|<[^>]+>)", re.S | re.I)
_ATTR = re.compile(r'(\s(?:placeholder|title|aria-label|alt)=")([^"]*)(")', re.I)
_SKIP_TAGS = re.compile(r"^<(textarea|pre|code)\b", re.I)


def _convert(text, lang):
    if lang == "uz-cyrl":
        return to_cyrillic(text)
    return translate_text(text, lang)


def _process_text(chunk, lang):
    raw = html.unescape(chunk)
    core = raw.strip()
    if not core or not re.search(r"[A-Za-z]", core):
        return chunk
    res = _convert(core, lang)
    if res is None:
        return chunk
    lead = raw[: len(raw) - len(raw.lstrip())]
    trail = raw[len(raw.rstrip()):]
    return html.escape(lead + res + trail, quote=False)


def _process_tag(tag, lang):
    def rep(m):
        val = html.unescape(m.group(2))
        res = _convert(val, lang) if val.strip() else None
        return m.group(1) + html.escape(res if res is not None else val, quote=True) + m.group(3)
    tag = _ATTR.sub(rep, tag)
    if tag[:5].lower() == "<html":
        tag = re.sub(r'lang="[^"]*"', 'lang="%s"' % lang, tag)
    return tag


def localize_html(content, lang):
    if lang == DEFAULT:
        return content
    if lang != "uz-cyrl":
        _ensure()
    parts = _SPLIT.split(content)
    skip = 0
    out = []
    for i, part in enumerate(parts):
        if i % 2:  # teg
            low = part[:12].lower()
            if low.startswith("<script") or low.startswith("<style") or low.startswith("<!--"):
                out.append(part)
                continue
            if _SKIP_TAGS.match(part):
                skip += 1
            elif re.match(r"^</(textarea|pre|code)>", part, re.I):
                skip = max(0, skip - 1)
            out.append(_process_tag(part, lang))
        else:
            out.append(part if skip else _process_text(part, lang))
    return "".join(out)


class LanguageMiddleware:
    """Cookie bo'yicha tilni aniqlaydi va HTML javobni shu tilga o'giradi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.COOKIES.get(COOKIE)
        if lang not in LANG_CODES:
            lang = DEFAULT
        request.LANGUAGE_CODE = lang
        translation.activate(DJANGO_LOCALE[lang])
        response = self.get_response(request)
        if (
            lang != DEFAULT
            and not request.path.startswith("/admin")
            and response.get("Content-Type", "").startswith("text/html")
            and not getattr(response, "streaming", False)
        ):
            charset = response.charset or "utf-8"
            text = response.content.decode(charset)
            response.content = localize_html(text, lang).encode(charset)
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        response.headers.setdefault("Content-Language", lang)
        translation.deactivate()
        return response
