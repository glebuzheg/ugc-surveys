from django.db import transaction
from django.db.models import Max
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from apps.surveys.api.exceptions import Conflict
from apps.surveys.api.serializers.question import QuestionSerializer
from apps.surveys.models import Question, Survey


class QuestionViewSet(ModelViewSet):
    serializer_class = QuestionSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        survey = get_object_or_404(Survey, pk=self.kwargs["survey_pk"], author=self.request.user)
        return survey.questions.all()

    @transaction.atomic
    def perform_create(self, serializer):
        survey = get_object_or_404(
            Survey.objects.select_for_update(),
            pk=self.kwargs["survey_pk"],
            author=self.request.user,
        )
        position = (survey.questions.aggregate(last=Max("position"))["last"] or 0) + 1
        serializer.save(survey=survey, position=position)

    @transaction.atomic
    def perform_update(self, serializer):
        get_object_or_404(
            Survey.objects.select_for_update(),
            pk=self.kwargs["survey_pk"],
            author=self.request.user,
        )
        get_object_or_404(Question, pk=serializer.instance.pk)
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        get_object_or_404(
            Survey.objects.select_for_update(),
            pk=self.kwargs["survey_pk"],
            author=self.request.user,
        )
        try:
            instance.delete()
        except ProtectedError as exc:
            raise Conflict("protected_data", "Question already has answers.") from exc
