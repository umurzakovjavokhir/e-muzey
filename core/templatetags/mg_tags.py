import hashlib

from django import template

register = template.Library()

GRADIENTS = [
    "linear-gradient(135deg,#123a6b 0%,#0a1a33 55%,#1d4a8a 100%)",
    "linear-gradient(135deg,#1a3a5c 0%,#0d1f38 50%,#2a5c47 100%)",
    "linear-gradient(135deg,#253a5e 0%,#101d33 55%,#3a3060 100%)",
    "linear-gradient(135deg,#0f2b4a 0%,#0a1729 50%,#14497d 100%)",
    "linear-gradient(135deg,#1d3355 0%,#0d1a2d 55%,#2b4a3a 100%)",
    "linear-gradient(135deg,#2a3f5f 0%,#101d33 50%,#4a3a20 100%)",
]


@register.filter
def gradient(value):
    """Rasm bo'lmasa ishlatiladigan barqaror gradient fon."""
    key = str(value or "mg")
    idx = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(GRADIENTS)
    return GRADIENTS[idx]


@register.inclusion_tag("includes/icon.html")
def icon(name):
    return {"name": name}


ICONS = {
    "home": '<path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H10v7H5a1 1 0 0 1-1-1z"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/>',
    "building": '<path d="M3 21h18M5 21V7l7-4 7 4v14"/><path d="M9 9h.01M15 9h.01M9 13h.01M15 13h.01M9 17h.01M15 17h.01"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "trophy": '<path d="M8 21h8M12 17v4M7 4h10v6a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "cap": '<path d="M22 10 12 5 2 10l10 5 10-5z"/><path d="M6 12v5c0 1 2.7 3 6 3s6-2 6-3v-5"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
    "user": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "star": '<path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
    "bookmark": '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    "arrow": '<path d="M5 12h14M12 5l7 7-7 7"/>',
    "chev": '<path d="m9 18 6-6-6-6"/>',
    "chevL": '<path d="m15 18-6-6 6-6"/>',
    "chevD": '<path d="m6 9 6 6 6-6"/>',
    "pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "camera": '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
    "video": '<path d="m23 7-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "share": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/>',
    "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "play": '<path d="m6 3 14 9-14 9z" fill="currentColor" stroke="none"/>',
    "expand": '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "filter": '<path d="M22 3H2l8 9.46V19l4 2v-8.54z"/>',
    "sort": '<path d="M11 5h10M11 9h7M11 13h4M3 17l3 3 3-3M6 6v14"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z"/>',
    "map": '<path d="m1 6 7-3 8 3 7-3v15l-7 3-8-3-7 3z"/><path d="M8 3v15M16 6v15"/>',
    "medal": '<circle cx="12" cy="15" r="6"/><path d="m8.21 13.89-1.5 4.5 5.29-3 5.29 3-1.5-4.5"/>',
    "chart": '<path d="M18 20V10M12 20V4M6 20v-6"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
    "box": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
}


@register.inclusion_tag("includes/icon.html", takes_context=True)
def svg(context, name, size=18):
    return {"path": ICONS.get(name, ""), "size": size}


@register.filter
def card_label(obj, key=""):
    if obj is None:
        return ""
    if key:
        getter = f"get_{key}_display"
        if hasattr(obj, getter):
            return getattr(obj, getter)()
        val = getattr(obj, key, "")
        if val:
            return val
    for k in ("achievement_type", "event_type", "edu_type", "doc_type", "person_type", "building_type", "media_type", "material_type"):
        if getattr(obj, k, None):
            getter = f"get_{k}_display"
            if hasattr(obj, getter):
                return getattr(obj, getter)()
    return ""


@register.filter
def title_of(obj):
    return getattr(obj, "title", None) or getattr(obj, "full_name", "") or str(obj)


@register.filter
def split(value, sep=" "):
    if value is None:
        return []
    return str(value).split(sep)


@register.filter
def lines(value):
    if not value:
        return []
    return [ln.strip() for ln in str(value).splitlines() if ln.strip()]


@register.filter
def get_item(d, key):
    if isinstance(d, dict):
        return d.get(key, 0)
    return 0


@register.filter
def fmt(value):
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return value


