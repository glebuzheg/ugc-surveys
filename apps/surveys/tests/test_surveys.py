from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.surveys.models import Answer, Choice, Participation, Question

from .base import SurveyTestCase


class SurveyTests(SurveyTestCase):
    def test_survey_endpoints_are_read_only(self):
        for path in (
            reverse("survey-list"),
            reverse("survey-detail", kwargs={"pk": self.survey.pk}),
            self.url,
        ):
            for method in (self.client.post, self.client.patch, self.client.delete):
                with self.subTest(path=path, method=method):
                    self.assertEqual(method(path, {}, format="json").status_code, 405)

    def test_authentication_uses_real_tokens(self):
        self.client = APIClient()
        self.assertEqual(self.client.get(self.url).status_code, 401)
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_empty_survey_cannot_start(self):
        self.survey.questions.all().delete()
        self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_positions_are_assigned_in_models(self):
        question = Question.objects.create(survey=self.survey, text="New")
        self.assertEqual(question.position, 10)
        choice = Choice.objects.create(question=self.first, text="Other")
        self.assertEqual(choice.position, 3)

    def test_deletion_protects_collected_data(self):
        self.answer(self.start(), choice=self.yes)
        for instance in (self.survey, self.first, self.yes):
            with self.subTest(instance=instance), self.assertRaises(ProtectedError):
                instance.delete()
        self.assertEqual(Answer.objects.count(), 1)

    def test_database_constraints(self):
        p = Participation.objects.create(user=self.user, survey=self.survey)
        for operation in (
            lambda: Participation.objects.create(user=self.user, survey=self.survey),
            lambda: Question.objects.create(survey=self.survey, text="Duplicate", position=2),
            lambda: Question.objects.create(survey=self.survey, text="Zero", position=0),
            lambda: Answer.objects.create(participation=p, question=self.first),
            lambda: Answer.objects.create(
                participation=p, question=self.first, choice=self.yes, custom_text="both"
            ),
        ):
            with (
                self.subTest(operation=operation),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                operation()
