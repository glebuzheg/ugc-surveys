from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Max

from .survey import Survey


class Choice(models.Model):
    id = models.BigAutoField("Идентификатор", primary_key=True)
    question = models.ForeignKey(
        "surveys.Question",
        verbose_name="Вопрос",
        related_name="choices",
        on_delete=models.CASCADE,
        db_index=False,
    )
    text = models.CharField("Текст варианта", max_length=500)
    position = models.PositiveIntegerField("Позиция", blank=True, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.text

    @transaction.atomic
    def save(self, *args, **kwargs):
        Survey.objects.select_for_update().get(pk=self.question.survey_id)
        if self.position is None:
            last = (
                type(self)
                .objects.filter(question_id=self.question_id)
                .aggregate(
                    last=Max("position"),
                )["last"]
            )
            self.position = (last or 0) + 1
        return super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        Survey.objects.select_for_update().get(pk=self.question.survey_id)
        return super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "вариант ответа"
        verbose_name_plural = "варианты ответов"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"],
                name="choice_question_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(condition=models.Q(position__gt=0), name="choice_position_gt_0"),
        ]
