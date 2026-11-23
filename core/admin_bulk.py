"""Admin: bir vaqtda ko'p rasm / video yuklash."""
import os
from datetime import date

from django import forms
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from core.models import Event, MediaItem, Photo, Video

VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v", ".ogg", ".ogv"}


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """Bir maydonda istalgancha rasm (har biri Pillow orqali tekshiriladi)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*", "multiple": True}))
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data if d]
        return [single(data, initial)] if data else []


class MultipleVideoField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "video/*", "multiple": True}))
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        out = []
        for f in files:
            f = super().clean(f, initial)
            if f and os.path.splitext(f.name)[1].lower() not in VIDEO_EXT:
                raise ValidationError(f"«{f.name}» video fayl emas (ruxsat: {', '.join(sorted(VIDEO_EXT))}).")
            if f:
                out.append(f)
        return out


def add_photos(obj, files, start=None, year=None):
    """Obyektga fotoalbom rasmlarini qo'shadi va foto hisoblagichini yangilaydi."""
    if not files:
        return 0
    ct = ContentType.objects.get_for_model(obj)
    if start is None:
        last = Photo.objects.filter(content_type=ct, object_id=obj.pk).order_by("-order").first()
        start = (last.order + 1) if last else 0
    for i, f in enumerate(files):
        Photo.objects.create(content_type=ct, object_id=obj.pk, image=f, order=start + i, year=year)
    if hasattr(obj, "photo_count"):
        total = Photo.objects.filter(content_type=ct, object_id=obj.pk).count() + (1 if getattr(obj, "image", None) else 0)
        type(obj).objects.filter(pk=obj.pk).update(photo_count=total)
    return len(files)


# ------------------------------------------------------------------ tahrirlash formasi
def _year_bounds():
    return 1900, date.today().year + 1


class BulkPhotoForm(forms.ModelForm):
    bulk_year = forms.IntegerField(
        label="Yuklanayotgan rasm/videolar yili", required=False,
        min_value=_year_bounds()[0], max_value=_year_bounds()[1],
        widget=forms.NumberInput(attrs={"placeholder": "masalan, 2024", "style": "width:140px"}),
        help_text="Shu safar yuklanayotgan barcha rasm va videolarga shu yil yoziladi (bo'sh qoldirilsa — materialning yili). "
                  "Saytda galereya yillar bo'yicha guruhlanadi. Keyin har birining yilini pastdagi ro'yxatda o'zgartirish mumkin.",
    )
    bulk_photos = MultipleImageField(
        label="Ko'p rasm yuklash",
        help_text="Bir vaqtda istalgancha rasm tanlang (Ctrl / Shift bilan yoki sudrab tashlab). "
                  "Ular shu materialning fotoalbomiga qo'shiladi. Asosiy rasm bo'sh bo'lsa, birinchisi asosiy rasm bo'ladi.",
    )


class BulkPhotoAdminMixin:
    """ModelAdmin uchun: tahrirlash sahifasida «Ko'p rasm yuklash» maydoni."""

    form = BulkPhotoForm

    def save_related(self, request, form, formsets, change):
        # Yil ko'rsatilmasa, albomga materialning o'z yili yoziladi (kategoriya/yil filtri uchun)
        if not form.cleaned_data.get("bulk_year"):
            obj = form.instance
            form.cleaned_data["bulk_year"] = getattr(obj, "year", None) or getattr(obj, "year_start", None)
        super().save_related(request, form, formsets, change)
        files = list(form.cleaned_data.get("bulk_photos") or [])
        if not files:
            return
        total = len(files)
        obj = form.instance
        main = "image" if hasattr(obj, "image") else ("photo" if hasattr(obj, "photo") else None)
        if main and not getattr(obj, main):
            setattr(obj, main, files.pop(0))
            obj.save(update_fields=[main])
        add_photos(obj, files, year=form.cleaned_data.get("bulk_year"))
        messages.success(request, f"{total} ta rasm yuklandi.")


def _parse_youtube(text):
    from core.templatetags.mg_tags import youtube_embed

    links = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    bad = [ln for ln in links if not youtube_embed(ln)]
    if bad:
        raise ValidationError("YouTube havolasi emas: " + ", ".join(bad[:3]))
    return links


