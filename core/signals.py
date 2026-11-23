"""Albomdagi rasm/video soni o'zgarganda materialning hisoblagichlarini yangilash."""
from django.contrib.contenttypes.models import ContentType

from core.models import Photo, Video


def recount(obj):
    """photo_count / video_count maydonlari bor obyekt uchun haqiqiy sonni yozadi."""
    if obj is None or not obj.pk:
        return
    model = type(obj)
    fields = {f.name for f in model._meta.get_fields()}
    ct = ContentType.objects.get_for_model(model)
    upd = {}
    if "photo_count" in fields:
        upd["photo_count"] = Photo.objects.filter(content_type=ct, object_id=obj.pk).count() + (
            1 if getattr(obj, "image", None) else 0)
    if "video_count" in fields:
        main_video = bool(getattr(obj, "video_file", None) or getattr(obj, "video_url", ""))
        upd["video_count"] = Video.objects.filter(content_type=ct, object_id=obj.pk).count() + (1 if main_video else 0)
    if upd:
        model.objects.filter(pk=obj.pk).update(**upd)


def media_changed(sender, instance, **kwargs):
    try:
        recount(instance.content_object)
    except Exception:  # noqa: BLE001 - ota-obyekt o'chirilgan bo'lishi mumkin
        pass


def owner_saved(sender, instance, raw=False, update_fields=None, **kwargs):
    if update_fields and not ({"image", "video_file", "video_url"} & set(update_fields)):
        return  # masalan, faqat ko'rishlar soni yangilandi
    if not raw and hasattr(instance, "photos"):
        recount(instance)
