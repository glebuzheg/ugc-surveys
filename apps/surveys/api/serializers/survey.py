from rest_framework import serializers

from apps.surveys.models import Survey

from .question import NextQuestionSerializer


class SurveySerializer(serializers.ModelSerializer):
    questions = NextQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Survey
        fields = ["id", "author", "title", "is_published", "created_at", "questions"]
        read_only_fields = fields
