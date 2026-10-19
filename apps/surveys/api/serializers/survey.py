from rest_framework import serializers

from apps.surveys.models import Survey


class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["id", "author", "title", "is_published", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class ReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=True)

    def validate_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("IDs must be unique.")
        return value
