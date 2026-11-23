"""Milliy gvardiya rasmiy manbalaridan yig'ilgan ma'lumotlarni bazaga yozadi.

Manba fayl: core/data/mg_data.json (rasmlar MEDIA_ROOT ichida tayyor turadi).
Qo'lda yuklangan rasmlar (persons/, dates/, departments/ dagi foydalanuvchi fayllari) saqlab qolinadi.

    python manage.py import_mg_data
"""
import json
import re
from datetime import date
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from core.management.commands.import_federation import load_federation
from core.management.commands.import_taminot import load_taminot
from core.management.commands.import_jamoat import load_jamoat

from core.i18n import bump_version

from core.models import (
    Achievement, Building, Department, Direction, Document, Education, Event, Hero, Highlight, ImportantDate,
    MediaItem, Person, Photo, Region, StatCard, Tag, Translation, YearArchive,
)

DATA = Path(__file__).resolve().parents[2] / "data" / "mg_data.json"
LOOKALIKE = str.maketrans({"х": "x", "Х": "X", "а": "a", "о": "o", "е": "e", "с": "s", "р": "r", "у": "y",
                           "ş": "sh", "Ş": "Sh", "ö": "o‘", "Ö": "O‘", "ğ": "g‘"})
TAG_RULES = [
    ("yangi bino", r"yangi bino|foydalanishga topshiril"),
    ("ma'muriy bino", r"ma.muriy bino"),
    ("Toshkent", r"toshkent|poytaxt"),
    ("musobaqa", r"musobaqa|chempionat|turnir|bellashuv"),
    ("mukofot", r"mukofot|medal|orden|taqdirla"),
    ("tarix", r"tarix|xotira|yodgorlik"),
    ("o'quv markazi", r"o.quv markaz"),
    ("tantana", r"tantana|marosim|bayram"),
    ("texnika", r"texnika|dron|texnolog"),
    ("hujjat", r"qonun|qaror|farmon|hujjat"),
    ("rivojlanish", r"rivojlan|takomillash"),
]


def fix(text):
    text = text or ""
    if len(re.findall(r"[а-яА-Я]", text)) < 4:
        text = text.translate(LOOKALIKE)
    return text


def d(s):
    return date.fromisoformat(s) if s else None


def is_user_file(field, prefix):
    """Foydalanuvchi admin orqali yuklagan rasm (bizning mg_ fayllarimiz emas)."""
    name = getattr(field, "name", "") or ""
    return bool(name) and not Path(name).name.startswith(prefix)


