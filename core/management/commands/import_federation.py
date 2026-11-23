"""
"Federatsiyalar faoliyati" bo'limi (Achievement / Erishilgan g'alabalar) ma'lumotlarini yuklaydi.

Manbalar (fayl: core/data/federation_data.json, rasmlar media/achievements/uza/ va qj/ ichida):
  * https://uzarchery.uz/oz — kamondan otish federatsiyasining Milliy gvardiyaga oid yangiliklari,
    fotoalbomlari va videolari;
  * https://qoljangi.uz — huquqni muhofaza qilish organlari qo'l jangi federatsiyasi (2020-yil
    sentabrdan Milliy gvardiya qo'mondoni rahbarligida) yangiliklari va galereyasi, ru/en tarjimalari bilan.

    python manage.py import_federation

Bo'limdagi BARCHA eski yozuvlar (va ularning foto/video albomlari) o'chiriladi.
"""
import json
from datetime import date
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from core.i18n import bump_version
from core.models import Achievement, Bookmark, Photo, Region, Tag, Translation, Video
from core.signals import recount

DATA = Path(__file__).resolve().parents[2] / "data" / "federation_data.json"


def load_federation(path=DATA, stdout=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    regions = {r.name: r for r in Region.objects.all()}
    ct = ContentType.objects.get_for_model(Achievement)
    sport = Tag.objects.filter(name="musobaqa").first()
    with transaction.atomic():
        old = list(Achievement.objects.values_list("pk", flat=True))
        Photo.objects.filter(content_type=ct, object_id__in=old).delete()
        Video.objects.filter(content_type=ct, object_id__in=old).delete()
        Bookmark.objects.filter(content_type__in=["achievement", "galaba"], object_id__in=old).delete()
        Achievement.objects.filter(pk__in=old).delete()

        for x in data["achievements"]:
            dt = date.fromisoformat(x["date"]) if x.get("date") else None
            photos, videos = x.get("photos", []), x.get("videos", [])
            o = Achievement.objects.create(
                title=x["title"][:300], summary=x["summary"][:400], description="\n".join(x["body"]),
                material_type="galaba", achievement_type=x["achievement_type"],
                date=dt, year=x["year"], region=regions.get(x.get("region") or ""),
                image=x.get("image") or "", source_url=x.get("source_url", ""),
                photo_count=(1 if x.get("image") else 0) + len(photos), video_count=len(videos),
                is_featured=x["achievement_type"] == "xalqaro", is_published=True,
            )
            Photo.objects.bulk_create([
                Photo(content_type=ct, object_id=o.pk, image=p, title="", year=o.year, order=i)
                for i, p in enumerate(photos)
            ])
            Video.objects.bulk_create([
                Video(content_type=ct, object_id=o.pk, video_url=f"https://www.youtube.com/watch?v={v['id']}",
                      title=v.get("title", "")[:255], year=o.year, order=i)
                for i, v in enumerate(videos)
            ])
            recount(o)  # bulk_create signal chaqirmaydi
            if sport and x["achievement_type"] in ("xalqaro", "respublika"):
                o.tags.add(sport)
        seen = set(Translation.objects.values_list("source_hash", flat=True))
        new_tr = []
        for t in data.get("translations", []):
            h = Translation.make_hash(t["source"])
            if h not in seen and (t.get("ru") or t.get("en")):
                seen.add(h)
                new_tr.append(Translation(source=t["source"], source_hash=h, ru=t.get("ru", ""), en=t.get("en", ""),
                                          is_ui=False))
        Translation.objects.bulk_create(new_tr)
    bump_version()
    if stdout:
        stdout.write(f"  Federatsiyalar faoliyati: {Achievement.objects.count()} ta material, "
                     f"{Photo.objects.filter(content_type=ct).count()} ta albom rasmi, "
                     f"{Video.objects.filter(content_type=ct).count()} ta video, {len(new_tr)} ta yangi tarjima")


class Command(BaseCommand):
    help = "Federatsiyalar faoliyati bo'limini uzarchery.uz va qoljangi.uz (Milliy gvardiyaga oid) ma'lumotlari bilan to'ldiradi"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DATA))

    def handle(self, *args, **opts):
        load_federation(opts["file"], self.stdout)
        self.stdout.write(self.style.SUCCESS("Federatsiya ma'lumotlari yuklandi."))
