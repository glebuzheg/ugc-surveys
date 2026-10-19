from django.db import models


class Question(models.Model):
    survey = models.ForeignKey(
        "surveys.Survey",
        related_name="questions",
        on_delete=models.CASCADE,
        db_index=False,
    )
    text = models.TextField()
    position = models.PositiveIntegerField()
    allow_custom_answer = models.BooleanField(default=False)

    class Meta:
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
