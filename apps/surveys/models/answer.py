from django.db import models


class Answer(models.Model):
    id = models.BigAutoField("Идентификатор", primary_key=True)
    participation = models.ForeignKey(
        "surveys.Participation",
        verbose_name="Прохождение",
        related_name="answers",
        on_delete=models.CASCADE,
        db_index=False,
    )
    question = models.ForeignKey(
        "surveys.Question",
        verbose_name="Вопрос",
        related_name="answers",
        on_delete=models.PROTECT,
        db_index=False,
    )
    choice = models.ForeignKey(
        "surveys.Choice",
        verbose_name="Вариант ответа",
        related_name="answers",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    custom_text = models.CharField("Собственный ответ", max_length=2000, blank=True, default="")
    created_at = models.DateTimeField("Дата ответа", auto_now_add=True)

    def __str__(self):
        return f"Ответ №{self.pk} на вопрос №{self.question_id}"

    class Meta:
        verbose_name = "ответ"
        verbose_name_plural = "ответы"
        indexes = [models.Index(fields=["question", "choice"])]
        constraints = [
            models.UniqueConstraint(
                fields=["participation", "question"],
                name="answer_participation_question_unique",
            ),
            models.CheckConstraint(
                condition=(models.Q(choice__isnull=False, custom_text=""))
                | (models.Q(choice__isnull=True) & ~models.Q(custom_text="")),
                name="answer_exactly_one_type",
            ),
        ]
