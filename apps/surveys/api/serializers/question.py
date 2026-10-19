from rest_framework import serializers

from apps.surveys.models import Question

from .choice import ChoiceSerializer


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "survey", "text", "position", "allow_custom_answer"]
        read_only_fields = ["id", "survey", "position"]


class NextQuestionSerializer(QuestionSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta(QuestionSerializer.Meta):
        fields = [*QuestionSerializer.Meta.fields, "choices"]
