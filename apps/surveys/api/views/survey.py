from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.surveys.api.pagination import SurveyPagination
from apps.surveys.api.serializers.question import NextQuestionSerializer
from apps.surveys.api.serializers.survey import SurveySerializer
from apps.surveys.models import Participation, Survey
from apps.surveys.utils.progress import unanswered_questions


class SurveyViewSet(ReadOnlyModelViewSet):
    serializer_class = SurveySerializer
    pagination_class = SurveyPagination

    def get_queryset(self):
        return Survey.objects.filter(
            Q(is_published=True) | Q(author=self.request.user),
        ).prefetch_related("questions__choices")


class NextQuestionView(GenericAPIView):
    serializer_class = NextQuestionSerializer

    def get_queryset(self):
        return Survey.objects.filter(Q(is_published=True) | Q(author=self.request.user))

    def get(self, request, pk):
        survey = self.get_object()
        try:
            participation = Participation.start(survey, request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        completed = participation.completed_at is not None
        question = (
            None
            if completed
            else (unanswered_questions(survey, participation).prefetch_related("choices").first())
        )
        return Response(
            {
                "state": "completed" if completed else "in_progress",
                "participation_id": participation.pk,
                "progress": {
                    "answered": participation.answers.count(),
                    "total": survey.questions.count(),
                },
                "question": self.get_serializer(question).data if question else None,
            }
        )
