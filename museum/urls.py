from django.conf import settings
import re

from django.conf.urls.static import static  # noqa: F401
from django.contrib import admin
from django.urls import include, path, re_path

from core.admin_bulk import delete_album_item
from core.media_serve import serve_media

urlpatterns = [
    # Admin: fotoalbom / videodagi bitta elementni o'chirish (admin.site.urls dan oldin bo'lishi shart)
    path("admin/album/<str:kind>/<int:pk>/delete/", admin.site.admin_view(delete_album_item), name="admin_album_delete"),
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]

if settings.DEBUG:
    # Range qo'llovi bilan (video oldinga o'tkazish va mp4 ochilishi uchun)
    urlpatterns += [re_path(r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")), serve_media)]

admin.site.site_header = "Milliy gvardiya elektron muzeyi boshqaruvi"
admin.site.site_title = "MG Elektron muzey"
admin.site.index_title = "Boshqaruv paneli"
