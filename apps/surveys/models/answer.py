from django.db import models


class Answer(models.Model):
    participation = models.ForeignKey(
        "surveys.Participation",
        related_name="answers",
        on_delete=models.CASCADE,
        db_index=False,
    )
    question = models.ForeignKey(
        "surveys.Question",
        related_name="answers",
        on_delete=models.PROTECT,
        db_index=False,
    )
    choice = models.ForeignKey(
        "surveys.Choice",
        related_name="answers",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    custom_text = models.CharField(max_length=2000, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
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
