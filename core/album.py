"""Foto va video albom: lightbox uchun elementlar ro'yxati va JSON endpoint."""
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404

from core.models import (
    Achievement, Building, Document, Education, Event, Hero, ImportantDate, MediaItem, Person,
    PublicOrder, YearArchive,
)

# URL'dagi qisqa nom -> model (faqat ochiq ko'rsatiladigan materiallar)
ALBUM_MODELS = {
    m._meta.model_name: m
    for m in (Achievement, Building, Document, Education, Event, Hero, ImportantDate, MediaItem,
              Person, PublicOrder, YearArchive)
}


def _title(obj):
    return str(getattr(obj, "title", "") or getattr(obj, "full_name", "") or obj)


def _main_image(obj):
    for f in ("image", "photo"):
        v = getattr(obj, f, None)
        if v and hasattr(v, "url"):
            return v
    return None


def photo_items(obj):
    title = _title(obj)
    year = getattr(obj, "year", None) or getattr(obj, "year_start", None)
    items = []
    main = _main_image(obj)
    if main:
        items.append({"type": "image", "src": main.url, "thumb": main.url, "title": title, "year": year})
    for p in obj.photos.all():
        if p.image:
            items.append({"type": "image", "src": p.image.url, "thumb": p.image.url,
                          "title": p.title or title, "year": p.year})
    return items


def video_items(obj):
    from core.templatetags.mg_tags import _youtube_id, video_thumb, youtube_embed, youtube_watch

    title = _title(obj)
    items = []
    cover = _main_image(obj)
    main_file = getattr(obj, "video_file", None)
    main_url = getattr(obj, "video_url", "")
    if main_file:
        items.append({"type": "video", "src": main_file.url, "thumb": cover.url if cover else "", "title": title,
                      "year": getattr(obj, "year", None)})
    elif main_url and _youtube_id(main_url):
        vid = _youtube_id(main_url)
        items.append({"type": "youtube", "src": youtube_embed(main_url) + "&autoplay=1", "watch": youtube_watch(main_url),
                      "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "title": title,
                      "year": getattr(obj, "year", None)})
    for v in obj.videos.all():
        if v.video_file:
            items.append({"type": "video", "src": v.video_file.url, "thumb": video_thumb(v), "title": v.title or title,
                          "year": v.year})
        elif v.video_url and _youtube_id(v.video_url):
            items.append({"type": "youtube", "src": youtube_embed(v.video_url) + "&autoplay=1",
                          "watch": youtube_watch(v.video_url), "thumb": video_thumb(v), "title": v.title or title,
                          "year": v.year})
    return items


def album_json(request, model, pk):
    """/albom/<model>/<pk>/?tur=foto|video — kartochkadan albomni ochish uchun."""
    Model = ALBUM_MODELS.get(model)
    if Model is None:
        raise Http404
    qs = Model.objects.all()
    if any(f.name == "is_published" for f in Model._meta.get_fields()):
        qs = qs.filter(is_published=True)
    obj = get_object_or_404(qs, pk=pk)
    kind = request.GET.get("tur", "foto")
    items = video_items(obj) if kind == "video" else photo_items(obj)
    href = obj.get_absolute_url()
    for it in items:
        it["href"] = href
    return JsonResponse({"title": _title(obj), "items": items})
