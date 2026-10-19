from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.surveys.models import Survey


@transaction.atomic
def reorder(survey_id, user, children, ids):
    get_object_or_404(Survey.objects.select_for_update(), pk=survey_id, author=user)
    objects = {obj.pk: obj for obj in children}
    if set(ids) != objects.keys():
        raise ValidationError({"ids": "Provide all IDs belonging to this parent exactly once."})
    ordered = []
    for position, pk in enumerate(ids, start=1):
        obj = objects[pk]
        obj.position = position
        ordered.append(obj)
    children.model.objects.bulk_update(ordered, ["position"])
