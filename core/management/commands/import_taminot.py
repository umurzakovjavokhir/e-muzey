"""
"Ta'minot yo'nalishlari" bo'limi (Education modeli, /talim/) ma'lumotlarini yuklaydi.

Manba: https://milliygvardiya.uz/oz/news — Milliy gvardiyaning kiyim-kechak, qurol-aslaha va texnika,
tibbiy ta'minot, harbiy xizmatchilarga uy-joy topshirish hamda yangi bino va inshootlar ochilishiga oid
rasmiy yangiliklari (fayl: core/data/taminot_data.json, rasmlar media/educations/tm/ ichida).

    python manage.py import_taminot

Bo'limdagi BARCHA eski yozuvlar (va ularning foto/video albomlari) o'chiriladi.
"""
import json
from datetime import date
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from core.i18n import bump_version
from core.models import Bookmark, Direction, Education, Photo, Region, Tag, Video
from core.signals import recount

DATA = Path(__file__).resolve().parents[2] / "data" / "taminot_data.json"
TAGS = {"bino": "yangi bino", "qurol": "texnika"}


def load_taminot(path=DATA, stdout=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    regions = {r.name: r for r in Region.objects.all()}
    tags = {t.name: t for t in Tag.objects.all()}
    ct = ContentType.objects.get_for_model(Education)
    with transaction.atomic():
        old = list(Education.objects.values_list("pk", flat=True))
        Photo.objects.filter(content_type=ct, object_id__in=old).delete()
        Video.objects.filter(content_type=ct, object_id__in=old).delete()
        Bookmark.objects.filter(content_type__in=["education", "talim"], object_id__in=old).delete()
        Education.objects.filter(pk__in=old).delete()

        for x in data["supplies"]:
            photos, videos = x.get("photos", []), x.get("videos", [])
            o = Education.objects.create(
                title=x["title"][:300], summary=x["summary"][:400], description="\n".join(x["body"]),
                material_type="malumot", edu_type=x["edu_type"],
                date=date.fromisoformat(x["date"]) if x.get("date") else None, year=x["year"],
                region=regions.get(x.get("region") or ""), image=x.get("image") or "",
                source_url=x.get("source_url", ""), is_published=True,
                is_featured=x["edu_type"] in ("uy_joy", "bino"),
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
            if TAGS.get(o.edu_type) in tags:
                o.tags.add(tags[TAGS[o.edu_type]])

        Direction.objects.filter(url="core:talim").update(
            title="Ta'minot yo'nalishlari", icon="box",
            description=(
                "Milliy gvardiyaning moddiy-texnik ta'minoti: harbiy xizmatchilarni kiyim-kechak, zamonaviy "
                "qurol-aslaha va texnika bilan ta'minlash, tibbiy xizmat va sog'lomlashtirish, harbiy "
                "xizmatchilarga uy-joy kalitlarini topshirish hamda yangi bino va inshootlarning ochilishi. "
                "Barcha materiallar milliygvardiya.uz rasmiy saytidan olingan."
            ),
        )
    bump_version()
    if stdout:
        stdout.write(f"  Ta'minot yo'nalishlari: {Education.objects.count()} ta material, "
                     f"{Photo.objects.filter(content_type=ct).count()} ta albom rasmi")


class Command(BaseCommand):
    help = "Ta'minot yo'nalishlari bo'limini milliygvardiya.uz ma'lumotlari bilan to'ldiradi (eski yozuvlar o'chiriladi)"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DATA))

    def handle(self, *args, **opts):
        load_taminot(opts["file"], self.stdout)
        self.stdout.write(self.style.SUCCESS("Ta'minot ma'lumotlari yuklandi."))
