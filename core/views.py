import re
from types import SimpleNamespace
from urllib.parse import urlparse

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.i18n import COOKIE, LANG_CODES
from core.search import search_q

from core.models import (
    Achievement,
    Bookmark,
    Building,
    Category,
    Direction,
    Document,
    Education,
    Hero,
    Event,
    Highlight,
    ImportantDate,
    MediaItem,
    Person,
    PublicOrder,
    Region,
    StatCard,
    YearArchive,
)

PER_PAGE = 12


YEAR_START = 2017


def _years():
    """Filtr uchun yillar: 2017-yildan joriy yilgacha (har doim to'liq ro'yxat)."""
    from datetime import date as _date

    return list(range(max(_date.today().year, YEAR_START), YEAR_START - 1, -1))


def _active_year(request):
    y = request.GET.get("yil", "")
    return int(y) if y.isdigit() and YEAR_START <= int(y) <= 2100 else None


def _person_in_year(p, year):
    """Xizmat davri (masalan «2017 — 2020, 2026 — hozirgacha») shu yilni qamrab oladimi.
    Davri ko'rsatilmagan (amaldagi) rahbarlar faqat joriy yilda ko'rinadi."""
    from datetime import date as _date

    now = _date.today().year
    ranges = re.findall(r"(\d{4})\s*[—–-]\s*(\d{4}|hozirgacha)", p.service_period or "")
    if not ranges:
        return year == now
    return any(int(a) <= year <= (now if b == "hozirgacha" else int(b)) for a, b in ranges)


def _persons_in_year(qs, year):
    return qs.filter(pk__in=[p.pk for p in qs if _person_in_year(p, year)])


def _page(request, qs, per_page=PER_PAGE):
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page") or 1
    return paginator.get_page(page_number)


def _apply_year(qs, year, year_filter):
    if callable(year_filter):
        return year_filter(qs, year)
    return qs.filter(**{year_filter: year})


def _filters(request, qs, cat_field=None, choices=(), year_filter="year", cat_param="tur", cat_title="Kategoriya",
             default_cat=""):
    """Bo'lim sahifalari uchun yagona filtr: kategoriya + yil.

    Har bir variant yonida (boshqa filtr hisobga olingan holda) materiallar soni ko'rsatiladi.
    default_cat berilsa: "Barchasi" varianti bo'lmaydi, kategoriya tanlanmasa shu ishlatiladi,
    yillar ro'yxatida esa faqat shu kategoriyada material bor yillar chiqadi.
    Qaytaradi: (filtrlangan queryset, kontekst lug'ati).
    """
    choices = list(choices)
    cat = request.GET.get(cat_param, "")
    if cat not in {str(v) for v, _ in choices}:
        cat = default_cat
    year = _active_year(request)

    by_cat = qs.filter(**{cat_field: cat}) if (cat and cat_field) else qs
    by_year = _apply_year(qs, year, year_filter) if year else qs

    cat_options = []
    if cat_field:
        for val, label in choices:
            cat_options.append({"value": val, "label": label, "count": by_year.filter(**{cat_field: val}).count()})
    year_options = [{"value": y, "count": _apply_year(by_cat, y, year_filter).count()} for y in _years()]
    if default_cat:
        year_options = [o for o in year_options if o["count"] or o["value"] == year]

    result = _apply_year(by_cat, year, year_filter) if year else by_cat
    return result, {
        "cat_param": cat_param,
        "cat_title": cat_title,
        "cat_default": default_cat,
        "cat_options": cat_options,
        "active_cat": cat,
        "active_cat_label": dict((str(v), lbl) for v, lbl in choices).get(cat, ""),
        "cat_total": by_year.count(),
        "year_options": year_options,
        "year_total": by_cat.count(),
        "active_year": year,
        "years": _years(),
        "filtered_total": result.count(),
    }


def _regions_with_counts(model):
    regions = Region.objects.all()
    rows = []
    for r in regions:
        rows.append({"name": r.name, "count": model.objects.filter(region=r).count(), "is_other": r.is_other})
    return rows


def _latest_news(limit=5, year=None):
    items = []
    yf = {"year": year} if year else {}
    for m in Achievement.objects.filter(is_published=True, **yf).order_by("-date")[:limit]:
        items.append(
            {
                "date": m.date, "title": m.summary or m.title, "image": m.image,
                "url": m.get_absolute_url(), "type": "galaba",
            }
        )
    for e in Event.objects.filter(is_published=True, **yf).order_by("-date")[:limit]:
        items.append(
            {
                "date": e.date, "title": e.summary or e.title, "image": e.image,
                "url": e.get_absolute_url(), "type": "tadbir",
            }
        )
    items.sort(key=lambda x: x["date"] or __import__("datetime").date.min, reverse=True)
    return items[:limit]


def _all_materials(year=None):
    """Yil sahifasidagi barcha materiallarni birlashtirish."""
    out = []

    def add(items, kind):
        for o in items:
            dt = getattr(o, "date", None) or getattr(o, "handover_date", None)
            out.append(
                {
                    "kind": kind,
                    "kind_label": {**dict(Achievement.MATERIAL_TYPES), "jamoat": "Jamoat tartibi"}.get(kind, kind),
                    "title": o.title,
                    "date": dt,
                    "url": o.get_absolute_url(),
                    "image": getattr(o, "image", None),
                    "photos": getattr(o, "photo_count", 0),
                    "videos": getattr(o, "video_count", 0),
                    "docs": getattr(o, "doc_count", 0),
                    "views": getattr(o, "views", 0),
                }
            )

    f = {"is_published": True}
    if year:
        f["year"] = year

    add(Building.objects.filter(**({"year": year} if year else {}))[:200], "building")
    add(PublicOrder.objects.filter(**f)[:200], "jamoat")
    add(Event.objects.filter(**f)[:200], "tadbir")
    add(Achievement.objects.filter(**f)[:200], "galaba")
    add(Document.objects.filter(**f)[:200], "hujjat")
    for m in MediaItem.objects.filter(**({"year": year} if year else {}))[:200]:
        kind = "foto" if m.media_type == "photo" else "video"
        out.append(
            {
                "kind": kind,
                "kind_label": "Foto" if kind == "foto" else "Video",
                "title": m.title,
                "date": m.date,
                "url": m.get_absolute_url(),
                "image": m.image,
                "photos": 1 if kind == "foto" else 0,
                "videos": 1 if kind == "video" else 0,
                "docs": 0,
                "views": m.views,
            }
        )
    out.sort(key=lambda x: x["date"] or __import__("datetime").date.min, reverse=True)
    return out


# ---------------------------------------------------------------- Bosh sahifa
def _home_stats():
    """Bosh sahifa kartalari: avtomatik manbali kartalar qiymati bazadan hisoblanadi."""
    cards = list(StatCard.objects.all()[:6])
    for card in cards:
        card.value = card.current_value()
    return cards


