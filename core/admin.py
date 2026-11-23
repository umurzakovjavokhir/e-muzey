from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.urls import reverse
from django.utils.html import format_html

from core.admin_bulk import BulkMediaAdminMixin, MediaBulkUploadMixin

from core.models import (
    Achievement,
    Bookmark,
    Building,
    Category,
    Direction,
    Document,
    Education,
    Event,
    Hero,
    Highlight,
    ImportantDate,
    MediaItem,
    Person,
    Photo,
    PublicOrder,
    Region,
    StatCard,
    Tag,
    Translation,
    Video,
    YearArchive,
)


class AlbumDeleteMixin:
    """Inline qatoriga darhol o'chiradigan «O'chirish» tugmasini qo'shadi."""
    album_kind = "photo"

    class Media:
        js = ("js/admin_album_delete.js",)

    @admin.display(description="O'chirish")
    def delete_btn(self, obj):
        if not obj or not obj.pk:
            return "—"
        return format_html(
            '<button type="button" class="button album-del-btn" data-kind="{}" data-url="{}" '
            'style="background:#ba2121;color:#fff;border:0;padding:6px 12px;border-radius:4px;cursor:pointer">'
            "🗑 O'chirish</button>",
            self.album_kind, reverse("admin_album_delete", args=[self.album_kind, obj.pk]),
        )


class PhotoInline(AlbumDeleteMixin, GenericTabularInline):
    model = Photo
    extra = 0
    fields = ("preview", "delete_btn", "image", "year", "title", "order")
    readonly_fields = ("preview", "delete_btn")

    @admin.display(description="Ko'rinish")
    def preview(self, obj):
        from django.utils.html import format_html

        if obj and obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:6px">', obj.image.url)
        return "—"


class VideoInline(AlbumDeleteMixin, GenericTabularInline):
    model = Video
    album_kind = "video"
    extra = 0
    fields = ("preview", "delete_btn", "video_file", "video_url", "cover", "year", "title", "order")
    readonly_fields = ("preview", "delete_btn")

    @admin.display(description="Ko'rinish")
    def preview(self, obj):
        from django.utils.html import format_html

        from core.templatetags.mg_tags import _youtube_id

        if obj and obj.video_file:
            return format_html('<video src="{}" style="height:60px;border-radius:6px" preload="metadata" muted></video>', obj.video_file.url)
        if obj and obj.video_url and _youtube_id(obj.video_url):
            return format_html('<img src="https://i.ytimg.com/vi/{}/default.jpg" style="height:60px;border-radius:6px">', _youtube_id(obj.video_url))
        return "—"


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ("short_source", "ru", "en", "is_ui")
    list_filter = ("is_ui",)
    search_fields = ("source", "ru", "en")

    @admin.display(description="O'zbekcha matn")
    def short_source(self, obj):
        return obj.source[:90]


# Hududlar admin panelda ko'rsatilmaydi (ro'yxatdan o'tkazilmagan).
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_other")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "color", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Building)
class BuildingAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "year", "building_type", "region", "latitude", "longitude", "location_precision", "is_active")
    list_filter = ("year", "building_type", "region", "is_active")
    search_fields = ("title", "address")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_active",)


# Yillar admin panelda ko'rsatilmaydi (ro'yxatdan o'tkazilmagan).
class YearArchiveAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("year", "title", "new_buildings", "new_departments", "achievements", "documents")
    list_editable = ("new_buildings", "new_departments", "achievements", "documents")


@admin.register(Achievement)
class AchievementAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "achievement_type", "date", "year", "region", "views", "is_published")
    list_filter = ("achievement_type", "year", "region", "is_published", "is_featured")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)


@admin.register(Event)
class EventAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "event_type", "date", "year", "location", "is_published")
    list_filter = ("event_type", "year", "region")
    search_fields = ("title", "location")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Education)
class EducationAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "edu_type", "date", "year", "students_count", "is_published")
    list_filter = ("edu_type", "year")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(PublicOrder)
class PublicOrderAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "order_type", "date", "year", "region", "is_published")
    list_filter = ("order_type", "year", "region")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Document)
class DocumentAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "doc_type", "doc_number", "date", "year", "pages", "is_published")
    list_filter = ("doc_type", "year")
    search_fields = ("title", "doc_number")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Person)
class PersonAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("full_name", "position", "person_type", "service_period", "media_count", "order")
    list_filter = ("person_type",)
    search_fields = ("full_name", "position")
    prepopulated_fields = {"slug": ("full_name",)}
    list_editable = ("order",)
    fieldsets = (
        (None, {"fields": ("full_name", "slug", "person_type", "position", "photo", "order")}),
        ("Ma'lumotlar", {"fields": ("birth_date", "service_period", "department", "bio", "awards", "source_url")}),
        ("Fotoalbom va videolar", {"fields": ("bulk_year", "bulk_photos", "bulk_videos", "bulk_youtube")}),
    )

    def get_queryset(self, request):
        from django.db.models import Count

        return super().get_queryset(request).annotate(
            _photos=Count("photos", distinct=True), _videos=Count("videos", distinct=True))

    @admin.display(description="Rasm / video")
    def media_count(self, obj):
        return f"{obj._photos} / {obj._videos}"


@admin.register(Hero)
class HeroAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("full_name", "category", "year", "rank", "birth_date", "death_date", "region", "is_published", "order")
    list_filter = ("category", "year", "region", "is_published")
    search_fields = ("full_name", "rank", "feat", "bio")
    prepopulated_fields = {"slug": ("full_name",)}
    list_editable = ("order", "is_published")
    fieldsets = (
        (None, {"fields": ("full_name", "slug", ("category", "year"), "rank", "photo", "is_published", "order")}),
        ("Hayot yo'li", {"fields": ("birth_date", "birth_place", "death_date", "region", "department")}),
        ("Jasorat va biografiya", {"fields": ("feat", "bio", "awards", "source_url")}),
        ("Fotoalbom va videolar", {"fields": ("bulk_year", "bulk_photos", "bulk_videos", "bulk_youtube")}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "year" in form.base_fields:
            form.base_fields["year"].required = True   # filtr uchun yil majburiy
        return form


@admin.register(ImportantDate)
class ImportantDateAdmin(BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "date_type", "date", "year", "is_featured")
    list_filter = ("date_type", "year", "is_featured")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(MediaItem)
class MediaItemAdmin(MediaBulkUploadMixin, BulkMediaAdminMixin, admin.ModelAdmin):
    inlines = [PhotoInline, VideoInline]
    list_display = ("title", "media_type", "topic", "date", "year", "views")
    list_filter = ("media_type", "topic", "year")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "icon", "url")
    list_editable = ("title", "icon", "url")


@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ("title", "building", "department", "order")
    list_filter = ("building", "department")
    list_editable = ("order",)


@admin.register(StatCard)
class StatCardAdmin(admin.ModelAdmin):
    list_display = ("label", "source", "joriy_qiymat", "icon", "color", "order")
    list_editable = ("source", "order")
    prepopulated_fields = {"slug": ("label",)}

    @admin.display(description="Joriy qiymat")
    def joriy_qiymat(self, obj):
        return obj.current_value()


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("session_key", "content_type", "object_id", "created_at")
