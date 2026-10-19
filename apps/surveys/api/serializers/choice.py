from rest_framework import serializers

from apps.surveys.models import Choice


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "question", "text", "position"]
        read_only_fields = fields
