from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from .survey import Survey


class Participation(models.Model):
    id = models.BigAutoField("Идентификатор", primary_key=True)
    survey = models.ForeignKey(
        "surveys.Survey",
        verbose_name="Опрос",
        related_name="participations",
        on_delete=models.PROTECT,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.PROTECT,
        db_index=False,
    )
    started_at = models.DateTimeField("Начало прохождения", default=timezone.now)
    completed_at = models.DateTimeField("Завершение прохождения", null=True, blank=True)

    def __str__(self):
        return f"Прохождение №{self.pk}: опрос №{self.survey_id}, пользователь №{self.user_id}"

    @classmethod
    def start(cls, survey, user):
        existing = cls.objects.filter(survey=survey, user=user).first()
        if existing:
            return existing
        with transaction.atomic():
            Survey.objects.select_for_update().get(pk=survey.pk)
            if not survey.questions.exists():
                raise ValidationError("В опросе нет вопросов.", code="no_questions")
            participation, _ = cls.objects.get_or_create(survey=survey, user=user)
            return participation

    class Meta:
        verbose_name = "прохождение"
        verbose_name_plural = "прохождения"
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
