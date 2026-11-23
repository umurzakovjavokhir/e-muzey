"""
"Jamoat tartibini saqlash" bo'limi (PublicOrder modeli, /jamoat-tartibi/) ma'lumotlarini yuklaydi.

Manba: https://milliygvardiya.uz/oz/news — ommaviy tadbirlarda xavfsizlik, patrul-post xizmati,
huquqbuzarliklar profilaktikasi, qo'riqlash xizmati va fuqarolarga yordamga oid rasmiy xabarlar
(fayl: core/data/jamoat_data.json, rasmlar media/jamoat/ ichida).

Shuningdek, o'chirilgan "Bo'linmalar tarixi" bo'limining (Department) barcha yozuvlarini tozalaydi.

    python manage.py import_jamoat
"""
import json
from datetime import date
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from core.i18n import bump_version
from core.models import Bookmark, Department, Direction, Photo, PublicOrder, Region, Video
from core.signals import recount

DATA = Path(__file__).resolve().parents[2] / "data" / "jamoat_data.json"


def clear_departments():
    """Bo'linmalar tarixi — bo'lim olib tashlangan; yozuvlar va albomlarini o'chiradi."""
    ct = ContentType.objects.get_for_model(Department)
    ids = list(Department.objects.values_list("pk", flat=True))
    Photo.objects.filter(content_type=ct, object_id__in=ids).delete()
    Video.objects.filter(content_type=ct, object_id__in=ids).delete()
    Bookmark.objects.filter(content_type__in=["department", "bolinma"]).delete()
    Department.objects.all().delete()  # bog'langan materiallarda department=NULL bo'ladi
    return len(ids)


def load_jamoat(path=DATA, stdout=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    regions = {r.name: r for r in Region.objects.all()}
    ct = ContentType.objects.get_for_model(PublicOrder)
    with transaction.atomic():
        n_dep = clear_departments()
        old = list(PublicOrder.objects.values_list("pk", flat=True))
        Photo.objects.filter(content_type=ct, object_id__in=old).delete()
        Video.objects.filter(content_type=ct, object_id__in=old).delete()
        Bookmark.objects.filter(content_type="jamoat", object_id__in=old).delete()
        PublicOrder.objects.filter(pk__in=old).delete()

        for x in data["items"]:
            photos, videos = x.get("photos", []), x.get("videos", [])
            o = PublicOrder.objects.create(
                title=x["title"][:300], summary=x["summary"][:400], description="\n".join(x["body"]),
                material_type="malumot", order_type=x["order_type"],
                date=date.fromisoformat(x["date"]) if x.get("date") else None, year=x["year"],
                region=regions.get(x.get("region") or ""), image=x.get("image") or "",
                source_url=x.get("source_url", ""), is_published=True,
            )
            Photo.objects.bulk_create([
                Photo(content_type=ct, object_id=o.pk, image=p, title="", year=o.year, order=i)
                for i, p in enumerate(photos)
            ])
            Video.objects.bulk_create([
                Video(content_type=ct, object_id=o.pk, video_url=f"https://www.youtube.com/watch?v={v}",
                      title="", year=o.year, order=i)
                for i, v in enumerate(videos)
            ])
            recount(o)  # bulk_create signal chaqirmaydi

        Direction.objects.filter(url__in=["core:bolinmalar", "core:jamoat"]).update(url="core:jamoat")
    bump_version()
    if stdout:
        stdout.write(f"  Jamoat tartibini saqlash: {PublicOrder.objects.count()} ta material, "
                     f"{Photo.objects.filter(content_type=ct).count()} ta albom rasmi; "
                     f"o'chirilgan bo'linmalar: {n_dep}")


class Command(BaseCommand):
    help = "Jamoat tartibini saqlash bo'limini milliygvardiya.uz ma'lumotlari bilan to'ldiradi"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DATA))

    def handle(self, *args, **opts):
        load_jamoat(opts["file"], self.stdout)
        self.stdout.write(self.style.SUCCESS("Jamoat tartibi ma'lumotlari yuklandi."))