def home(request):
    y = _active_year(request)
    buildings = Building.objects.all()
    achievements = Achievement.objects.filter(is_published=True)
    events = Event.objects.filter(is_published=True)
    if y:
        buildings = buildings.filter(year=y)
        achievements = achievements.filter(year=y)
        events = events.filter(year=y)
    ctx = {
        "active": "home",
        "active_year": y,
        "stats": _home_stats(),
        "buildings": buildings[:8],
        "achievements": achievements[:6],
        "events": events[:6],
        "latest": _latest_news(5, y),
        "regions": _regions_with_counts(Building),
        "years": _years(),
        "directions": Direction.objects.all()[:6],
    }
    return render(request, "core/home.html", ctx)


def landing(request):
    ctx = {"active": "landing", "directions": Direction.objects.all(), "years": _years()}
    return render(request, "core/landing.html", ctx)


# ------------------------------------------------------------ Yillar bo'yicha
def yillar(request, template_name="core/yillar.html"):
    year = request.GET.get("yil")
    active_year = int(year) if year and year.isdigit() else 2023
    archive = get_object_or_404(YearArchive, year=active_year)
    materials = _all_materials(active_year)

    kind = request.GET.get("tur")
    if kind:
        materials = [m for m in materials if m["kind"] == kind]

    search = request.GET.get("q", "").strip()
    if search:
        materials = [m for m in materials if search.lower() in m["title"].lower()]

    sort = request.GET.get("sort", "date")
    if sort == "views":
        materials.sort(key=lambda x: x["views"], reverse=True)

    counts = {}
    for m in _all_materials(active_year):
        counts[m["kind"]] = counts.get(m["kind"], 0) + 1
    counts["barcha"] = len(_all_materials(active_year))

    years = _years()
    prev_year = next((y for y in years if y < active_year), None)
    next_year = next((y for y in years if y > active_year), None)

    ctx = {
        "active": "yillar",
        "active_year": active_year,
        "archive": archive,
        **_year_media(archive),
        "materials": materials[:PER_PAGE],
        "counts": counts,
        "years": years,
        "prev_year": prev_year,
        "next_year": next_year,
        "dates": ImportantDate.objects.filter(date__year=active_year)[:5],
        "search": search,
        "kind": kind,
        "sort": sort,
        "total": len(materials),
    }
    return render(request, template_name, ctx)


def yil_detail(request, year):
    qs = YearArchive.objects.filter(year=year).first()
    if not qs:
        messages.info(request, "Bu yil uchun arxiv ma'lumoti topilmadi.")
        return redirect("core:yillar")
    request.GET = request.GET.copy()
    request.GET["yil"] = str(year)
    return yillar(request, template_name="core/yil_detail.html")


# ------------------------------------------------------------------ Binolar
def binolar(request):
    qs = Building.objects.all()
    years = _years()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "address", "description"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "building_type", Building.BUILDING_TYPES)
    active_year, turi = flt["active_year"], flt["active_cat"]

    ctx = {
        **flt,
        "active": "binolar",
        "page": _page(request, qs),
        "years": years,
        "active_year": active_year,
        "buildings_total": Building.objects.count(),
        "regions_count": Building.objects.values("region").distinct().count(),
        "capacity_total": sum(b.capacity for b in Building.objects.all()),
        "cost_total": sum(b.cost for b in Building.objects.all()),
        "photos_total": sum(b.photo_count for b in Building.objects.all()),
        "year_min": min(years) if years else "",
        "year_max": max(years) if years else "",
        "regions": _regions_with_counts(Building),
        "map_buildings": list(qs),
        "latest": Building.objects.order_by("-handover_date")[:4],
        "types": Building.BUILDING_TYPES,
        "q": q,
        "turi": turi,
    }
    return render(request, "core/binolar.html", ctx)


def bino_detail(request, slug):
    bino = get_object_or_404(Building, slug=slug)
    bino.views += 1
    bino.save(update_fields=["views"])

    related = []
    if bino.department:
        related += list(bino.department.gallery.all()[:5])
    related += list(MediaItem.objects.filter(event__isnull=False)[:5])

    ctx = {
        "active": "binolar",
        "bino": bino,
        "highlights": Highlight.objects.filter(building=bino),
        **_year_media(bino),
        "related": related[:5],
    }
    return render(request, "core/bino_detail.html", ctx)


# ------------------------------------------------------ Jamoat tartibini saqlash
def bolinmalar_redirect(request, slug=None):
    """Eski "Bo'linmalar tarixi" havolalari — bo'lim o'chirilgan, Jamoat tartibiga yo'naltiriladi."""
    return redirect("core:jamoat", permanent=True)


def jamoat(request):
    qs = PublicOrder.objects.filter(is_published=True)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "summary", "description"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "order_type", PublicOrder.ORDER_TYPES)
    allq = PublicOrder.objects.filter(is_published=True)
    by_type = dict(allq.order_by().values_list("order_type").annotate(n=Count("pk")))
    return render(request, "core/talim.html", {
        **flt,
        "active": "jamoat",
        "title": "Jamoat tartibini saqlash",
        "subtitle": "Milliy gvardiyaning jamoat tartibini saqlash, ommaviy tadbirlarda fuqarolar xavfsizligini ta'minlash, patrul-post xizmati, huquqbuzarliklarning oldini olish, obyektlarni qo'riqlash va fuqarolarga yordam ko'rsatish faoliyati.",
        "page": _page(request, qs),
        "types": PublicOrder.ORDER_TYPES,
        "tur": flt["active_cat"],
        "q": q,
        "years": flt["years"],
        "active_year": flt["active_year"],
        "type_key": "order_type",
        "card_color": "#1d4ed8",
        "empty_icon": "🛡️",
        "stats": [
            {"value": allq.count(), "label": "Jami materiallar", "icon": "🛡️", "color": "#1d4ed8"},
            {"value": by_type.get("tadbir", 0), "label": "Ommaviy tadbirlar", "icon": "🎉", "color": "#0f766e"},
            {"value": by_type.get("patrul", 0) + by_type.get("profilaktika", 0), "label": "Patrul va profilaktika", "icon": "🚓", "color": "#eab308"},
            {"value": by_type.get("yordam", 0), "label": "Fuqarolarga yordam", "icon": "🤝", "color": "#dc2626"},
        ],
        "panel_title": "Hududlar bo'yicha",
        "regions": [
            {"name": r["region__name"], "count": r["n"]}
            for r in allq.exclude(region=None).values("region__name").annotate(n=Count("pk")).order_by("-n")[:8]
        ],
        "mini_items": [
            {"title": o.title, "url": o.get_absolute_url(), "image": o.image, "meta": f"{o.date} · {o.get_order_type_display()}"}
            for o in allq[:5]
        ],
        "mini_title": "So'nggi qo'shilgan",
    })