def add_videos(obj, files=(), links=(), year=None):
    """Obyektga video fayllar va YouTube havolalarini qo'shadi."""
    ct = ContentType.objects.get_for_model(obj)
    last = Video.objects.filter(content_type=ct, object_id=obj.pk).order_by("-order").first()
    n = (last.order + 1) if last else 0
    for f in files:
        Video.objects.create(content_type=ct, object_id=obj.pk, video_file=f, title=_title_from(f.name), order=n, year=year)
        n += 1
    for url in links:
        Video.objects.create(content_type=ct, object_id=obj.pk, video_url=url, order=n, year=year)
        n += 1
    return len(files) + len(links)


class BulkMediaForm(BulkPhotoForm):
    bulk_videos = MultipleVideoField(
        label="Ko'p video yuklash",
        help_text="Bir vaqtda istalgancha video fayl tanlang (mp4, webm, mov).",
    )
    bulk_youtube = forms.CharField(
        label="YouTube havolalari", required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Har bir qatorga bitta havola"}),
        help_text="https://www.youtube.com/watch?v=... yoki https://youtu.be/...",
    )

    def clean_bulk_youtube(self):
        return _parse_youtube(self.cleaned_data.get("bulk_youtube"))


class BulkMediaAdminMixin(BulkPhotoAdminMixin):
    """Ko'p rasm + ko'p video (fayl yoki YouTube) yuklash."""

    form = BulkMediaForm

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        files = list(form.cleaned_data.get("bulk_videos") or [])
        links = list(form.cleaned_data.get("bulk_youtube") or [])
        if files or links:
            n = add_videos(form.instance, files, links, year=form.cleaned_data.get("bulk_year"))
            messages.success(request, f"{n} ta video qo'shildi.")


