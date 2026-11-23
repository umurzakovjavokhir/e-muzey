from django.urls import path

from core import views
from core.album import album_json

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("landing/", views.landing, name="landing"),

    path("yillar/", views.yillar, name="yillar"),
    path("yillar/<int:year>/", views.yil_detail, name="yil_detail"),

    path("binolar/", views.binolar, name="binolar"),
    path("binolar/<slug:slug>/", views.bino_detail, name="bino_detail"),

    path("jamoat-tartibi/", views.jamoat, name="jamoat"),
    path("jamoat-tartibi/<slug:slug>/", views.jamoat_detail, name="jamoat_detail"),
    # eski "Bo'linmalar tarixi" havolalari
    path("bolinmalar/", views.bolinmalar_redirect),
    path("bolinmalar/<slug:slug>/", views.bolinmalar_redirect),

    path("galabalar/", views.galabalar, name="galabalar"),
    path("galabalar/<slug:slug>/", views.galaba_detail, name="galaba_detail"),

    path("tadbirlar/", views.tadbirlar, name="tadbirlar"),
    path("tadbirlar/<slug:slug>/", views.tadbir_detail, name="tadbir_detail"),

    path("talim/", views.talim, name="talim"),
    path("talim/<slug:slug>/", views.talim_detail, name="talim_detail"),

    path("galereya/", views.galereya, name="galereya"),
    path("galereya/<slug:slug>/", views.media_detail, name="media_detail"),

    path("hujjatlar/", views.hujjatlar, name="hujjatlar"),
    path("hujjatlar/<slug:slug>/", views.hujjat_detail, name="hujjat_detail"),
    path("hujjatlar/<slug:slug>/word/", views.hujjat_word, name="hujjat_word"),

    path("shaxslar/", views.shaxslar, name="shaxslar"),
    path("shaxslar/<slug:slug>/", views.shaxs_detail, name="shaxs_detail"),

    path("qahramonlar/", views.qahramonlar, name="qahramonlar"),
    path("qahramonlar/<slug:slug>/", views.qahramon_detail, name="qahramon_detail"),

    path("sanalar/", views.sanalar, name="sanalar"),
    path("sanalar/<slug:slug>/", views.sana_detail, name="sana_detail"),

    path("qidiruv/", views.qidiruv, name="qidiruv"),
    path("albom/<str:model>/<int:pk>/", album_json, name="album_json"),
    path("yonalishlar/", views.yonalishlar, name="yonalishlar"),

    path("saqlanganlar/", views.saqlanganlar, name="saqlanganlar"),
    path("saqlash/", views.bookmark_toggle, name="bookmark_toggle"),
    path("til/<str:code>/", views.set_language, name="set_language"),
]