def jamoat_detail(request, slug):
    obj = get_object_or_404(PublicOrder, slug=slug)
    obj.views += 1
    obj.save(update_fields=["views"])
    return render(request, "core/talim_detail.html", _detail_ctx(
        request, obj, active="jamoat",
        badge=obj.get_order_type_display(), badge_color="#1d4ed8",
        breadcrumbs=[{"title": "Jamoat tartibini saqlash", "url": "/jamoat-tartibi/"}, {"title": obj.title}],
        meta=[
            {"icon": "calendar", "value": obj.date},
            {"icon": "shield", "value": obj.get_order_type_display},
            {"icon": "pin", "value": obj.region or "—"},
        ],
        info=[
            {"icon": "calendar", "label": "Sana", "value": obj.date},
            {"icon": "shield", "label": "Yo'nalish", "value": obj.get_order_type_display},
            {"icon": "pin", "label": "Hudud", "value": obj.region or "—"},
            {"icon": "globe", "label": "Manba", "value": "milliygvardiya.uz" if obj.source_url else "—"},
        ],
        tags=[t.name for t in obj.tags.all()] + [str(obj.year)],
        related=_related_materials(PublicOrder.objects.filter(order_type=obj.order_type).exclude(pk=obj.pk)[:5]),
        related_url="/jamoat-tartibi/",
        bookmark="jamoat",
        **_year_media(obj),
    ))


# ------------------------------------------------------------- G'alabalar
TYPE_LABELS = {
    "xalqaro": "Xalqaro",
    "respublika": "Respublika",
    "sport": "Sport",
    "kasbiy": "Kasbiy mahorat",
    "innovatsion": "Innovatsion loyiha",
    "mukofot": "Mukofot",
    "taktik": "Taktik o'quvlar",
    "boshqa": "Boshqa",
}


def galabalar(request):
    qs = Achievement.objects.filter(is_published=True)
    turlar = list(Achievement.ACHIEVEMENT_TYPES)
    years = _years()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "summary", "description"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "achievement_type", turlar)
    turi, active_year = flt["active_cat"] or None, flt["active_year"]
    active_type = TYPE_LABELS.get(turi, turi) if turi else None

    distribution = []
    total = Achievement.objects.count() or 1
    for key, label in Achievement.ACHIEVEMENT_TYPES:
        c = Achievement.objects.filter(achievement_type=key).count()
        if c:
            distribution.append(
                {"label": label, "count": c, "percent": round(c * 100 / total), "key": key}
            )

    ctx = {
        **flt,
        "active": "galabalar",
        "page": _page(request, qs, 9),
        "types": turlar,
        "type_labels": TYPE_LABELS,
        "active_type": active_type,
        "turi": turi,
        "years": years,
        "active_year": active_year,
        "q": q,
        "total": Achievement.objects.count(),
        "xalqaro": Achievement.objects.filter(achievement_type="xalqaro").count(),
        "respublika": Achievement.objects.filter(achievement_type="respublika").count(),
        "jamoaviy": Event.objects.count(),
        "eng_muhim": Achievement.objects.filter(is_featured=True).count() or 28,
        "latest": Achievement.objects.order_by("-date")[:5],
        "distribution": distribution,
        "regions": _regions_with_counts(Achievement),
    }
    return render(request, "core/galabalar.html", ctx)


def galaba_detail(request, slug):
    obj = get_object_or_404(Achievement, slug=slug)
    obj.views += 1
    obj.save(update_fields=["views"])
    ctx = _detail_ctx(
        request, obj, active="galabalar",
        badge=TYPE_LABELS.get(obj.achievement_type, obj.achievement_type), badge_color="#b45309",
        breadcrumbs=[{"title": "Erishilgan g'alabalar", "url": "/galabalar/"}, {"title": obj.title}],
        meta=[
            {"icon": "calendar", "value": obj.date},
            {"icon": "pin", "value": obj.region or "O'zbekiston"},
            {"icon": "trophy", "value": obj.get_achievement_type_display},
        ],
        info=[
            {"icon": "calendar", "label": "Sana", "value": obj.date},
            {"icon": "pin", "label": "Hudud", "value": obj.region or "—"},
            {"icon": "trophy", "label": "Yutuq turi", "value": obj.get_achievement_type_display},
            {"icon": "camera", "label": "Materiallar soni", "value": f"{obj.photo_count + obj.video_count + obj.doc_count} ta (foto {obj.photo_count}, video {obj.video_count}, hujjat {obj.doc_count})"},
        ],
        tags=[t.name for t in obj.tags.all()] + ([str(obj.year)] if obj.year else []),
        related=_related_materials(Achievement.objects.filter(achievement_type=obj.achievement_type).exclude(pk=obj.pk)[:5]),
        related_url="/galabalar/",
        bookmark="galaba",
        **_year_media(obj),
    )
    return render(request, "core/galaba_detail.html", ctx)


def _related_materials(qs):
    return [
        {"title": o.title, "url": o.get_absolute_url(), "image": o.image, "date": o.date, "meta": ""}
        for o in qs
    ]


def _gallery(obj, extra=(), full=False):
    """Obyektning o'z rasmlari: asosiy rasm + fotoalbom (+ qo'shimcha media).
    full=False bo'lsa, bitta rasm galereya hisoblanmaydi (bo'sh ro'yxat)."""
    items = []
    main = getattr(obj, "image", None) or getattr(obj, "photo", None)
    if main:
        items.append(SimpleNamespace(image=main, title=str(obj)))
    photos = getattr(obj, "photos", None)
    if photos is not None:
        items += [p for p in photos.all()[:500] if p.image]
    items += list(extra)
    return items if (full or len(items) > 1) else []


def _by_year(items):
    """Yil bo'yicha (yangisi oldin) tartiblaydi; yili yo'q asosiy surat boshida qoladi."""
    def key(it):
        if not hasattr(it, "year"):
            return (0, 0)
        return (1, -(it.year or 0))
    return sorted(items, key=key)


def _year_media(obj, extra=()):
    """Yil bo'yicha guruhlanadigan galereya va videolar."""
    photos = _by_year(_gallery(obj, extra, full=True))
    return {"gallery": photos if len(photos) > 1 else [], "album_photos": photos,
            "videos": _by_year(list(obj.videos.all()))}


def _source_info(obj):
    url = getattr(obj, "source_url", "")
    if not url:
        return []
    host = urlparse(url).netloc.replace("www.", "")
    return [{"icon": "globe", "label": "Manba", "value": format_html('<a href="{}" target="_blank" rel="noopener" class="text-accent">{}</a>', url, host)}]


