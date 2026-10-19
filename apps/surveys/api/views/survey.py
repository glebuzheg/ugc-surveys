from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.surveys.api.exceptions import Conflict
from apps.surveys.api.serializers.participation import ParticipationSerializer
from apps.surveys.api.serializers.question import NextQuestionSerializer
from apps.surveys.api.serializers.survey import ReorderSerializer, SurveySerializer
from apps.surveys.models import Participation, Survey
from apps.surveys.utils.ordering import reorder
from apps.surveys.utils.progress import unanswered_questions
from apps.surveys.utils.statistics import survey_statistics


class SurveyViewSet(ModelViewSet):
    serializer_class = SurveySerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Survey.objects.all()
        if self.action in {"partial_update", "destroy", "reorder_questions", "statistics"}:
            return queryset.filter(author=self.request.user)
        if self.action == "list":
            if self.request.query_params.get("mine") == "1":
                return queryset.filter(author=self.request.user)
            return queryset.filter(is_published=True)
        return queryset.filter(Q(is_published=True) | Q(author=self.request.user))

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance = get_object_or_404(
                Survey.objects.select_for_update(),
                pk=instance.pk,
                author=self.request.user,
            )
            try:
                instance.delete()
            except ProtectedError as exc:
                raise Conflict("protected_data", "Survey already has participations.") from exc

    @action(detail=True, methods=["post"], url_path="reorder-questions")
    def reorder_questions(self, request, pk=None):
        survey = self.get_object()
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reorder(survey.pk, request.user, survey.questions.all(), serializer.validated_data["ids"])
        return Response({"ids": serializer.validated_data["ids"]})

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        survey = self.get_object()
        with transaction.atomic():
            # Serializes start with structural deletes; answer writes use a different lock.
            survey = get_object_or_404(
                Survey.objects.select_for_update().filter(
                    Q(is_published=True) | Q(author=request.user),
                ),
                pk=survey.pk,
            )
            participation = Participation.objects.filter(user=request.user, survey=survey).first()
            if participation:
                return Response(ParticipationSerializer(participation).data)
            if not survey.questions.exists():
                raise Conflict("no_questions", "Survey has no questions.")
            participation, created = Participation.objects.get_or_create(
                user=request.user,
                survey=survey,
            )
        return Response(ParticipationSerializer(participation).data, status=201 if created else 200)

    @action(detail=True, methods=["get"], url_path="next-question")
    def next_question(self, request, pk=None):
        survey = self.get_object()
        participation = Participation.objects.filter(user=request.user, survey=survey).first()
        completed = participation is not None and participation.completed_at is not None
        question = (
            None
            if completed
            else (unanswered_questions(survey, participation).prefetch_related("choices").first())
        )
        return Response(
            {
                "state": "completed"
                if completed
                else "in_progress"
                if participation
                else "not_started",
                "participation_id": participation.pk if participation else None,
                "progress": {
                    "answered": participation.answers.count() if participation else 0,
                    "total": survey.questions.count(),
                },
                "question": NextQuestionSerializer(question).data if question else None,
            }
        )

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        return Response(survey_statistics(self.get_object()))
