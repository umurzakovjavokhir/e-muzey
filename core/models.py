from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan sana", auto_now=True)

    class Meta:
        abstract = True


class Photo(models.Model):
    """Har qanday material (bino, bo'linma, tadbir, media va h.k.) uchun fotoalbom rasmi."""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    image = models.ImageField("Rasm", upload_to="photos/")
    title = models.CharField("Izoh", max_length=255, blank=True)
    year = models.PositiveSmallIntegerField("Yil", null=True, blank=True, db_index=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Fotoalbom rasmi"
        verbose_name_plural = "Fotoalbom rasmlari"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title or self.image.name


class Video(models.Model):
    """Har qanday material (shaxs, qahramon va h.k.) uchun video: fayl yoki YouTube havola."""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    video_file = models.FileField(
        "Video fayl", upload_to="videos/", blank=True,
        help_text="mp4 / webm / mov fayl.",
    )
    video_url = models.URLField("YouTube havola", blank=True)
    cover = models.ImageField("Muqova rasmi", upload_to="videos/covers/", blank=True)
    title = models.CharField("Izoh", max_length=255, blank=True)
    year = models.PositiveSmallIntegerField("Yil", null=True, blank=True, db_index=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videolar"
        ordering = ["order", "id"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.video_file and not self.video_url:
            raise ValidationError("Video fayl yuklang yoki YouTube havolasini kiriting.")

    def __str__(self):
        return self.title or (self.video_file.name if self.video_file else self.video_url)


class Translation(models.Model):
    """Sayt matnlarining tarjimalari (o'zbekcha matn -> ruscha / inglizcha)."""
    source = models.TextField("O'zbekcha matn (lotin)")
    source_hash = models.CharField(max_length=64, unique=True, editable=False)
    ru = models.TextField("Ruscha", blank=True)
    en = models.TextField("Inglizcha", blank=True)
    is_ui = models.BooleanField("Interfeys matni", default=False)

    class Meta:
        verbose_name = "Tarjima"
        verbose_name_plural = "Tarjimalar"

    @staticmethod
    def normalize(text):
        import re
        text = re.sub(r"[‘’ʻʼ`´]", "'", text or "")
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def make_hash(cls, text):
        import hashlib
        return hashlib.sha256(cls.normalize(text).encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        self.source_hash = self.make_hash(self.source)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.source[:80]


class Region(models.Model):
    name = models.CharField("Nomi", max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    order = models.PositiveIntegerField("Tartib", default=0)
    is_other = models.BooleanField("Boshqa hududlar", default=False)

    class Meta:
        verbose_name = "Hudud"
        verbose_name_plural = "Hududlar"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("Nomi", max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    icon = models.CharField("Belgi (emoji/icon)", max_length=40, blank=True, default="📁")
    color = models.CharField("Rangi", max_length=20, default="#1d4ed8")
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField("Nomi", max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "Teg"
        verbose_name_plural = "Teglar"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Department(TimeStampedModel):
    """Bo'linma — bo'linmalar tarixi bo'limi."""
    title = models.CharField("Bo'linma nomi", max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    summary = models.CharField("Qisqa tavsif", max_length=400, blank=True)
    description = models.TextField("Tavsif", blank=True)
    image = models.ImageField("Asosiy rasm", upload_to="departments/", blank=True)
    year_start = models.PositiveIntegerField("Boshlanish yili", default=2017)
    year_end = models.CharField("Tugash yili", max_length=20, default="hozirgacha")
    region = models.ForeignKey(
        Region, verbose_name="Hudud", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="departments",
    )
    category = models.ForeignKey(
        Category, verbose_name="Kategoriya", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="departments",
    )
    photo_count = models.PositiveIntegerField("Foto", default=0)
    video_count = models.PositiveIntegerField("Video", default=0)
    doc_count = models.PositiveIntegerField("Hujjat", default=0)
    views = models.PositiveIntegerField("Ko'rishlar", default=0)
    is_featured = models.BooleanField("Muhim", default=False)
    order = models.PositiveIntegerField("Tartib", default=0)
    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")

    class Meta:
        verbose_name = "Bo'linma"
        verbose_name_plural = "Bo'linmalar"
        ordering = ["order", "title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:280] or "bolinma"
            base = self.slug
            n = 2
            while Department.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:jamoat")  # "Bo'linmalar tarixi" bo'limi olib tashlangan

    @property
    def year_range(self):
        return f"{self.year_start} - {self.year_end}"

    def __str__(self):
        return self.title


class Building(TimeStampedModel):
    """Yangi bino."""
    BUILDING_TYPES = [
        ("mamuriy", "Ma'muriy bino"),
        ("quv_markaz", "O'quv markazi"),
        ("yashash", "Yashash majmuasi"),
        ("tibbiy", "Tibbiy inshoot"),
        ("bolinma", "Bo'linma binosi"),
        ("logistika", "Logistika markazi"),
        ("aloqa", "Aloqa markazi"),
        ("sport", "Sport majmuasi"),
        ("safarbarlik", "Safarbarlik inshooti"),
        ("nazorat", "Nazorat punkti"),
        ("texnik", "Texnik xizmat"),
    ]
    title = models.CharField("Bino nomi", max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    building_type = models.CharField("Turi", max_length=40, choices=BUILDING_TYPES, default="mamuriy")
    year = models.PositiveIntegerField("Topshirilgan yil", default=2023)
    handover_date = models.DateField("Topshirilgan sana", null=True, blank=True)
    address = models.CharField("Manzil", max_length=255, blank=True)
    region = models.ForeignKey(
        Region, verbose_name="Hudud", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="buildings",
    )
    department = models.ForeignKey(
        Department, verbose_name="Tegishli bo'linma", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="buildings",
    )
    area_m2 = models.PositiveIntegerField("Bino maydoni, m²", default=0)
    cost = models.DecimalField("Qurilish qiymati, mlrd so'm", max_digits=12, decimal_places=2, default=0)
    capacity = models.PositiveIntegerField("Xizmat o'rinlari", default=0)
    description = models.TextField("Tavsif", blank=True)
    image = models.ImageField("Asosiy rasm", upload_to="buildings/", blank=True)
    photo_count = models.PositiveIntegerField("Foto", default=0)
    video_count = models.PositiveIntegerField("Video", default=0)
    doc_count = models.PositiveIntegerField("Hujjat", default=0)
    views = models.PositiveIntegerField("Ko'rishlar", default=0)
    is_active = models.BooleanField("Foydalanishga topshirilgan", default=True)
    order = models.PositiveIntegerField("Tartib", default=0)
    source_url = models.URLField("Manba havolasi", blank=True)
    latitude = models.DecimalField("Kenglik (latitude)", max_digits=9, decimal_places=6, null=True, blank=True,
                                   help_text="Masalan: 41.311081. Google Maps'da joyga o'ng tugma bosib nusxa olish mumkin.")
    longitude = models.DecimalField("Uzunlik (longitude)", max_digits=9, decimal_places=6, null=True, blank=True,
                                    help_text="Masalan: 69.240562")
    LOCATION_PRECISION = [("aniq", "Aniq manzil"), ("tuman", "Tuman markazi"), ("viloyat", "Viloyat / shahar markazi (taxminiy)")]
    location_precision = models.CharField("Joylashuv aniqligi", max_length=10, choices=LOCATION_PRECISION, default="aniq")
    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")

    class Meta:
        verbose_name = "Yangi bino"
        verbose_name_plural = "Yangi binolar"
        ordering = ["-year", "order", "title"]

    def save(self, *args, **kwargs):
        if self.handover_date:
            self.year = self.handover_date.year
        if not self.slug:
            self.slug = slugify(self.title)[:280] or "bino"
            base = self.slug
            n = 2
            while Building.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:bino_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class YearArchive(TimeStampedModel):
    """Yillar bo'yicha tarix yili."""
    year = models.PositiveIntegerField("Yil", unique=True)
    title = models.CharField("Yil nomi", max_length=255)
    subtitle = models.CharField("Shior", max_length=255, blank=True)
    description = models.TextField("Tavsif", blank=True)
    image = models.ImageField("Banner rasm", upload_to="years/", blank=True)
    video_url = models.URLField("Video havolasi", blank=True)
    new_buildings = models.PositiveIntegerField("Yangi bino va inshoot", default=0)
    new_departments = models.PositiveIntegerField("Yangi bo'linma", default=0)
    achievements = models.PositiveIntegerField("Erishilgan g'alaba", default=0)
    documents = models.PositiveIntegerField("Hujjat va material", default=0)
    is_featured = models.BooleanField("Muhim yil", default=False)

    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")

    class Meta:
        verbose_name = "Yil"
        verbose_name_plural = "Yillar"
        ordering = ["-year"]

    def get_absolute_url(self):
        return reverse("core:yil_detail", kwargs={"year": self.year})

    def __str__(self):
        return str(self.year)


class MaterialQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class AbstractMaterial(TimeStampedModel):
    MATERIAL_TYPES = [
        ("news", "Yangilik"),
        ("building", "Yangi bino"),
        ("bolinma", "Bo'linma"),
        ("tadbir", "Tadbir"),
        ("galaba", "Erishilgan g'alaba"),
        ("hujjat", "Hujjat"),
        ("foto", "Foto"),
        ("video", "Video"),
        ("malumot", "Ma'lumot"),
    ]
    title = models.CharField("Sarlavha", max_length=300)
    slug = models.SlugField(max_length=320, unique=True, blank=True)
    material_type = models.CharField("Material turi", max_length=20, choices=MATERIAL_TYPES, default="news")
    category = models.ForeignKey(
        Category, verbose_name="Kategoriya", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(class)ss",
    )
    date = models.DateField("Sana", null=True, blank=True)
    year = models.PositiveIntegerField("Yil", default=2023, db_index=True)
    region = models.ForeignKey(
        Region, verbose_name="Hudud", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(class)ss",
    )
    department = models.ForeignKey(
        Department, verbose_name="Tegishli bo'linma", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="%(class)ss",
    )
    summary = models.CharField("Qisqa tavsif", max_length=400, blank=True)
    description = models.TextField("Tavsif", blank=True)
    body = models.TextField("To'liq matn", blank=True)
    image = models.ImageField("Asosiy rasm", upload_to="%(class)ss/", blank=True)
    tags = models.ManyToManyField(Tag, verbose_name="Teglar", blank=True, related_name="%(class)ss")
    photo_count = models.PositiveIntegerField("Foto", default=0)
    video_count = models.PositiveIntegerField("Video", default=0)
    doc_count = models.PositiveIntegerField("Hujjat", default=0)
    views = models.PositiveIntegerField("Ko'rishlar", default=0)
    is_published = models.BooleanField("Chop etilgan", default=True)
    is_featured = models.BooleanField("Muhim", default=False)
    source_url = models.URLField("Manba havolasi", blank=True)
    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")

    objects = MaterialQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["-date", "-created_at"]

    def save(self, *args, **kwargs):
        if self.date:
            self.year = self.date.year
        if not self.slug:
            self.slug = slugify(self.title)[:320] or "material"
            base = self.slug
            n = 2
            model = type(self)
            while model.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Achievement(AbstractMaterial):
    """Erishilgan g'alaba."""
    ACHIEVEMENT_TYPES = [
        ("xalqaro", "Xalqaro musobaqalar"),
        ("respublika", "Respublika musobaqalar"),
        ("sport", "Sport yutuqlari"),
        ("kasbiy", "Kasbiy mahorat"),
        ("innovatsion", "Innovatsion loyihalar"),
        ("mukofot", "Mukofotlar"),
        ("taktik", "Taktik o'quvlar"),
        ("boshqa", "Boshqa"),
    ]
    achievement_type = models.CharField(
        "Yutuq turi", max_length=30, choices=ACHIEVEMENT_TYPES, default="xalqaro",
    )

    class Meta:
        verbose_name = "Erishilgan g'alaba"
        verbose_name_plural = "Erishilgan g'alabalar"
        ordering = ["-date", "-created_at"]

    def get_absolute_url(self):
        return reverse("core:galaba_detail", kwargs={"slug": self.slug})


class Event(AbstractMaterial):
    """Tadbir va marosim."""
    EVENT_TYPES = [
        ("marosim", "Marosim"),
        ("musobaqa", "Musobaqa"),
        ("tashrif", "Tashrif"),
        ("tanlov", "Tanlov"),
        ("trening", "Trening"),
        ("boshqa", "Boshqa"),
    ]
    event_type = models.CharField("Tadbir turi", max_length=30, choices=EVENT_TYPES, default="marosim")
    location = models.CharField("Joylashuv", max_length=255, blank=True)
    start_time = models.TimeField("Boshlanish vaqti", null=True, blank=True)

    class Meta:
        verbose_name = "Tadbir"
        verbose_name_plural = "Tadbirlar va marosimlar"
        ordering = ["-date", "-created_at"]

    def get_absolute_url(self):
        return reverse("core:tadbir_detail", kwargs={"slug": self.slug})


class Education(AbstractMaterial):
    """Ta'minot yo'nalishlari materiali (kiyim-kechak, qurol-aslaha, tibbiyot, uy-joy, yangi binolar).

    Model nomi tarixiy sabablarga ko'ra "Education" bo'lib qolgan (/talim/ manzili ham)."""
    EDU_TYPES = [
        ("kiyim", "Kiyim-kechak ta'minoti"),
        ("qurol", "Qurol-aslaha va texnika"),
        ("tibbiyot", "Tibbiy ta'minot"),
        ("uy_joy", "Uy-joy bilan ta'minlash"),
        ("bino", "Yangi bino va inshootlar"),
    ]
    edu_type = models.CharField("Ta'minot turi", max_length=30, choices=EDU_TYPES, default="bino")
    duration = models.CharField("Davomiyligi", max_length=100, blank=True)
    students_count = models.PositiveIntegerField("Qamrab olinganlar soni", default=0)

    class Meta:
        verbose_name = "Ta'minot materiali"
        verbose_name_plural = "Ta'minot yo'nalishlari"
        ordering = ["-date", "-created_at"]

    def get_absolute_url(self):
        return reverse("core:talim_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class PublicOrder(AbstractMaterial):
    """Jamoat tartibini saqlash — milliygvardiya.uz rasmiy xabarlari."""
    ORDER_TYPES = [
        ("tadbir", "Ommaviy tadbirlarda xavfsizlik"),
        ("patrul", "Patrul-post xizmati va xavfsiz muhit"),
        ("profilaktika", "Huquqbuzarliklar profilaktikasi"),
        ("qoriqlash", "Qo'riqlash xizmati"),
        ("yordam", "Fuqarolarga yordam"),
    ]
    order_type = models.CharField("Yo'nalish", max_length=30, choices=ORDER_TYPES, default="patrul")

    class Meta:
        verbose_name = "Jamoat tartibi materiali"
        verbose_name_plural = "Jamoat tartibini saqlash"
        ordering = ["-date", "-created_at"]

    def get_absolute_url(self):
        return reverse("core:jamoat_detail", kwargs={"slug": self.slug})


class Document(AbstractMaterial):
    """Hujjat va relikiya."""
    DOC_TYPES = [
        ("hujjat", "Rasmiy hujjat"),
        ("relikiya", "Relikiya"),
        ("tarixiy", "Tarixiy hujjat"),
        ("buyruq", "Buyruq"),
        ("farmoyish", "Farmoyish"),
        ("shartnoma", "Shartnoma"),
        ("boshqa", "Boshqa"),
    ]
    doc_type = models.CharField("Hujjat turi", max_length=30, choices=DOC_TYPES, default="hujjat")
    doc_number = models.CharField("Hujjat raqami", max_length=100, blank=True)
    issuer = models.CharField("Qabul qilgan organ", max_length=255, blank=True,
                              help_text="Masalan: O‘zbekiston Respublikasi Prezidenti, Vazirlar Mahkamasi, Oliy Majlis")
    effective_date = models.DateField("Kuchga kirgan sana", null=True, blank=True)
    status = models.CharField("Holati", max_length=120, blank=True, help_text="Masalan: Amalda / Kuchini yo‘qotgan (29.05.2021)")
    publication = models.CharField("Rasmiy nashr manbasi", max_length=255, blank=True)
    file = models.FileField("PDF fayl", upload_to="documents/files/", blank=True,
                            help_text="Hujjatning elektron PDF nusxasi — saytda ichida ochiladi.")
    file_word = models.FileField("Word fayl", upload_to="documents/files/", blank=True,
                                 help_text=".docx yoki .doc fayl — saytda ichida ochiladi.")
    pages = models.PositiveIntegerField("Sahifalar soni", default=0)

    class Meta:
        verbose_name = "Hujjat"
        verbose_name_plural = "Hujjatlar va relikiyalar"
        ordering = ["-date", "-created_at"]

    def get_absolute_url(self):
        return reverse("core:hujjat_detail", kwargs={"slug": self.slug})


class Person(TimeStampedModel):
    """Rahbar va shaxslar."""
    PERSON_TYPES = [
        ("rahbar", "Rahbarlar"),
        ("tarixiy", "Tarixiy shaxs"),
    ]
    full_name = models.CharField("F.I.Sh.", max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    position = models.CharField("Lavozim", max_length=255, blank=True)
    person_type = models.CharField("Turi", max_length=30, choices=PERSON_TYPES, default="rahbar")
    birth_date = models.DateField("Tug'ilgan sana", null=True, blank=True)
    service_period = models.CharField("Xizmat davri", max_length=100, blank=True)
    bio = models.TextField("Biografiya", blank=True)
    photo = models.ImageField("Surat", upload_to="persons/", blank=True)
    department = models.ForeignKey(
        Department, verbose_name="Bo'linma", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="persons",
    )
    awards = models.TextField("Mukofotlar", blank=True)
    source_url = models.URLField("Manba havolasi", blank=True)
    views = models.PositiveIntegerField("Ko'rishlar", default=0)
    order = models.PositiveIntegerField("Tartib", default=0)
    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")

    class Meta:
        verbose_name = "Shaxs"
        verbose_name_plural = "Rahbarlar va shaxslar"
        ordering = ["order", "full_name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.full_name)[:280] or "shaxs"
            base = self.slug
            n = 2
            while Person.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:shaxs_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.full_name


class Hero(TimeStampedModel):
    """Bizning qahramonlar: halok bo'lgan qahramonlar, sportchilar va davlat mukofoti sohiblari."""
    CATEGORIES = [
        ("halok", "Halok bo'lgan qahramonlar"),
        ("sportchi", "Sportchilarimiz"),
        ("mukofot", "Davlat mukofoti sohiblari"),
    ]
    full_name = models.CharField("F.I.Sh.", max_length=255)
    category = models.CharField("Toifa", max_length=20, choices=CATEGORIES, default="halok", db_index=True)
    year = models.PositiveIntegerField(
        "Yil", null=True, blank=True, db_index=True,
        help_text="Filtr uchun: halok bo'lgan / mukofotlangan / natija qayd etilgan yil.",
    )
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    rank = models.CharField("Harbiy unvon / lavozim", max_length=255, blank=True)
    birth_date = models.DateField("Tug'ilgan sana", null=True, blank=True)
    death_date = models.DateField("Halok bo'lgan sana", null=True, blank=True)
    birth_place = models.CharField("Tug'ilgan joyi", max_length=255, blank=True)
    region = models.ForeignKey(
        Region, verbose_name="Hudud", on_delete=models.SET_NULL, null=True, blank=True, related_name="heroes",
    )
    department = models.ForeignKey(
        Department, verbose_name="Bo'linma", on_delete=models.SET_NULL, null=True, blank=True, related_name="heroes",
    )
    feat = models.TextField("Jasorat tavsifi", blank=True, help_text="Qahramonlik ko'rsatilgan voqea qisqacha.")
    bio = models.TextField("Biografiya", blank=True)
    awards = models.TextField("Mukofotlar", blank=True)
    photo = models.ImageField("Surat", upload_to="heroes/", blank=True)
    source_url = models.URLField("Manba havolasi", blank=True)
    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")
    views = models.PositiveIntegerField("Ko'rishlar", default=0)
    order = models.PositiveIntegerField("Tartib", default=0)
    is_published = models.BooleanField("Chop etilgan", default=True)

    class Meta:
        verbose_name = "Qahramon / shaxsiyat"
        verbose_name_plural = "Bizning qahramonlar"
        ordering = ["order", "full_name"]

    def save(self, *args, **kwargs):
        if not self.year and self.death_date:
            self.year = self.death_date.year
        if not self.slug:
            self.slug = slugify(self.full_name)[:280] or "qahramon"
            base = self.slug
            n = 2
            while Hero.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:qahramon_detail", kwargs={"slug": self.slug})

    @property
    def life_years(self):
        a = self.birth_date.year if self.birth_date else ""
        b = self.death_date.year if self.death_date else ""
        return f"{a} — {b}" if (a or b) else ""

    @property
    def title(self):
        return self.full_name

    def __str__(self):
        return self.full_name


class ImportantDate(TimeStampedModel):
    """Muhim sana."""
    DATE_TYPES = [
        ("tashkil", "Tashkil etilgan sana"),
        ("bayram", "Bayram va tantana"),
        ("hujjat", "Hujjat qabul qilingan"),
        ("xotira", "Xotira kuni"),
        ("tarixiy", "Tarixiy voqea"),
        ("boshqa", "Boshqa"),
    ]
    title = models.CharField("Sarlavha", max_length=300)
    slug = models.SlugField(max_length=320, unique=True, blank=True)
    date_type = models.CharField("Kategoriya", max_length=20, choices=DATE_TYPES, default="tarixiy", db_index=True)
    date = models.DateField("Sana", db_index=True)
    year = models.PositiveIntegerField("Yil", default=2017, db_index=True, editable=False)
    description = models.TextField("Tavsif", blank=True)
    image = models.ImageField("Rasm", upload_to="dates/", blank=True)
    event = models.ForeignKey(
        Event, verbose_name="Tadbir", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="important_dates",
    )
    is_featured = models.BooleanField("Muhim", default=False)

    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")

    class Meta:
        verbose_name = "Muhim sana"
        verbose_name_plural = "Muhim sanalar"
        ordering = ["-date"]

    def save(self, *args, **kwargs):
        if self.date:
            self.year = self.date.year
        if not self.slug:
            self.slug = slugify(self.title)[:320] or "sana"
            base = self.slug
            n = 2
            while ImportantDate.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:sana_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class MediaItem(TimeStampedModel):
    """Foto va videoarxiv."""
    MEDIA_TYPES = [("photo", "Foto"), ("video", "Video")]
    TOPICS = [
        ("tadbir", "Tadbir va marosimlar"),
        ("xizmat", "Xizmat faoliyati"),
        ("mashgulot", "O'quv mashg'ulotlari"),
        ("sport", "Sport"),
        ("bino", "Binolar va inshootlar"),
        ("tarix", "Tarixiy materiallar"),
        ("boshqa", "Boshqa"),
    ]
    title = models.CharField("Sarlavha", max_length=300)
    slug = models.SlugField(max_length=320, unique=True, blank=True)
    media_type = models.CharField("Turi", max_length=10, choices=MEDIA_TYPES, default="photo")
    topic = models.CharField("Kategoriya", max_length=20, choices=TOPICS, default="xizmat", db_index=True)
    image = models.ImageField("Rasm", upload_to="gallery/", blank=True)
    video_url = models.URLField("Video havola", blank=True)
    video_file = models.FileField(
        "Video fayl", upload_to="videos/", blank=True,
        help_text="mp4 / webm / mov fayl. YouTube havolasi bo'lsa, «Video havola» maydonidan foydalaning.",
    )
    date = models.DateField("Sana", null=True, blank=True)
    year = models.PositiveIntegerField("Yil", default=2023, db_index=True)
    description = models.TextField("Tavsif", blank=True)
    department = models.ForeignKey(
        Department, verbose_name="Bo'linma", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="gallery",
    )
    event = models.ForeignKey(
        Event, verbose_name="Tadbir", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="gallery",
    )
    views = models.PositiveIntegerField("Ko'rishlar", default=0)
    order = models.PositiveIntegerField("Tartib", default=0)
    source_url = models.URLField("Manba havolasi", blank=True)
    photos = GenericRelation(Photo)
    videos = GenericRelation("Video")

    class Meta:
        verbose_name = "Media material"
        verbose_name_plural = "Foto va videoarxiv"
        ordering = ["-date", "order"]

    def save(self, *args, **kwargs):
        if self.date:
            self.year = self.date.year
        if not self.slug:
            self.slug = slugify(self.title)[:320] or "media"
            base = self.slug
            n = 2
            while MediaItem.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{n}"
                n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:media_detail", kwargs={"slug": self.slug})

    @property
    def duration(self):
        return "04:32"

    def __str__(self):
        return self.title


class Direction(TimeStampedModel):
    """10 ta asosiy y'onalish."""
    number = models.PositiveIntegerField("Raqam", unique=True)
    title = models.CharField("Nomi", max_length=255)
    description = models.TextField("Tavsif", blank=True)
    icon = models.CharField("Belgi (svg nomi)", max_length=40, default="star")
    url = models.CharField(
        "Havola (URL nomi)", max_length=100, blank=True, default="core:yonalishlar",
    )

    class Meta:
        verbose_name = "Yo'nalish"
        verbose_name_plural = "Yo'nalishlar"
        ordering = ["number"]

    def __str__(self):
        return f"{self.number}. {self.title}"


class Highlight(TimeStampedModel):
    """Detail sahifadagi "Asosiy natijalar va imkoniyatlar" bloki."""
    title = models.CharField("Sarlavha", max_length=255)
    text = models.TextField("Matn", blank=True)
    icon = models.CharField("Belgi", max_length=40, default="🏛️")
    building = models.ForeignKey(
        Building, verbose_name="Bino", on_delete=models.CASCADE, null=True, blank=True,
        related_name="highlights",
    )
    department = models.ForeignKey(
        Department, verbose_name="Bo'linma", on_delete=models.CASCADE, null=True, blank=True,
        related_name="highlights",
    )
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Asosiy natija"
        verbose_name_plural = "Asosiy natijalar"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class StatCard(TimeStampedModel):
    """Statistika kartochkalari."""
    SOURCES = [
        ("manual", "Qo'lda kiritiladi"),
        ("buildings", "Bino va inshootlar soni"),
        ("regions", "Viloyat va shaharlar soni"),
        ("photos", "Foto materiallar soni"),
        ("videos", "Video materiallar soni"),
        ("achievements", "G'alabalar soni"),
        ("events", "Tadbirlar soni"),
        ("documents", "Hujjatlar soni"),
        ("heroes", "Qahramonlar soni"),
        ("persons", "Shaxslar soni"),
        ("archive", "Jami arxiv materiallari"),
    ]
    source = models.CharField(
        "Manba", max_length=20, choices=SOURCES, default="manual",
        help_text="Avtomatik manba tanlansa, qiymat bazadan o'zi hisoblanadi.",
    )
    value = models.CharField("Qiymat", max_length=50, blank=True,
                             help_text="Faqat manba \"Qo'lda kiritiladi\" bo'lsa ishlatiladi.")
    label = models.CharField("Yorliq", max_length=200)
    icon = models.CharField("Belgi", max_length=40, default="📊")
    color = models.CharField("Rangi", max_length=20, default="#1d4ed8")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Statistika kartasi"
        verbose_name_plural = "Statistika kartalari"
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.label)[:100] or "stat"
        super().save(*args, **kwargs)

    def current_value(self):
        """Avtomatik manbadan joriy qiymatni hisoblaydi."""
        archive_models = (Achievement, Event, Education, Document, MediaItem, Building)
        counters = {
            "buildings": lambda: Building.objects.count(),
            "regions": lambda: Region.objects.filter(is_other=False).count(),
            "photos": lambda: Photo.objects.count() + MediaItem.objects.exclude(image="").exclude(image=None).count(),
            "videos": lambda: MediaItem.objects.filter(media_type="video").count(),
            "achievements": lambda: Achievement.objects.count(),
            "events": lambda: Event.objects.count(),
            "documents": lambda: Document.objects.count(),
            "heroes": lambda: Hero.objects.count(),
            "persons": lambda: Person.objects.count(),
            "archive": lambda: sum(m.objects.count() for m in archive_models),
        }
        fn = counters.get(self.source)
        return str(fn()) if fn else self.value

    def __str__(self):
        return f"{self.label} ({self.get_source_display()})"


class Bookmark(models.Model):
    """Saqlanganlar (session asosida)."""
    session_key = models.CharField(max_length=64, db_index=True)
    content_type = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Saqlangan"
        verbose_name_plural = "Saqlanganlar"
        unique_together = ("session_key", "content_type", "object_id")

    def __str__(self):
        return f"{self.content_type}#{self.object_id}"
