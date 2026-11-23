"""Mavjud yozuvlarga kategoriya va yilni to'ldirish, albom hisoblagichlarini to'g'rilash."""
from django.db import migrations

MATERIALS = ["Achievement", "Event", "Education", "Document", "MediaItem", "Building", "ImportantDate", "Hero",
             "Department", "Person", "YearArchive"]


def _guess(text, rules, default):
    t = (text or "").lower()
    for key, words in rules:
        if any(w in t for w in words):
            return key
    return default


DATE_RULES = [
    ("tashkil", ["tashkil", "tuzil"]),
    ("xotira", ["xotira", "qadrlash", "halok"]),
    ("hujjat", ["farmon", "qaror", "qonun", "buyruq", "qabul qilin"]),
    ("bayram", ["bayram", "kuni", "tantana", "yubiley", "mustaqillik"]),
]
TOPIC_RULES = [
    ("sport", ["sport", "chempion", "musobaqa", "medal", "olimpi"]),
    ("mashgulot", ["mashg'ulot", "mashg‘ulot", "o'quv", "o‘quv", "trening", "kurs", "taktik"]),
    ("bino", ["bino", "inshoot", "qurilish", "foydalanishga topshir"]),
    ("tadbir", ["tadbir", "marosim", "tantana", "bayram", "tashrif", "uchrashuv", "konsert"]),
    ("tarix", ["tarix", "arxiv", "xotira"]),
]


def forwards(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Photo = apps.get_model("core", "Photo")
    Video = apps.get_model("core", "Video")

    ImportantDate = apps.get_model("core", "ImportantDate")
    for d in ImportantDate.objects.all():
        d.year = d.date.year
        d.date_type = _guess(f"{d.title} {d.description}", DATE_RULES, "tarixiy")
        d.save(update_fields=["year", "date_type"])

    MediaItem = apps.get_model("core", "MediaItem")
    for m in MediaItem.objects.all():
        m.topic = "tadbir" if m.event_id else _guess(f"{m.title} {m.description}", TOPIC_RULES, "xizmat")
        if m.date:
            m.year = m.date.year
        m.save(update_fields=["topic", "year"])

    for name in ("Achievement", "Event", "Education", "Document"):
        Model = apps.get_model("core", name)
        for o in Model.objects.exclude(date=None):
            if o.year != o.date.year:
                Model.objects.filter(pk=o.pk).update(year=o.date.year)

    Hero = apps.get_model("core", "Hero")
    for h in Hero.objects.filter(year=None).exclude(death_date=None):
        Hero.objects.filter(pk=h.pk).update(year=h.death_date.year)

    # Albom: yili ko'rsatilmagan rasm/videolarga materialning yilini yozish, hisoblagichlarni to'g'rilash
    for name in MATERIALS:
        Model = apps.get_model("core", name)
        try:
            ct = ContentType.objects.get(app_label="core", model=name.lower())
        except ContentType.DoesNotExist:
            continue
        fields = {f.name for f in Model._meta.get_fields()}
        for o in Model.objects.all():
            year = getattr(o, "year", None) or getattr(o, "year_start", None)
            if year:
                Photo.objects.filter(content_type=ct, object_id=o.pk, year=None).update(year=year)
                Video.objects.filter(content_type=ct, object_id=o.pk, year=None).update(year=year)
            upd = {}
            if "photo_count" in fields:
                upd["photo_count"] = Photo.objects.filter(content_type=ct, object_id=o.pk).count() + (1 if o.image else 0)
            if "video_count" in fields:
                main = bool(getattr(o, "video_file", None) or getattr(o, "video_url", ""))
                upd["video_count"] = Video.objects.filter(content_type=ct, object_id=o.pk).count() + (1 if main else 0)
            if upd:
                Model.objects.filter(pk=o.pk).update(**upd)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_category_year_album"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
