"""lex.uz (Qonunchilik ma'lumotlari milliy bazasi) dan hujjatlarning PDF / Word fayllari va ma'lumotlarini yuklaydi.

    python manage.py fetch_lex_files            # fayli yo'q hujjatlar uchun
    python manage.py fetch_lex_files --force    # hammasini qayta yuklash

Hujjatning «Manba havolasi» lex.uz bo'lishi kerak (masalan https://lex.uz/docs/4399172).
"""
import html
import re
import urllib.request
from datetime import date

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.models import Document

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGMuseum/1.0"}
ISSUERS = [
    (r"Oliy Majlis", "O‘zbekiston Respublikasi Oliy Majlisi"),
    (r"Qonuni", "O‘zbekiston Respublikasi Oliy Majlisi (Qonun)"),
    (r"Prezidentining (qarori|Qarori|Farmoni|farmoni)", "O‘zbekiston Respublikasi Prezidenti"),
    (r"Vazirlar Mahkamasining", "O‘zbekiston Respublikasi Vazirlar Mahkamasi"),
]


def fetch(url, timeout=60):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
    return r.read(), r.headers.get("Content-Type", "")


def dmy(s):
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", s or "")
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def page_text(raw):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    return [ln.strip() for ln in t.split("\n") if ln.strip()]


def pdf_pages(data):
    n = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return n


class Command(BaseCommand):
    help = "lex.uz dan hujjatlarning PDF/Word fayllari va ma'lumotlarini yuklaydi"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        done = 0
        for doc in Document.objects.filter(source_url__icontains="lex.uz"):
            m = re.search(r"/(?:docs|pdfs)/-?(\d+)", doc.source_url)
            if not m:
                continue
            if doc.file and doc.file_word and not opts["force"]:
                continue
            lex_id = m.group(1)
            base = None
            lines = []
            for cand in (f"https://lex.uz/uz/docs/-{lex_id}", f"https://lex.uz/docs/{lex_id}"):
                try:
                    raw, _ = fetch(cand)
                    lines = page_text(raw.decode("utf-8", "ignore"))
                    if len(lines) > 60:
                        base = cand
                        break
                except Exception as e:  # noqa: BLE001
                    self.stderr.write(f"  {cand}: {e}")
            if not base:
                self.stderr.write(self.style.WARNING(f"[{doc.doc_number}] lex.uz sahifasi ochilmadi"))
                continue
            text = "\n".join(lines[:120])
            # ma'lumotlar
            st = re.search(r"Hujjat kuchini yo.qotgan\s*(\d{2}\.\d{2}\.\d{4})", text)
            doc.status = f"Kuchini yo‘qotgan ({st.group(1)})" if st else "Amalda"
            eff = next((lines[i + 1] for i, ln in enumerate(lines[:150]) if ln == "Kuchga kirish sanasi" and i + 1 < len(lines)), "")
            doc.effective_date = dmy(eff) or doc.effective_date
            for rx, name in ISSUERS:
                if re.search(rx, doc.summary or ""):
                    doc.issuer = name
                    break
            pub = next((ln for ln in reversed(lines) if re.search(r"Qonun hujjatlari ma.lumotlari milliy bazasi|Qonunchilik ma.lumotlari milliy bazasi", ln)), "")
            doc.publication = pub.strip("() ")[:255]
            safe = re.sub(r"[^\w.-]+", "_", f"{doc.doc_number or lex_id}_{doc.date or ''}")
            try:
                pdf, ct = fetch(base + "?type=pdf", 120)
                if pdf[:4] == b"%PDF":
                    if doc.file:
                        doc.file.delete(save=False)
                    doc.file.save(f"{safe}.pdf", ContentFile(pdf), save=False)
                    doc.pages = pdf_pages(pdf) or doc.pages
            except Exception as e:  # noqa: BLE001
                self.stderr.write(f"  PDF: {e}")
            try:
                word, ct = fetch(base + "?type=doc", 120)
                if len(word) > 500:
                    if doc.file_word:
                        doc.file_word.delete(save=False)
                    doc.file_word.save(f"{safe}.doc", ContentFile(word), save=False)
            except Exception as e:  # noqa: BLE001
                self.stderr.write(f"  Word: {e}")
            doc.doc_count = int(bool(doc.file)) + int(bool(doc.file_word))
            doc.save()
            done += 1
            self.stdout.write(f"[{doc.doc_number}] {doc.status} | kuchga kirgan: {doc.effective_date} | "
                              f"PDF: {'✓' if doc.file else '—'} ({doc.pages} bet) | Word: {'✓' if doc.file_word else '—'}")
        self.stdout.write(self.style.SUCCESS(f"Tayyor: {done} ta hujjat yangilandi."))
