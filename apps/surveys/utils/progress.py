from django.db.models import Exists, OuterRef

from apps.surveys.models import Answer


def unanswered_questions(survey, participation):
    answers = Answer.objects.filter(participation=participation, question_id=OuterRef("pk"))
    return survey.questions.filter(~Exists(answers)).order_by("position")
