from rest_framework import serializers

from apps.surveys.models import Answer


class AnswerSerializer(serializers.ModelSerializer):
    # Resolve IDs in the locked write path, rather than validating global FK querysets.
    question = serializers.IntegerField(min_value=1)
    choice = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    class Meta:
        model = Answer
        fields = ["id", "question", "choice", "custom_text", "created_at"]
        read_only_fields = ["id", "created_at"]
        validators = []  # Identical retries must reach the idempotent write path.

    def validate(self, attrs):
        text = attrs.get("custom_text", "")
        if (attrs.get("choice") is not None) == bool(text):
            raise serializers.ValidationError("Provide either choice or non-empty custom_text.")
        return attrs
