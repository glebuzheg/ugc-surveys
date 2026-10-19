from django.conf import settings
from django.db import models, transaction


class Survey(models.Model):
    id = models.BigAutoField("Идентификатор", primary_key=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор", on_delete=models.PROTECT, db_index=False
    )
    title = models.CharField("Название", max_length=255)
    is_published = models.BooleanField("Опубликован", default=False)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    def __str__(self):
        return self.title

    @transaction.atomic
    def delete(self, *args, **kwargs):
        type(self).objects.select_for_update().get(pk=self.pk)
        return super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "опрос"
        verbose_name_plural = "опросы"
        indexes = [
            models.Index(fields=["is_published", "id"]),
            models.Index(fields=["author", "id"]),
        ]
