"""DEBUG rejimida media fayllarni HTTP Range (qisman yuklash) qo'llovi bilan berish.

Django'ning standart static.serve() Range'ni qo'llamaydi — shuning uchun brauzer videoni
oldinga o'tkazolmaydi, ba'zi mp4 fayllar (moov oxirida) umuman ochilmaydi.
"""
import mimetypes
import os
import re

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotModified
from django.utils._os import safe_join
from django.utils.http import http_date
from django.views.static import was_modified_since

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def serve_media(request, path):
    try:
        full = safe_join(settings.MEDIA_ROOT, path)
    except Exception:  # noqa: BLE001 — MEDIA_ROOT tashqarisiga chiqish urinishi
        raise Http404
    if not os.path.isfile(full):
        raise Http404
    stat = os.stat(full)
    ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
    if not was_modified_since(request.META.get("HTTP_IF_MODIFIED_SINCE"), stat.st_mtime):
        return HttpResponseNotModified()
    size = stat.st_size
    m = RANGE_RE.match(request.META.get("HTTP_RANGE", ""))
    if m and (m.group(1) or m.group(2)):
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
        end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            resp = HttpResponse(status=416)
            resp["Content-Range"] = f"bytes */{size}"
            return resp
        with open(full, "rb") as f:
            f.seek(start)
            data = f.read(end - start + 1)
        resp = HttpResponse(data, status=206, content_type=ctype)
        resp["Content-Range"] = f"bytes {start}-{end}/{size}"
        resp["Content-Length"] = str(len(data))
    else:
        resp = FileResponse(open(full, "rb"), content_type=ctype)
        resp["Content-Length"] = str(size)
    resp["Accept-Ranges"] = "bytes"
    resp["Last-Modified"] = http_date(stat.st_mtime)
    return resp
