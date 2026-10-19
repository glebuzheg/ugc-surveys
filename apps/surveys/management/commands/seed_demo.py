from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

from apps.surveys.models import Choice, Question, Survey
from apps.users.models import User


class Command(BaseCommand):
    help = "Create an author, a respondent, API tokens and the Vegetables survey. Safe to repeat."

    @transaction.atomic
    def handle(self, *args, **options):
        users = []
        for username in ("demo_author", "demo_respondent"):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            token, _ = Token.objects.get_or_create(user=user)
            users.append(user)
            self.stdout.write(f"{username}: {token.key}")
        survey, created = Survey.objects.get_or_create(
            author=users[0],
            title="Овощи",
            defaults={"is_published": True},
        )
        if created:
            for position, (text, choices) in enumerate(
                [
                    ("Ты любишь буратту с помидорами?", ["Да", "Нет", "Непереносимость лактозы"]),
                    ("Ты любишь огурцы?", ["Да", "Нет", "Только в коктейлях"]),
                ],
                start=1,
            ):
                question = Question.objects.create(
                    survey=survey,
                    text=text,
                    position=position,
                    allow_custom_answer=True,
                )
                Choice.objects.bulk_create(
                    [
                        Choice(question=question, text=value, position=index)
                        for index, value in enumerate(choices, start=1)
                    ]
                )
        self.stdout.write(f"survey_id: {survey.pk}")
