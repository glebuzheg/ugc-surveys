from django.db import models


class Choice(models.Model):
    question = models.ForeignKey(
        "surveys.Question",
        related_name="choices",
        on_delete=models.CASCADE,
        db_index=False,
    )
    text = models.CharField(max_length=500)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"],
                name="choice_question_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(condition=models.Q(position__gt=0), name="choice_position_gt_0"),
        ]
