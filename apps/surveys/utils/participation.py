from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.surveys.models import Answer, Choice, Participation
from apps.surveys.utils.progress import unanswered_questions


@transaction.atomic
def submit_answer(participation_id, user, data):
    # Lock one participant, never the shared survey row on the answer hot path.
    participation = get_object_or_404(
        Participation.objects.select_for_update(of=("self",))
        .select_related("survey")
        .filter(
            Q(survey__is_published=True) | Q(survey__author=user),
        ),
        pk=participation_id,
        user=user,
    )
    question_id = data["question"]
    choice_id = data.get("choice")
    custom_text = data.get("custom_text", "")
    existing = participation.answers.filter(question_id=question_id).first()
    if existing:
        if existing.choice_id == choice_id and existing.custom_text == custom_text:
            return existing, False
        raise ValidationError("An answer to this question already exists.")
    if participation.completed_at:
        raise ValidationError("This participation is completed.")
    question = unanswered_questions(participation.survey, participation).first()
    if question is None or question.pk != question_id:
        raise ValidationError("Answer the current next question.")
    if choice_id is not None:
        if not Choice.objects.filter(pk=choice_id, question=question).exists():
            raise ValidationError({"choice": "Choice must belong to the current question."})
    elif not question.allow_custom_answer:
        raise ValidationError({"custom_text": "Custom answers are not allowed for this question."})
    answer = Answer.objects.create(
        participation=participation,
        question=question,
        choice_id=choice_id,
        custom_text=custom_text,
    )
    if not unanswered_questions(participation.survey, participation).exists():
        participation.completed_at = timezone.now()
        participation.save(update_fields=["completed_at"])
    return answer, True