def _detail_ctx(request, obj, **kwargs):
    ctx = {"obj": obj, "active": kwargs.pop("active")}
    ctx.update(kwargs)
    if "info" in ctx:
        ctx["info"] = list(ctx["info"]) + _source_info(obj)
    return ctx


# ----------------------------------------------------------------- Tadbirlar
def tadbirlar(request):
    qs = Event.objects.filter(is_published=True)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "summary", "description", "location"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "event_type", Event.EVENT_TYPES)
    tur, years, active_year = flt["active_cat"], flt["years"], flt["active_year"]
    return render(request, "core/tadbirlar.html", {
        **flt,
        "active": "tadbirlar",
        "title": "Tadbirlar va marosimlar",
        "subtitle": "Milliy gvardiyaning tantanali marosimlari, musobaqalari, tashriflari, treninglari va boshqa tadbirlari arxivi.",
        "page": _page(request, qs),
        "types": Event.EVENT_TYPES,
        "tur": tur,
        "q": q,
        "years": years,
        "active_year": active_year,
        "type_key": "event_type",
        "card_color": "#0f766e",
        "empty_icon": "🎉",
        "stats": [
            {"value": Event.objects.count(), "label": "Jami tadbirlar", "icon": "👥", "color": "#0f766e"},
            {"value": Event.objects.filter(event_type="marosim").count(), "label": "Marosimlar", "icon": "🎗️", "color": "#1d4ed8"},
            {"value": Event.objects.filter(event_type="musobaqa").count(), "label": "Musobaqalar", "icon": "🏆", "color": "#eab308"},
            {"value": len(years), "label": "Arxiv yillari", "icon": "📅", "color": "#8b5cf6"},
        ],
        "panel_title": "Hududlar bo'yicha tadbirlar",
        "regions": _regions_with_counts(Event),
        "map": True,
        "mini_items": [
            {"title": e.title, "url": e.get_absolute_url(), "image": e.image, "meta": e.date}
            for e in Event.objects.order_by("-date")[:5]
        ],
        "mini_title": "So'nggi tadbirlar",
    })


def tadbir_detail(request, slug):
    obj = get_object_or_404(Event, slug=slug)
    obj.views += 1
    obj.save(update_fields=["views"])
    return render(request, "core/tadbir_detail.html", _detail_ctx(
        request, obj, active="tadbirlar",
        badge=obj.get_event_type_display(), badge_color="#0f766e",
        breadcrumbs=[{"title": "Tadbirlar va marosimlar", "url": "/tadbirlar/"}, {"title": obj.title}],
        meta=[
            {"icon": "calendar", "value": obj.date},
            {"icon": "pin", "value": obj.location or obj.region or "—"},
            {"icon": "users", "value": obj.department or "Milliy gvardiya"},
        ],
        info=[
            {"icon": "calendar", "label": "Sana", "value": obj.date},
            {"icon": "pin", "label": "Joylashuv", "value": obj.location or "—"},
            {"icon": "users", "label": "Tadbir turi", "value": obj.get_event_type_display},
            {"icon": "camera", "label": "Materiallar soni", "value": f"{obj.photo_count + obj.video_count + obj.doc_count} ta"},
        ],
        tags=[t.name for t in obj.tags.all()] + [str(obj.year)],
        related=_related_materials(Event.objects.filter(event_type=obj.event_type).exclude(pk=obj.pk)[:5]),
        related_url="/tadbirlar/",
        bookmark="tadbir",
        **_year_media(obj, [m for m in obj.gallery.all()[:8] if m.image]),
    ))


# ------------------------------------------------------- Ta'minot yo'nalishlari
def talim(request):
    qs = Education.objects.filter(is_published=True)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "summary", "description"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "edu_type", Education.EDU_TYPES)
    tur, years, active_year = flt["active_cat"], flt["years"], flt["active_year"]
    allq = Education.objects.filter(is_published=True)
    by_type = dict(allq.order_by().values_list("edu_type").annotate(n=Count("pk")))
    return render(request, "core/talim.html", {
        **flt,
        "active": "talim",
        "title": "Ta'minot yo'nalishlari",
        "subtitle": "Milliy gvardiyaning moddiy-texnik ta'minoti: kiyim-kechak, qurol-aslaha va texnika, tibbiy xizmat, harbiy xizmatchilarga uy-joy topshirish hamda yangi bino va inshootlarning ochilishi.",
        "page": _page(request, qs),
        "types": Education.EDU_TYPES,
        "tur": tur,
        "q": q,
        "years": years,
        "active_year": active_year,
        "type_key": "edu_type",
        "card_color": "#0f766e",
        "empty_icon": "📦",
        "stats": [
            {"value": allq.count(), "label": "Jami materiallar", "icon": "📦", "color": "#0f766e"},
            {"value": by_type.get("uy_joy", 0), "label": "Uy-joy topshirish", "icon": "🏠", "color": "#1d4ed8"},
            {"value": by_type.get("tibbiyot", 0), "label": "Tibbiy ta'minot", "icon": "🩺", "color": "#dc2626"},
            {"value": by_type.get("bino", 0), "label": "Yangi binolar", "icon": "🏛️", "color": "#eab308"},
        ],
        "panel_title": "Hududlar bo'yicha",
        "regions": [
            {"name": r["region__name"], "count": r["n"]}
            for r in allq.exclude(region=None).values("region__name").annotate(n=Count("pk")).order_by("-n")[:8]
        ],
        "mini_items": [
            {"title": o.title, "url": o.get_absolute_url(), "image": o.image, "meta": f"{o.date} · {o.get_edu_type_display()}"}
            for o in allq[:5]
        ],
        "mini_title": "So'nggi qo'shilgan",
    })


def talim_detail(request, slug):
    obj = get_object_or_404(Education, slug=slug)
    obj.views += 1
    obj.save(update_fields=["views"])
    return render(request, "core/talim_detail.html", _detail_ctx(
        request, obj, active="talim",
        badge=obj.get_edu_type_display(), badge_color="#0f766e",
        breadcrumbs=[{"title": "Ta'minot yo'nalishlari", "url": "/talim/"}, {"title": obj.title}],
        meta=[
            {"icon": "calendar", "value": obj.date},
            {"icon": "box", "value": obj.get_edu_type_display},
            {"icon": "pin", "value": obj.region or "—"},
        ],
        info=[
            {"icon": "calendar", "label": "Sana", "value": obj.date},
            {"icon": "box", "label": "Ta'minot turi", "value": obj.get_edu_type_display},
            {"icon": "pin", "label": "Hudud", "value": obj.region or "—"},
            {"icon": "globe", "label": "Manba", "value": "milliygvardiya.uz" if obj.source_url else "—"},
        ],
        tags=[t.name for t in obj.tags.all()] + [str(obj.year)],
        related=_related_materials(Education.objects.filter(edu_type=obj.edu_type).exclude(pk=obj.pk)[:5]),
        related_url="/talim/",
        **_year_media(obj),
    ))


