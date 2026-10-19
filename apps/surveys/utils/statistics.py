from django.db import connection, transaction
from django.db.models import Avg, Count, F, Q

from apps.surveys.models import Answer


@transaction.atomic
def survey_statistics(survey):
    # READ COMMITTED would give each aggregate a different snapshot.
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    summary = survey.participations.aggregate(
        started_count=Count("pk"),
        completed_count=Count("pk", filter=Q(completed_at__isnull=False)),
        average_duration=Avg(F("completed_at") - F("started_at")),
    )
    duration = summary.pop("average_duration")
    started, completed = summary["started_count"], summary["completed_count"]
    summary.update(
        in_progress_count=started - completed,
        completion_rate=completed / started if started else 0,
        average_completion_seconds=duration.total_seconds() if duration is not None else None,
    )
    counts = {
        (row["question_id"], row["choice_id"]): row["count"]
        for row in Answer.objects.filter(question__survey=survey)
        .order_by()
        .values("question_id", "choice_id")
        .annotate(count=Count("pk"))
    }
    questions = []
    for question in survey.questions.prefetch_related("choices"):
        custom_count = counts.get((question.pk, None), 0)
        choices = [
            {"id": choice.pk, "text": choice.text, "count": counts.get((question.pk, choice.pk), 0)}
            for choice in question.choices.all()
        ]
        total = custom_count + sum(choice["count"] for choice in choices)
        maximum = max((choice["count"] for choice in choices), default=0)
        for choice in choices:
            choice["share"] = choice["count"] / total if total else 0
        questions.append(
            {
                "id": question.pk,
                "text": question.text,
                "answers_count": total,
                "custom_answers_count": custom_count,
                "choices": choices,
                "popular_choice_ids": [
                    choice["id"] for choice in choices if maximum and choice["count"] == maximum
                ],
            }
        )
    return {**summary, "answers_count": sum(counts.values()), "questions": questions}
