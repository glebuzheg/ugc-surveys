from django.conf import settings
from django.db import models
from django.utils import timezone


class Participation(models.Model):
    survey = models.ForeignKey(
        "surveys.Survey",
        related_name="participations",
        on_delete=models.PROTECT,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_index=False)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "survey"], name="participation_user_survey_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(completed_at__isnull=True)
                | models.Q(completed_at__gte=models.F("started_at")),
                name="participation_completion_after_start",
            ),
        ]