# ------------------------------------------------------------------ Galereya
def galereya(request):
    qs = MediaItem.objects.prefetch_related("photos")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "description"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    turi = request.GET.get("tur")
    if turi in ("photo", "video"):
        qs = qs.filter(media_type=turi)
    else:
        turi = None
    qs, flt = _filters(request, qs, "topic", MediaItem.TOPICS, cat_param="kategoriya")
    years, active_year = flt["years"], flt["active_year"]
    return render(request, "core/galereya.html", {
        **flt,
        "active": "galereya",
        "title": "Foto va videoarxiv",
        "subtitle": "Milliy gvardiyaning tadbirlari, mashg'ulotlari, yangi binolari va xizmat faoliyatidan olingan foto hamda video materiallar arxivi.",
        "page": _page(request, qs),
        "q": q,
        "types": MediaItem.MEDIA_TYPES,
        "tur": turi,
        "years": years,
        "active_year": active_year,
        "type_key": "media_type",
        "card_color": "#0e7490",
        "grid_class": "grid--4",
        "empty_icon": "🖼️",
        "stats": [
            {"value": MediaItem.objects.filter(media_type="photo").count(), "label": "Foto materiallar", "icon": "📷", "color": "#0e7490"},
            {"value": MediaItem.objects.filter(media_type="video").count(), "label": "Video materiallar", "icon": "🎥", "color": "#1d4ed8"},
            {"value": len(years), "label": "Arxiv yillari", "icon": "📅", "color": "#eab308"},
            {"value": MediaItem.objects.count(), "label": "Jami materiallar", "icon": "🗂️", "color": "#7c3aed"},
        ],
        "mini_items": [
            {"title": m.title, "url": m.get_absolute_url(), "image": m.image, "meta": m.date}
            for m in MediaItem.objects.order_by("-date")[:5]
        ],
        "mini_title": "So'nggi materiallar",
    })


# ----------------------------------------------------------------- Hujjatlar
def hujjatlar(request):
    qs = Document.objects.filter(is_published=True)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "doc_number", "summary", "description"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "doc_type", Document.DOC_TYPES)
    tur, years, active_year = flt["active_cat"], flt["years"], flt["active_year"]
    return render(request, "core/hujjatlar.html", {
        **flt,
        "active": "hujjatlar",
        "title": "Hujjatlar va relikiyalar",
        "subtitle": "Milliy gvardiyaning normativ-huquqiy hujjatlari, buyruqlari, farmoyishlari, tarixiy hujjatlari va relikiyalar arxivi.",
        "page": _page(request, qs),
        "types": Document.DOC_TYPES,
        "tur": tur,
        "q": q,
        "years": years,
        "active_year": active_year,
        "type_key": "doc_type",
        "card_color": "#6d28d9",
        "grid_class": "grid--4",
        "empty_icon": "📄",
        "stats": [
            {"value": Document.objects.count(), "label": "Jami hujjatlar", "icon": "📄", "color": "#6d28d9"},
            {"value": Document.objects.filter(doc_type="hujjat").count(), "label": "Rasmiy hujjatlar", "icon": "🏛️", "color": "#1d4ed8"},
            {"value": Document.objects.filter(doc_type="relikiya").count(), "label": "Relikiyalar", "icon": "🏺", "color": "#b45309"},
            {"value": len(years), "label": "Arxiv yillari", "icon": "📅", "color": "#0f766e"},
        ],
        "panel_title": "Hujjat turlari bo'yicha",
        "mini_items": [
            {"title": d.title, "url": d.get_absolute_url(), "image": d.image, "meta": f"{d.doc_number or d.date}"}
            for d in Document.objects.order_by("-date")[:5]
        ],
        "mini_title": "So'nggi hujjatlar",
    })


def _word_kind(f):
    """Word faylning turi: 'html' (lex.uz .doc / .htm), 'docx' yoki 'binary' (eski .doc)."""
    if not f:
        return ""
    name = f.name.lower()
    try:
        with f.open("rb") as fh:
            head = fh.read(512)
    except (OSError, ValueError):
        return ""
    if head[:4] == b"PK" or name.endswith(".docx"):
        return "docx"
    if b"<html" in head.lower() or name.endswith((".htm", ".html")):
        return "html"
    return "binary"


DOC_KIND_LABELS = {
    "Qonuni": "Qonun", "Farmoni": "Prezident Farmoni", "Prezidentining qarori": "Prezident qarori",
    "Prezidentining Qarori": "Prezident qarori", "Vazirlar Mahkamasining qarori": "Vazirlar Mahkamasi qarori",
}


def hujjat_detail(request, slug):
    obj = get_object_or_404(Document, slug=slug)
    obj.views += 1
    obj.save(update_fields=["views"])
    kind = next((v for k, v in DOC_KIND_LABELS.items() if k in (obj.summary or "")), obj.get_doc_type_display())
    fmt = lambda v: v or "—"  # noqa: E731
    return render(request, "core/hujjat_detail.html", _detail_ctx(
        request, obj, active="hujjatlar",
        badge=kind, badge_color="#6d28d9",
        breadcrumbs=[{"title": "Hujjatlar va relikiyalar", "url": "/hujjatlar/"}, {"title": obj.title}],
        meta=[
            {"icon": "calendar", "value": obj.date},
            {"icon": "file", "value": obj.doc_number or obj.get_doc_type_display},
            {"icon": "users", "value": obj.issuer or obj.department or "Milliy gvardiya"},
        ],
        info=[
            {"icon": "file", "label": "Hujjat turi", "value": kind},
            {"icon": "file", "label": "Hujjat raqami", "value": fmt(obj.doc_number)},
            {"icon": "calendar", "label": "Qabul qilingan sana", "value": fmt(obj.date)},
            {"icon": "calendar", "label": "Kuchga kirgan sana", "value": fmt(obj.effective_date)},
            {"icon": "users", "label": "Qabul qilgan organ", "value": fmt(obj.issuer)},
            {"icon": "shield", "label": "Holati", "value": fmt(obj.status)},
            {"icon": "flag", "label": "Rasmiy nashr manbasi", "value": fmt(obj.publication)},
            {"icon": "camera", "label": "Sahifalar soni", "value": obj.pages or "—"},
        ],
        tags=[t.name for t in obj.tags.all()] + [str(obj.year)],
        related=_related_materials(Document.objects.exclude(pk=obj.pk)[:5]),
        related_url="/hujjatlar/",
        bookmark="hujjat",
        **_year_media(obj),
        doc_kind=kind,
        word_kind=_word_kind(obj.file_word),
    ))