# ------------------------------------------------------------------ ommaviy yuklash sahifasi
class MediaBulkUploadForm(forms.Form):
    MODE_CHOICES = [
        ("album", "Bitta albom — barcha rasmlar bitta materialda (galereya bilan)"),
        ("separate", "Har bir rasm alohida material bo'lsin"),
    ]
    title = forms.CharField(label="Sarlavha", max_length=250, required=False,
                            help_text="Bo'sh qoldirilsa, fayl nomidan olinadi. Bir nechta material bo'lsa, oxiriga raqam qo'shiladi.")
    date = forms.DateField(label="Sana", initial=date.today, widget=forms.DateInput(attrs={"type": "date"}))
    description = forms.CharField(label="Tavsif", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    event = forms.ModelChoiceField(label="Tadbir", queryset=Event.objects.all(), required=False)
    mode = forms.ChoiceField(label="Rasmlar qanday saqlansin", choices=MODE_CHOICES, initial="album",
                             widget=forms.RadioSelect)
    images = MultipleImageField(label="Rasmlar", help_text="Bir vaqtda 2, 10, 40 va undan ko'p rasm tanlash mumkin.")
    videos = MultipleVideoField(label="Video fayllar", help_text="mp4, webm, mov. Har bir video alohida material bo'ladi.")
    youtube = forms.CharField(
        label="YouTube havolalari", required=False, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Har bir qatorga bitta havola"}),
        help_text="Har bir qatorga bitta havola: https://www.youtube.com/watch?v=... yoki https://youtu.be/...",
    )

    def clean_youtube(self):
        return _parse_youtube(self.cleaned_data.get("youtube"))

    def clean(self):
        data = super().clean()
        if not (data.get("images") or data.get("videos") or data.get("youtube")):
            raise ValidationError("Kamida bitta rasm, video fayl yoki YouTube havolasini kiriting.")
        return data


def _title_from(name):
    base = os.path.splitext(os.path.basename(name))[0]
    return base.replace("_", " ").replace("-", " ").strip()[:250] or "Media"


class MediaBulkUploadMixin:
    """MediaItemAdmin uchun «Ommaviy yuklash» sahifasi."""

    change_list_template = "admin/core/mediaitem/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [path("ommaviy-yuklash/", self.admin_site.admin_view(self.bulk_upload_view), name="core_mediaitem_bulk")]
        return custom + urls

    def bulk_upload_view(self, request):
        if not self.has_add_permission(request):
            messages.error(request, "Material qo'shishga ruxsatingiz yo'q.")
            return redirect("admin:core_mediaitem_changelist")
        form = MediaBulkUploadForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            created = self._create_items(form.cleaned_data)
            messages.success(request, f"{len(created)} ta media material yaratildi "
                                      f"({sum(c[1] for c in created)} ta fayl/havola yuklandi).")
            if len(created) == 1:
                return redirect(reverse("admin:core_mediaitem_change", args=[created[0][0].pk]))
            return redirect("admin:core_mediaitem_changelist")
        ctx = {
            **self.admin_site.each_context(request),
            "title": "Ommaviy yuklash — rasm va videolar",
            "form": form,
            "opts": self.model._meta,
            "has_view_permission": True,
        }
        return TemplateResponse(request, "admin/core/mediaitem/bulk_upload.html", ctx)

    def _create_items(self, cd):
        d = cd["date"]
        common = {"date": d, "year": d.year, "description": cd.get("description", ""),
                  "department": cd.get("department"), "event": cd.get("event")}
        title = (cd.get("title") or "").strip()
        images, videos, links = list(cd["images"]), list(cd["videos"]), list(cd["youtube"])
        total_items = (1 if images and cd["mode"] == "album" else len(images)) + len(videos) + len(links)
        counter = {"n": 0}
        created = []

        def next_title(fallback):
            counter["n"] += 1
            if not title:
                return fallback
            return title if total_items == 1 else f"{title} — {counter['n']}"

        if images:
            if cd["mode"] == "album":
                item = MediaItem.objects.create(title=next_title(_title_from(images[0].name)), media_type="photo",
                                                image=images[0], **common)
                add_photos(item, images[1:])
                created.append((item, len(images)))
            else:
                for f in images:
                    item = MediaItem.objects.create(title=next_title(_title_from(f.name)), media_type="photo", image=f, **common)
                    created.append((item, 1))
        for f in videos:
            item = MediaItem.objects.create(title=next_title(_title_from(f.name)), media_type="video", video_file=f, **common)
            created.append((item, 1))
        for url in links:
            vid = url.rstrip("/").split("v=")[-1].split("/")[-1].split("&")[0].split("?")[0]
            item = MediaItem.objects.create(title=next_title(f"YouTube video {vid}"), media_type="video", video_url=url, **common)
            self._youtube_thumb(item, vid)
            created.append((item, 1))
        return created

    @staticmethod
    def _youtube_thumb(item, vid):
        """YouTube muqovasini yuklashga urinadi (internet bo'lmasa — jim o'tadi)."""
        import urllib.request

        from django.core.files.base import ContentFile

        try:
            data = urllib.request.urlopen(
                urllib.request.Request(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", headers={"User-Agent": "Mozilla/5.0"}),
                timeout=10).read()
            if len(data) > 2000:
                item.image.save(f"yt_{vid}.jpg", ContentFile(data), save=True)
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------------ albomdan bittalab o'chirish
def delete_album_item(request, kind, pk):
    """Admin: fotoalbomdagi bitta rasm yoki videoni darhol o'chiradi (AJAX, POST)."""
    from django.http import JsonResponse

    model = {"photo": Photo, "video": Video}.get(kind)
    if request.method != "POST" or model is None:
        return JsonResponse({"ok": False, "error": "Noto'g'ri so'rov"}, status=400)
    if not (request.user.is_active and request.user.is_staff):
        return JsonResponse({"ok": False, "error": "Ruxsat yo'q"}, status=403)
    item = model.objects.filter(pk=pk).select_related("content_type").first()
    if item is None:
        return JsonResponse({"ok": True})  # allaqachon o'chirilgan
    owner_model = item.content_type.model_class()
    if owner_model is not None:
        perm = f"{owner_model._meta.app_label}.change_{owner_model._meta.model_name}"
        if not request.user.has_perm(perm):
            return JsonResponse({"ok": False, "error": "Ruxsat yo'q"}, status=403)
    files = [f for f in (getattr(item, "image", None), getattr(item, "video_file", None), getattr(item, "cover", None)) if f]
    item.delete()
    for f in files:
        try:
            f.storage.delete(f.name)
        except Exception:  # noqa: BLE001 - fayl topilmasa ham yozuv o'chirilgan
            pass
    return JsonResponse({"ok": True})
