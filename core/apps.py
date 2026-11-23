from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = "Elektron muzey"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from core.i18n import bump_version
        from core.models import Translation

        post_save.connect(bump_version, sender=Translation, dispatch_uid="tr_save")
        post_delete.connect(bump_version, sender=Translation, dispatch_uid="tr_delete")

        from core import signals
        from core.models import Photo, Video

        for m in (Photo, Video):
            post_save.connect(signals.media_changed, sender=m, dispatch_uid=f"album_save_{m.__name__}")
            post_delete.connect(signals.media_changed, sender=m, dispatch_uid=f"album_del_{m.__name__}")
        post_save.connect(signals.owner_saved, dispatch_uid="album_owner_saved")