def hujjat_word(request, slug):
    """Word (HTML formatidagi .doc) hujjatni sayt ichida xavfsiz ko'rsatish."""
    from django.http import Http404, HttpResponse

    obj = get_object_or_404(Document, slug=slug)
    if _word_kind(obj.file_word) != "html":
        raise Http404
    with obj.file_word.open("rb") as fh:
        raw = fh.read()
    m = re.search(rb"charset=[\"']?([\w-]+)", raw[:2000])
    try:
        text = raw.decode(m.group(1).decode() if m else "utf-8")
    except (LookupError, UnicodeDecodeError):
        text = raw.decode("utf-8", "ignore")
    # xavfsizlik: skript va faol elementlarni olib tashlash
    text = re.sub(r"<(script|iframe|object|embed|form)\b.*?</\1\s*>", "", text, flags=re.S | re.I)
    text = re.sub(r"<(script|iframe|object|embed|link|meta http-equiv=.refresh)[^>]*>", "", text, flags=re.I)
    text = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", text, flags=re.I)
    text = re.sub(r"javascript:", "", text, flags=re.I)
    paper = ("<style>html{background:#e9edf3}body{max-width:820px;margin:24px auto;padding:56px 64px;background:#fff;"
             "color:#111;box-shadow:0 4px 24px rgba(0,0,0,.18);font-family:'Times New Roman',serif;line-height:1.45}"
             "@media(max-width:700px){body{margin:0;padding:20px}}</style>")
    text = re.sub(r"</head>", paper + "</head>", text, count=1, flags=re.I) if re.search(r"</head>", text, re.I) else paper + text
    resp = HttpResponse(text, content_type="text/html; charset=utf-8")
    resp["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data: https:; font-src data: https:"
    resp["X-Frame-Options"] = "SAMEORIGIN"
    return resp


# ------------------------------------------------------------------ Shaxslar
def shaxslar(request):
    qs = Person.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["full_name", "position", "bio", "awards"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "person_type", Person.PERSON_TYPES, year_filter=_persons_in_year)
    tur, active_year = flt["active_cat"], flt["active_year"]
    return render(request, "core/shaxslar.html", {
        **flt,
        "active": "shaxslar",
        "years": _years(),
        "active_year": active_year,
        "title": "Rahbarlar va shaxslar",
        "subtitle": "Milliy gvardiya qo‘mondonligi, hududiy boshqarmalar rahbarlari va tarixiy shaxslarning biografiyalar arxivi.",
        "page": _page(request, qs),
        "types": Person.PERSON_TYPES,
        "tur": tur,
        "q": q,
        "type_key": "person_type",
        "card_color": "#0f766e",
        "grid_class": "grid--4",
        "empty_icon": "👤",
        "stats": [
            {"value": Person.objects.count(), "label": "Jami shaxslar", "icon": "👤", "color": "#0f766e"},
            {"value": Person.objects.filter(person_type="rahbar").count(), "label": "Rahbarlar", "icon": "⭐", "color": "#1d4ed8"},
            {"value": Person.objects.filter(position__icontains="boshqarma").count(), "label": "Hududiy boshqarma rahbarlari", "icon": "📍", "color": "#eab308"},
            {"value": Person.objects.filter(person_type="tarixiy").count(), "label": "Tarixiy shaxslar", "icon": "📜", "color": "#7c3aed"},
        ],
        "panel_title": "Turlar bo'yicha",
        "mini_items": [
            {"title": p.full_name, "url": p.get_absolute_url(), "image": p.photo, "meta": p.position}
            for p in Person.objects.order_by("order")[:6]
        ],
        "mini_title": "Mashhur shaxslar",
    })


def shaxs_detail(request, slug):
    obj = get_object_or_404(Person, slug=slug)
    obj.views += 1
    obj.save(update_fields=["views"])
    return render(request, "core/shaxs_detail.html", _detail_ctx(
        request, obj, active="shaxslar",
        badge=obj.get_person_type_display(), badge_color="#0f766e",
        breadcrumbs=[{"title": "Rahbarlar va shaxslar", "url": "/shaxslar/"}, {"title": obj.full_name}],
        meta=[
            {"icon": "user", "value": obj.full_name},
            {"icon": "calendar", "value": obj.service_period or obj.birth_date},
            {"icon": "building", "value": obj.position or "—"},
        ],
        info=[
            {"icon": "user", "label": "F.I.Sh.", "value": obj.full_name},
            {"icon": "building", "label": "Lavozim", "value": obj.position or "—"},
            {"icon": "calendar", "label": "Tug'ilgan sana", "value": obj.birth_date or "—"},
            {"icon": "clock", "label": "Xizmat davri", "value": obj.service_period or "—"},
            {"icon": "star", "label": "Mukofotlar", "value": obj.awards or "—"},
        ],
        tags=[obj.get_person_type_display()] + ([str(obj.department)] if obj.department else []),
        related=[
            {"title": p.full_name, "url": p.get_absolute_url(), "image": p.photo, "date": p.service_period, "meta": p.position}
            for p in Person.objects.exclude(pk=obj.pk)[:5]
        ],
        related_url="/shaxslar/",
        bookmark="shaxs",
        **_year_media(obj),
    ))


# ---------------------------------------------------------- Bizning qahramonlar
def qahramonlar(request):
    qs = Hero.objects.filter(is_published=True).select_related("region")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["full_name", "rank", "feat", "bio", "awards", "birth_place"], q,
                                getattr(request, "LANGUAGE_CODE", "uz")))
    region = request.GET.get("hudud")
    if region and region.isdigit():
        qs = qs.filter(region_id=int(region))
    qs, flt = _filters(request, qs, "category", Hero.CATEGORIES, default_cat="sportchi")
    tur, active_year = flt["active_cat"] or None, flt["active_year"]
    all_heroes = Hero.objects.filter(is_published=True)
    regions = [
        {"name": r.name, "count": r.c}
        for r in Region.objects.filter(heroes__is_published=True).annotate(c=Count("heroes")).order_by("-c")
    ]
    return render(request, "core/qahramonlar.html", {
        **flt,
        "active": "qahramonlar",
        "title": "Bizning qahramonlar",
        "subtitle": "Xizmat vazifasini bajarish chog‘ida jasorat ko‘rsatib halok bo‘lgan gvardiyachilar, xalqaro maydonda g‘alaba qozongan sportchilarimiz va davlat mukofotlari bilan taqdirlangan safdoshlarimiz.",
        "page": _page(request, qs, 24),
        "q": q,
        "types": Hero.CATEGORIES,
        "tur": tur,
        "years": _years(),
        "active_year": active_year,
        "card_color": "#b45309",
        "card_text": "Qahramon",
        "grid_class": "grid--4 grid--heroes",
        "empty_icon": "🎖️",
        "hero_gold": True,
        "stats": [
            {"value": all_heroes.count(), "label": "Jami", "icon": "🎖️", "color": "#eab308"},
            {"value": all_heroes.filter(category="halok").count(), "label": "Halok bo'lgan qahramonlar", "icon": "🕯️", "color": "#b45309"},
            {"value": all_heroes.filter(category="sportchi").count(), "label": "Sportchilarimiz", "icon": "🥇", "color": "#16a34a"},
            {"value": all_heroes.filter(category="mukofot").count(), "label": "Davlat mukofoti sohiblari", "icon": "🏅", "color": "#7c3aed"},
        ],
        "panel_title": "Hududlar bo'yicha",
        "regions": regions,
        "mini_items": [
            {"title": h.full_name, "url": h.get_absolute_url(), "image": h.photo, "meta": h.life_years or h.rank}
            for h in all_heroes.filter(category="halok").order_by("-death_date")[:6]
        ],
        "mini_title": "Xotira sahifasi",
    })


