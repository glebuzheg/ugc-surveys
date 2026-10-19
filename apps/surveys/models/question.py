from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Max

from .survey import Survey


class Question(models.Model):
    id = models.BigAutoField("Идентификатор", primary_key=True)
    survey = models.ForeignKey(
        "surveys.Survey",
        verbose_name="Опрос",
        related_name="questions",
        on_delete=models.CASCADE,
        db_index=False,
    )
    text = models.TextField("Текст вопроса")
    position = models.PositiveIntegerField("Позиция", blank=True, validators=[MinValueValidator(1)])
    allow_custom_answer = models.BooleanField("Разрешить собственный ответ", default=False)

    def __str__(self):
        return self.text

    @transaction.atomic
    def save(self, *args, **kwargs):
        Survey.objects.select_for_update().get(pk=self.survey_id)
        if self.position is None:
            last = (
                type(self)
                .objects.filter(survey_id=self.survey_id)
                .aggregate(
                    last=Max("position"),
                )["last"]
            )
            self.position = (last or 0) + 1
        return super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        Survey.objects.select_for_update().get(pk=self.survey_id)
        return super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "вопрос"
        verbose_name_plural = "вопросы"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "position"],
                name="question_survey_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0), name="question_position_gt_0"
            ),
        ]