class Command(BaseCommand):
    help = "Milliy gvardiya rasmiy manbalaridan olingan real ma'lumotlarni import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DATA))

    def handle(self, *args, **opts):
        data = json.loads(Path(opts["file"]).read_text(encoding="utf-8"))
        with transaction.atomic():
            self.regions = {r.name: r for r in Region.objects.all()}
            self.depts = {dp.title: dp for dp in Department.objects.all()}
            self.tags = {t.name: t for t in Tag.objects.all()}
            self._clear()
            self._materials(data)
            self._media(data["media"])
            self._documents(data["documents"])
            self._persons(data["persons"])
            self._heroes(data.get("heroes", []))
            load_federation(stdout=self.stdout)
            load_taminot(stdout=self.stdout)
            load_jamoat(stdout=self.stdout)  # Bo'linmalar tarixini ham tozalaydi
            self._dates(data["dates"])
            self._years(data["years"])
            self._stats()
            self._directions()
            self._translations(data["translations"])
            self._ui_translations()
        self.stdout.write(self.style.SUCCESS("Import yakunlandi."))
        for m in (Building, Achievement, Event, Education, Document, MediaItem, Person, ImportantDate, Photo, Translation):
            self.stdout.write(f"  {m._meta.verbose_name_plural}: {m.objects.count()}")

    # ------------------------------------------------------------------ yordamchi
    def region(self, name):
        return self.regions.get(name) if name else None

    def dept(self, name):
        return self.depts.get(name) if name else None

    def photos(self, obj, paths):
        ct = ContentType.objects.get_for_model(obj)
        Photo.objects.bulk_create([
            Photo(content_type=ct, object_id=obj.pk, image=p, title="", order=i) for i, p in enumerate(paths)
        ])

    def tag(self, obj, text):
        for name, rx in TAG_RULES:
            if name in self.tags and re.search(rx, text, re.I):
                obj.tags.add(self.tags[name])

    def _clear(self):
        """Faqat avvalgi importdan kelgan yozuvlarni (manba havolasi bor) o'chiradi.
        Admin orqali qo'lda qo'shilgan materiallar (manba havolasi bo'sh) saqlanib qoladi."""
        # Achievement ("Federatsiyalar faoliyati") — alohida manba: import_federation
        # Education ("Ta'minot yo'nalishlari") — alohida manba: import_taminot
        for model in (Building, Event, Document, MediaItem):
            ct = ContentType.objects.get_for_model(model)
            ids = list(model.objects.exclude(source_url="").values_list("pk", flat=True))
            Photo.objects.filter(content_type=ct, object_id__in=ids).delete()
            Highlight.objects.filter(building_id__in=ids if model is Building else []).delete()
            model.objects.filter(pk__in=ids).delete()
        Translation.objects.filter(is_ui=False).delete()

    # ------------------------------------------------------------------ materiallar
    def _common(self, x):
        body = [fix(p) for p in x["body"]]
        return dict(
            title=fix(x["title"])[:300], summary=fix(x["summary"])[:400], description="\n".join(body),
            date=d(x["date"]), year=x["year"], region=self.region(x.get("region")),
            department=self.dept(x.get("department")), image=x.get("image") or "",
            photo_count=(1 if x.get("image") else 0) + len(x.get("photos", [])),
            source_url=x.get("source_url", ""), is_published=True,
        )

    def _materials(self, data):
        for i, x in enumerate(data["buildings"]):
            body = [fix(p) for p in x["body"]]
            b = Building.objects.create(
                title=fix(x["title"])[:255], building_type=x["building_type"], year=x["year"],
                handover_date=d(x["date"]), address=x.get("address") or "", region=self.region(x.get("region")),
                department=self.dept(x.get("department")), description="\n".join(body), image=x.get("image") or "",
                photo_count=(1 if x.get("image") else 0) + len(x.get("photos", [])), is_active=True, order=i,
                source_url=x.get("source_url", ""), views=0,
            )
            self.photos(b, x.get("photos", []))
        for x in data.get("achievements", []):  # eski manba; endi bo'sh — import_federation ishlatiladi
            o = Achievement.objects.create(material_type="galaba", achievement_type=x["achievement_type"],
                                           is_featured=x["achievement_type"] == "xalqaro", **self._common(x))
            self.photos(o, x.get("photos", []))
            self.tag(o, o.title + " " + o.description)
        for x in data["events"]:
            o = Event.objects.create(material_type="tadbir", event_type=x["event_type"], location=x.get("location") or "",
                                     **self._common(x))
            self.photos(o, x.get("photos", []))
            self.tag(o, o.title + " " + o.description)
        # "educations" (eski Ta'lim bo'limi) endi ishlatilmaydi — Ta'minot yo'nalishlari: import_taminot

    def _media(self, items):
        from django.conf import settings

        from core.templatetags.mg_tags import _youtube_id

        for i, x in enumerate(items):
            # YouTube videolari serverga yuklab olingan (media/videos/yt/<id>.mp4) — saytda o'sha fayl ochiladi
            url, vfile = x.get("video_url", ""), ""
            vid = _youtube_id(url) if url else None
            if vid and (Path(settings.MEDIA_ROOT) / "videos" / "yt" / f"{vid}.mp4").exists():
                url, vfile = "", f"videos/yt/{vid}.mp4"
            m = MediaItem.objects.create(
                title=fix(x["title"])[:300], media_type=x["media_type"], image=x.get("image") or "",
                video_url=url, video_file=vfile, date=d(x["date"]), year=x["year"], description=fix(x["description"]),
                order=i,
                source_url=x.get("source_url", ""),
            )
            self.photos(m, x.get("photos", []))

    def _documents(self, items):
        for x in items:
            o = Document.objects.create(
                title=fix(x["title"])[:300], doc_type=x["doc_type"], doc_number=x["doc_number"], date=d(x["date"]),
                year=x["year"], summary=fix(x["summary"])[:400], description="\n".join(fix(p) for p in x["description"]),
                image=x.get("image") or "", material_type="hujjat", source_url=x.get("source_url", ""), doc_count=1,
                is_published=True, is_featured=x["doc_number"] in ("O‘RQ-647", "Ramz"),
            )
            self.tag(o, o.title + " hujjat")

    # ------------------------------------------------------------------ shaxslar
    def _persons(self, items):
        old = list(Person.objects.all())
        keep_ids = set()
        done = set()
        for x in items:
            name = fix(x["full_name"])
            if name.lower() in done:
                # bir shaxs bir necha ro'yxatda (masalan, rahbar va mukofot sohibi) — mukofotni qo'shamiz
                p = Person.objects.filter(full_name=name).first()
                if p and x.get("awards") and x["awards"] not in p.awards:
                    p.awards = (p.awards + "\n" + fix(x["awards"])).strip()
                    p.save(update_fields=["awards"])
                continue
            done.add(name.lower())
            if x["person_type"] == "shaxs":
                # sportchilar va davlat mukofoti sohiblari — «Bizning qahramonlar» bo'limida
                cat = "sportchi" if "/athletes" in x.get("source_url", "") else "mukofot"
                h = Hero.objects.filter(full_name=name).first() or Hero(full_name=name)
                h.category = cat
                h.rank = fix(x["position"])[:255]
                h.bio = "\n".join(fix(p) for p in x["bio"])
                h.awards = fix(x.get("awards", ""))
                h.birth_date = d(x.get("birth_date"))
                h.source_url = x.get("source_url", "")[:200]
                h.order = 100 + x["order"]
                if not h.photo:
                    h.photo = x["photo"]
                h.save()
                continue
            obj = None
            if x["person_type"] in ("rahbar", "tarixiy") and x["order"] < 10:
                surname = x["match"].lower()
                obj = next((p for p in old if p.full_name.lower().startswith(surname)), None)
                if obj is None and "birinchi o" in x["position"].lower():
                    obj = next((p for p in old if "birinchi o" in p.full_name.lower()), None)
            if obj is None:
                obj = Person.objects.filter(full_name=name).first() or Person()
            keep_photo = obj.pk and is_user_file(obj.photo, "mg_")
            obj.full_name = name
            obj.slug = obj.slug if obj.pk else ""
            obj.position = fix(x["position"])[:255]
            obj.person_type = x["person_type"]
            obj.bio = "\n".join(fix(p) for p in x["bio"])
            obj.awards = fix(x.get("awards", ""))
            obj.service_period = x.get("service_period", "")[:100]
            obj.birth_date = d(x.get("birth_date"))
            obj.department = self.dept(x.get("department"))
            obj.order = x["order"]
            obj.source_url = x.get("source_url", "")[:200]
            if not keep_photo:
                obj.photo = x["photo"]
            obj.save()
            keep_ids.add(obj.pk)
        Person.objects.exclude(pk__in=keep_ids).filter(photo="").delete()
        # demo yozuvlar (foydalanuvchi rasmi bo'lmagan) o'chiriladi
        for p in Person.objects.exclude(pk__in=keep_ids):
            if not is_user_file(p.photo, "mg_"):
                p.delete()

    # ------------------------------------------------------------------ sanalar
    def _dates(self, items):
        user_dates = [x for x in ImportantDate.objects.all() if is_user_file(x.image, "mg_")]
        ImportantDate.objects.exclude(pk__in=[x.pk for x in user_dates]).delete()
        founding = next((x for x in user_dates if "tashkil" in x.title.lower()), None)
        for x in items:
            if founding and x["date"] == "2017-08-04":
                founding.title = x["title"]
                founding.date = d(x["date"])
                founding.description = x["description"]
                founding.is_featured = True
                founding.save()
                continue
            ImportantDate.objects.create(title=x["title"], date=d(x["date"]), description=x["description"],
                                         image=x["image"], is_featured=x["is_featured"])

    # ------------------------------------------------------------------ bo'linmalar
    # ------------------------------------------------------------------ yillar
    def _years(self, items):
        for x in items:
            y, _ = YearArchive.objects.get_or_create(year=x["year"], defaults={"title": f"{x['year']}-yil"})
            if x["subtitle"]:
                y.title = x["subtitle"]
                y.subtitle = f"{x['year']}-yil"
            else:
                y.subtitle = f"{x['year']}-yil"
            y.description = "\n".join(x["description"])
            if not is_user_file(y.image, "mg_") or not y.image:
                y.image = x["image"]
            y.video_url = x.get("video_url", "")
            y.new_buildings = x["new_buildings"]
            y.achievements = x["achievements"]
            y.documents = x["documents"]
            y.new_departments = 14 if x["year"] == 2019 else (1 if x["year"] == 2017 else 0)
            y.is_featured = x["year"] in (2017, 2019, 2020, 2026)
            y.save()

    # ------------------------------------------------------------------ statistika
    def _stats(self):
        photos = Photo.objects.count() + sum(1 for m in MediaItem.objects.all() if m.image)
        values = [
            (str(Building.objects.count()), "Yangi bino va inshootlar"),
            (str(Region.objects.filter(is_other=False).count()), "Viloyat va shahar"),
            (str(photos), "Foto materiallar"),
            (str(MediaItem.objects.filter(media_type="video").count()), "Video materiallar"),
            (str(Achievement.objects.count()), "Erishilgan g‘alabalar"),
            (str(sum(m.objects.count() for m in (Achievement, Event, Education, Document, MediaItem, Building))), "Arxiv materiallari"),
        ]
        cards = list(StatCard.objects.all()[:6])
        for card, (val, label) in zip(cards, values):
            card.value, card.label = val, label
            card.save()

    def _directions(self):
        for dr in Direction.objects.all():
            t = fix(dr.title)
            if t != dr.title:
                dr.title = t
                dr.save(update_fields=["title"])

    def _translations(self, items):
        seen = set(Translation.objects.values_list("source_hash", flat=True))
        objs = []
        for x in items:
            src = fix(x["source"])
            h = Translation.make_hash(src)
            if h in seen or not (x.get("ru") or x.get("en")):
                continue
            seen.add(h)
            objs.append(Translation(source=src, source_hash=h, ru=x.get("ru", ""), en=x.get("en", ""), is_ui=False))
        Translation.objects.bulk_create(objs)
        bump_version()

    def _ui_translations(self):
        from core.data.ui_translations import UI

        Translation.objects.filter(is_ui=True).delete()
        existing = set(Translation.objects.values_list("source_hash", flat=True))
        objs, seen = [], set()
        for src, ru, en in UI:
            h = Translation.make_hash(src)
            if h in seen:
                continue
            seen.add(h)
            if h in existing:
                Translation.objects.filter(source_hash=h).update(ru=ru, en=en, is_ui=True)
                continue
            objs.append(Translation(source=src, source_hash=h, ru=ru, en=en, is_ui=True))
        Translation.objects.bulk_create(objs)
        bump_version()

    def _heroes(self, items):
        import re as _re

        for x in items:
            name = fix(x["full_name"])
            h = Hero.objects.filter(full_name=name).first() or Hero(full_name=name)
            place = _re.sub(r"\s*,\s*", ", ", x.get("birth_place", ""))
            place = place.replace("viloyatining", "viloyati").replace("tumanida", "tumani")
            h.rank = x.get("rank", "")
            h.birth_date = d(x.get("birth_date"))
            h.death_date = d(x.get("death_date"))
            h.birth_place = place[:255]
            h.region = self.region(x.get("region"))
            h.feat = fix(x.get("feat", ""))
            h.bio = "\n".join(fix(p) for p in x["bio"])
            h.awards = fix(x.get("awards", ""))
            h.source_url = x.get("source_url", "")
            h.order = x.get("order", 0)
            if not h.photo and x.get("photo"):
                h.photo = x["photo"]
            h.save()