def qahramon_detail(request, slug):
    obj = get_object_or_404(Hero, slug=slug, is_published=True)
    obj.views += 1
    obj.save(update_fields=["views"])
    fmt_date = lambda v: v or "—"  # noqa: E731
    return render(request, "core/qahramon_detail.html", _detail_ctx(
        request, obj, active="qahramonlar",
        badge=obj.get_category_display(), badge_color="#b45309",
        breadcrumbs=[{"title": "Bizning qahramonlar", "url": "/qahramonlar/"}, {"title": obj.full_name}],
        **_year_media(obj),
        meta=[
            {"icon": "user", "value": obj.full_name},
            {"icon": "calendar", "value": obj.life_years or "—"},
            {"icon": "medal", "value": obj.rank or obj.get_category_display()},
        ],
        info=[
            {"icon": "user", "label": "F.I.Sh.", "value": obj.full_name},
            {"icon": "shield", "label": "Harbiy unvon / lavozim", "value": obj.rank or "—"},
            {"icon": "calendar", "label": "Tug'ilgan sana", "value": fmt_date(obj.birth_date)},
            {"icon": "pin", "label": "Tug'ilgan joyi", "value": obj.birth_place or "—"},
            *([{"icon": "flag", "label": "Halok bo'lgan sana", "value": fmt_date(obj.death_date)}] if obj.category == "halok" else []),
            {"icon": "map", "label": "Xizmat qilgan hudud", "value": obj.region or "—"},
            {"icon": "star", "label": "Mukofotlar", "value": obj.awards or "—"},
        ],
        tags=[obj.get_category_display()] + ([str(obj.region)] if obj.region else []),
        related=[
            {"title": h.full_name, "url": h.get_absolute_url(), "image": h.photo, "date": h.life_years, "meta": h.rank}
            for h in Hero.objects.filter(is_published=True, category=obj.category).exclude(pk=obj.pk)[:5]
        ],
        related_url="/qahramonlar/",
        bookmark="qahramon",
    ))


# ------------------------------------------------------------ Muhim sanalar
def sanalar(request):
    qs = ImportantDate.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(search_q(["title", "description"], q, getattr(request, "LANGUAGE_CODE", "uz")))
    qs, flt = _filters(request, qs, "date_type", ImportantDate.DATE_TYPES)
    years, active_year = flt["years"], flt["active_year"]
    return render(request, "core/sanalar.html", {
        **flt,
        "active": "sanalar",
        "title": "Muhim sanalar",
        "subtitle": "Milliy gvardiya tarixidagi muhim voqealar, tashkil etilgan kunlar, tantanalar va esda qolishi kerak bo'lgan sanalar.",
        "page": _page(request, qs),
        "q": q,
        "years": years,
        "active_year": active_year,
        "card_color": "#b45309",
        "grid_class": "grid--3",
        "types": ImportantDate.DATE_TYPES,
        "type_key": "date_type",
        "card_text": "Muhim sana",
        "empty_icon": "📅",
        "stats": [
            {"value": ImportantDate.objects.count(), "label": "Jami muhim sanalar", "icon": "📅", "color": "#b45309"},
            {"value": len(years), "label": "Arxiv yillari", "icon": "🗂️", "color": "#1d4ed8"},
            {"value": YearArchive.objects.count(), "label": "Yillar arxivi", "icon": "🏛️", "color": "#0f766e"},
            {"value": Event.objects.count(), "label": "Tadbirlar", "icon": "👥", "color": "#7c3aed"},
        ],
        "panel_title": "Yillar bo'yicha tarix",
        "mini_items": [
            {"title": y.title, "url": y.get_absolute_url(), "image": y.image, "meta": f"{y.year}-yil arxivi"}
            for y in YearArchive.objects.all()[:6]
        ],
        "mini_title": "Yillar arxivi",
    })


def sana_detail(request, slug):
    obj = get_object_or_404(ImportantDate, slug=slug)
    return render(request, "core/sana_detail.html", _detail_ctx(
        request, obj, active="sanalar",
        badge="Muhim sana", badge_color="#b45309",
        **_year_media(obj),
        breadcrumbs=[{"title": "Muhim sanalar", "url": "/sanalar/"}, {"title": obj.title}],
        meta=[
            {"icon": "calendar", "value": obj.date},
            {"icon": "star", "value": "Muhim sana"},
        ],
        info=[
            {"icon": "calendar", "label": "Sana", "value": obj.date},
            {"icon": "star", "label": "Turi", "value": "Muhim sana"},
            {"icon": "file", "label": "Tegishli tadbir", "value": obj.event or "—"},
        ],
        tags=[str(obj.date.year)],
        related=[
            {"title": d.title, "url": d.get_absolute_url(), "image": d.image, "date": d.date, "meta": ""}
            for d in ImportantDate.objects.exclude(pk=obj.pk)[:5]
        ],
        related_url="/sanalar/",
    ))


def media_detail(request, slug):
    obj = get_object_or_404(MediaItem, slug=slug)
    obj.views += 1
    obj.save(update_fields=["views"])
    return render(request, "core/media_detail.html", _detail_ctx(
        request, obj, active="galereya",
        badge=obj.get_media_type_display(), badge_color="#0e7490",
        breadcrumbs=[{"title": "Foto va videoarxiv", "url": "/galereya/"}, {"title": obj.title}],
        **_year_media(obj),
        meta=[
            {"icon": "calendar", "value": obj.date},
            {"icon": "camera" if obj.media_type == "photo" else "video", "value": obj.get_media_type_display},
            {"icon": "eye", "value": obj.views},
        ],
        info=[
            {"icon": "calendar", "label": "Sana", "value": obj.date},
            {"icon": "camera", "label": "Turi", "value": obj.get_media_type_display},
            {"icon": "users", "label": "Tadbir", "value": obj.event or "—"},
            {"icon": "eye", "label": "Ko'rishlar", "value": obj.views},
        ],
        tags=[str(obj.year), obj.get_media_type_display()],
        related=[
            {"title": m.title, "url": m.get_absolute_url(), "image": m.image, "date": m.date, "meta": ""}
            for m in MediaItem.objects.exclude(pk=obj.pk)[:5]
        ],
        related_url="/galereya/",
    ))


