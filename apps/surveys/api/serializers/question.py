from rest_framework import serializers

from apps.surveys.models import Question

from .choice import ChoiceSerializer


class NextQuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "survey", "text", "position", "allow_custom_answer", "choices"]
        read_only_fields = fields
