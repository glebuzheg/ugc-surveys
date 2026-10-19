from django.db import transaction
from django.db.models import Max
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.surveys.api.exceptions import Conflict
from apps.surveys.api.serializers.choice import ChoiceSerializer
from apps.surveys.api.serializers.survey import ReorderSerializer
from apps.surveys.models import Question, Survey
from apps.surveys.utils.ordering import reorder


class ChoiceViewSet(ModelViewSet):
    serializer_class = ChoiceSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_question(self):
        return get_object_or_404(
            Question,
            pk=self.kwargs["question_pk"],
            survey_id=self.kwargs["survey_pk"],
            survey__author=self.request.user,
        )

    def get_queryset(self):
        return self.get_question().choices.all()

    @transaction.atomic
    def perform_create(self, serializer):
        get_object_or_404(
            Survey.objects.select_for_update(),
            pk=self.kwargs["survey_pk"],
            author=self.request.user,
        )
        question = self.get_question()
        position = (question.choices.aggregate(last=Max("position"))["last"] or 0) + 1
        serializer.save(question=question, position=position)

    @transaction.atomic
    def perform_update(self, serializer):
        get_object_or_404(
            Survey.objects.select_for_update(),
            pk=self.kwargs["survey_pk"],
            author=self.request.user,
        )
        get_object_or_404(self.get_question().choices, pk=serializer.instance.pk)
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
            raise Conflict("protected_data", "Choice already has answers.") from exc

    def reorder_choices(self, request, **kwargs):
        question = self.get_question()
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        # The parent may have been deleted while waiting for the survey lock.
        with transaction.atomic():
            get_object_or_404(
                Survey.objects.select_for_update(),
                pk=question.survey_id,
                author=request.user,
            )
            if not Question.objects.filter(pk=question.pk).exists():
                raise ValidationError({"ids": "Question no longer exists."})
            reorder(question.survey_id, request.user, question.choices.all(), ids)
        return Response({"ids": ids})