# ------------------------------------------------------------- Yo'nalishlar
def yonalishlar(request):
    ctx = {"active": "yonalishlar", "directions": Direction.objects.all()}
    return render(request, "core/yonalishlar.html", ctx)


# ------------------------------------------------------------------ Qidiruv
def qidiruv(request):
    q = request.GET.get("q", "").strip()
    lang = getattr(request, "LANGUAGE_CODE", "uz")
    results = []
    if q:
        def add(qs, kind, title, date=None, image="image", meta=None, limit=12):
            for o in qs[:limit]:
                results.append({
                    "kind": kind,
                    "title": getattr(o, title),
                    "date": getattr(o, date) if date else None,
                    "url": o.get_absolute_url(),
                    "image": getattr(o, image, None),
                    "meta": meta(o) if meta else "",
                })

        S = lambda fields: search_q(fields, q, lang)  # noqa: E731
        add(Building.objects.filter(S(["title", "address", "description"])), "Yangi bino", "title", "handover_date", meta=lambda o: o.address or o.get_building_type_display())
        add(PublicOrder.objects.published().filter(S(["title", "summary", "description", "body"])), "Jamoat tartibi", "title", "date", meta=lambda o: o.get_order_type_display())
        add(Achievement.objects.published().filter(S(["title", "summary", "description", "body"])), "G'alaba", "title", "date", meta=lambda o: TYPE_LABELS.get(o.achievement_type, ""))
        add(Event.objects.published().filter(S(["title", "summary", "description", "body", "location"])), "Tadbir", "title", "date", meta=lambda o: o.location)
        add(Education.objects.published().filter(S(["title", "summary", "description", "body"])), "Ta'minot", "title", "date", meta=lambda o: o.get_edu_type_display())
        add(Document.objects.published().filter(S(["title", "doc_number", "summary", "description"])), "Hujjat", "title", "date", meta=lambda o: o.doc_number)
        add(Person.objects.filter(S(["full_name", "position", "bio", "awards"])), "Shaxs", "full_name", "birth_date", image="photo", meta=lambda o: o.position)
        add(Hero.objects.filter(is_published=True).filter(S(["full_name", "rank", "feat", "bio", "awards", "birth_place"])), "Qahramon", "full_name", "death_date", image="photo", meta=lambda o: o.life_years or o.rank)
        add(ImportantDate.objects.filter(S(["title", "description"])), "Muhim sana", "title", "date")
        add(MediaItem.objects.filter(S(["title", "description"])), "Media", "title", "date", meta=lambda o: o.get_media_type_display())
        years = [int(t) for t in re.findall(r"(?<!\d)((?:19|20)\d\d)(?!\d)", q)]
        for y in YearArchive.objects.filter(Q(year__in=years) | S(["title", "subtitle", "description"])):
            results.insert(0, {"kind": "Yil", "title": y.title, "date": None, "url": y.get_absolute_url(), "image": y.image, "meta": str(y.year)})
        if years:
            # yil yozilgan bo'lsa — o'sha yildagi materiallar ham
            seen = {r["url"] for r in results}
            for model, kind in ((Achievement, "G'alaba"), (Event, "Tadbir"), (Education, "Ta'minot"), (PublicOrder, "Jamoat tartibi"), (Document, "Hujjat")):
                for o in model.objects.published().filter(year__in=years)[:6]:
                    if o.get_absolute_url() not in seen:
                        results.append({"kind": kind, "title": o.title, "date": o.date, "url": o.get_absolute_url(), "image": o.image, "meta": ""})
            for o in Building.objects.filter(year__in=years)[:6]:
                if o.get_absolute_url() not in seen:
                    results.append({"kind": "Yangi bino", "title": o.title, "date": o.handover_date, "url": o.get_absolute_url(), "image": o.image, "meta": o.address})
    ctx = {"active": "qidiruv", "q": q, "results": results, "count": len(results)}
    return render(request, "core/qidiruv.html", ctx)


# --------------------------------------------------------------- Saqlanganlar
def saqlanganlar(request):
    key = request.session.session_key
    saved = Bookmark.objects.filter(session_key=key)
    registry = {
        "bino": (Building, "Yangi bino"),
        "jamoat": (PublicOrder, "Jamoat tartibi"),
        "galaba": (Achievement, "G'alaba"),
        "tadbir": (Event, "Tadbir"),
        "hujjat": (Document, "Hujjat"),
        "talim": (Education, "Ta'minot"),
        "shaxs": (Person, "Shaxs"),
        "qahramon": (Hero, "Qahramon"),
        "media": (MediaItem, "Media"),
    }
    items = []
    for s in saved:
        entry = registry.get(s.content_type)
        if not entry:
            continue
        model, kind = entry
        obj = model.objects.filter(pk=s.object_id).first()
        if not obj:
            s.delete()
            continue
        items.append({
            "kind": kind,
            "ctype": s.content_type,
            "obj": obj,
            "url": obj.get_absolute_url(),
            "image": getattr(obj, "image", None) or getattr(obj, "photo", None),
            "title": getattr(obj, "title", None) or getattr(obj, "full_name", str(obj)),
            "bookmark_id": s.pk,
        })
    return render(request, "core/saqlanganlar.html", {
        "active": "saqlanganlar",
        "title": "Saqlanganlar",
        "subtitle": "Siz saqlagan materiallar ro'yxati. Saqlash tugmasi orqali materiallarni shu yerda to'plashingiz mumkin.",
        "items": items,
        "total": len(items),
    })


@require_POST
def bookmark_toggle(request):
    key = request.session.session_key
    if not key:
        request.session.create()
        key = request.session.session_key
    ctype = request.POST.get("ctype")
    oid = request.POST.get("oid")
    url = request.POST.get("next") or "/"
    if not oid or not ctype:
        return redirect(url)
    obj = Bookmark.objects.filter(session_key=key, content_type=ctype, object_id=oid).first()
    if obj:
        obj.delete()
        messages.success(request, "Saqlanganlardan olib tashlandi.")
    else:
        Bookmark.objects.create(session_key=key, content_type=ctype, object_id=oid)
        messages.success(request, "Saqlanganlarga qo'shildi.")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": not obj})
    return redirect(url)


# --------------------------------------------------------------- Til tanlash
def set_language(request, code):
    nxt = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = "/"
    response = redirect(nxt)
    if code in LANG_CODES:
        response.set_cookie(COOKIE, code, max_age=365 * 24 * 3600, samesite="Lax")
    return response
