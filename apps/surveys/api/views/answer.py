from django.db import IntegrityError
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.surveys.api.exceptions import Conflict
from apps.surveys.api.serializers.answer import AnswerSerializer
from apps.surveys.utils.participation import submit_answer


class AnswerViewSet(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = AnswerSerializer

    def create(self, request, participation_pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            answer, created = submit_answer(
                participation_pk, request.user, serializer.validated_data
            )
        except IntegrityError as exc:
            if getattr(exc.__cause__, "sqlstate", None) != "23503":
                raise
            raise Conflict(
                "structure_changed", "Question or choice was deleted; reload the survey."
            ) from exc
        # Input IDs are scalar fields; output uses the same shape without another FK lookup.
        return Response(
            {
                "id": answer.pk,
                "question": answer.question_id,
                "choice": answer.choice_id,
                "custom_text": answer.custom_text,
                "created_at": answer.created_at,
            },
            status=201 if created else 200,
        )