@register.filter
def money(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if v >= 1000:
        return f"{v / 1000:.1f} trln so'm".replace(".0 ", " ")
    return f"{v:g} mlrd so'm"


def _youtube_id(url):
    import re

    m = re.search(r"(?:youtu\.be/|v=|/embed/|/shorts/)([A-Za-z0-9_-]{6,})", str(url or ""))
    return m.group(1) if m else ""


@register.filter
def youtube_embed(url):
    """YouTube havolasini (watch / youtu.be / embed / shorts) embed manziliga o'giradi."""
    vid = _youtube_id(url)
    return f"https://www.youtube.com/embed/{vid}?rel=0&playsinline=1" if vid else ""


@register.filter
def youtube_watch(url):
    vid = _youtube_id(url)
    return f"https://www.youtube.com/watch?v={vid}" if vid else (url or "")


@register.filter
def lb_items(obj):
    """Galereya (lightbox) uchun JSON: rasm(lar), YouTube yoki video fayl."""
    import json

    title = str(getattr(obj, "title", "") or getattr(obj, "full_name", "") or obj)
    href = obj.get_absolute_url() if hasattr(obj, "get_absolute_url") else ""
    cover = obj.image.url if getattr(obj, "image", None) else ""
    items = []
    video_file = getattr(obj, "video_file", None)
    if video_file:
        items.append({"type": "video", "src": video_file.url, "thumb": cover, "title": title, "href": href})
    elif getattr(obj, "video_url", "") and _youtube_id(obj.video_url):
        items.append({"type": "youtube", "src": youtube_embed(obj.video_url) + "&autoplay=1",
                      "watch": youtube_watch(obj.video_url), "thumb": cover, "title": title, "href": href})
    else:
        if cover:
            items.append({"type": "image", "src": cover, "title": title, "href": href})
        photos = getattr(obj, "photos", None)
        if photos is not None:
            items += [{"type": "image", "src": p.image.url, "title": title, "href": href} for p in photos.all() if p.image]
    return json.dumps(items, ensure_ascii=False)


@register.filter
def main_image(obj):
    """Asosiy rasm maydoni: image yoki photo (bo'sh bo'lsa None)."""
    for f in ("image", "photo"):
        v = getattr(obj, f, None)
        if v and hasattr(v, "url"):
            return v
    return None


@register.filter
def media_years(items):
    """[(yil, soni), ...] - yangi yil oldin; yili ko'rsatilmaganlar hisobga olinmaydi."""
    from collections import Counter

    c = Counter(getattr(i, "year", None) for i in items)
    c.pop(None, None)
    return sorted(c.items(), reverse=True)


@register.filter
def video_thumb(v):
    """Video muqovasi: yuklangan rasm yoki YouTube eskizi."""
    if getattr(v, "cover", None):
        return v.cover.url
    vid = _youtube_id(getattr(v, "video_url", ""))
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""


@register.filter
def video_lb(v):
    """Bitta video uchun lightbox JSON."""
    import json

    title = v.title or ""
    if v.video_file:
        item = {"type": "video", "src": v.video_file.url, "thumb": video_thumb(v), "title": title}
    else:
        item = {"type": "youtube", "src": youtube_embed(v.video_url) + "&autoplay=1",
                "watch": youtube_watch(v.video_url), "thumb": video_thumb(v), "title": title}
    return json.dumps([item], ensure_ascii=False)


@register.filter
def year_video_lb(archive):
    """Yil kartasidagi asosiy video uchun lightbox JSON: yilning video havolasi + biriktirilgan videolar."""
    import json

    items = []
    if getattr(archive, "video_url", ""):
        items.append({"type": "youtube", "src": youtube_embed(archive.video_url) + "&autoplay=1",
                      "watch": youtube_watch(archive.video_url),
                      "thumb": video_thumb(archive), "title": f"{archive.year}-yil — asosiy voqealar"})
    for v in archive.videos.all():
        items.extend(json.loads(video_lb(v)))
    return json.dumps(items, ensure_ascii=False) if items else ""


@register.simple_tag(takes_context=True)
def year_url(context, year=None):
    """Joriy GET parametrlarini (tur, kategoriya, q ...) saqlagan holda yilni almashtiradi."""
    request = context.get("request")
    params = request.GET.copy() if request else {}
    if hasattr(params, "pop"):
        params.pop("page", None)
        params.pop("yil", None)
    if year:
        params["yil"] = str(year)
    qs = params.urlencode() if hasattr(params, "urlencode") else ""
    return "?" + qs if qs else "?"


@register.filter
def map_points(objs):
    """Binolar ro'yxatini xarita uchun JSON ga o'giradi (koordinatasi borlarini)."""
    import json

    if objs is None:
        return "[]"
    if not hasattr(objs, "__iter__"):
        objs = [objs]
    pts = []
    for b in objs:
        if b.latitude is None or b.longitude is None:
            continue
        pts.append({
            "lat": float(b.latitude), "lng": float(b.longitude), "title": b.title,
            "url": b.get_absolute_url(), "date": str(b.handover_date or b.year or ""),
            "img": b.image.url if b.image else "", "place": b.address or (str(b.region) if b.region else ""),
            "approx": getattr(b, "location_precision", "aniq") != "aniq",
        })
    return json.dumps(pts, ensure_ascii=False)


@register.filter
def album_ref(obj):
    """Kartochkadan albomni ochish uchun JSON manzil: /albom/<model>/<pk>/."""
    from django.urls import reverse

    return reverse("core:album_json", kwargs={"model": obj._meta.model_name, "pk": obj.pk})


@register.filter
def album_n(obj, kind="foto"):
    """Albomdagi haqiqiy rasm / video soni."""
    if kind == "video":
        n = obj.videos.count() if hasattr(obj, "videos") else 0
        return n + (1 if (getattr(obj, "video_file", None) or getattr(obj, "video_url", "")) else 0)
    n = obj.photos.count() if hasattr(obj, "photos") else 0
    return n + (1 if main_image(obj) else 0)


@register.simple_tag(takes_context=True)
def filter_url(context, *pairs):
    """{% filter_url "yil" 2024 cat_param "" %} — joriy GET parametrlarini saqlab, berilganlarini almashtiradi
    (bo'sh qiymat — parametrni olib tashlash)."""
    kwargs = dict(zip(pairs[::2], pairs[1::2]))
    request = context.get("request")
    params = request.GET.copy() if request else None
    if params is None:
        return "?"
    params.pop("page", None)
    for k, v in kwargs.items():
        params.pop(k, None)
        if v not in (None, ""):
            params[k] = str(v)
    qs = params.urlencode()
    return "?" + qs if qs else "?"
