from rest_framework import serializers

from apps.surveys.models import Participation


class ParticipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participation
        fields = ["id", "survey", "user", "started_at", "completed_at"]
        read_only_fields = fields
