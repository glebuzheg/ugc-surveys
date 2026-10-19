from django.conf import settings
from django.db import models


class Survey(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_index=False)
    title = models.CharField(max_length=255)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_published", "id"]),
            models.Index(fields=["author", "id"]),
        ]
