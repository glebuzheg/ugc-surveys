from rest_framework.test import APITransactionTestCase

from apps.surveys.models import Choice, Question, Survey
from apps.users.models import User


class SurveyTestCase(APITransactionTestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author")
        self.user = User.objects.create_user(username="respondent")
        self.other = User.objects.create_user(username="other")
        self.survey = Survey.objects.create(
            author=self.author, title="Vegetables", is_published=True
        )
        self.first = Question.objects.create(
            survey=self.survey,
            text="Tomatoes?",
            position=2,
            allow_custom_answer=True,
        )
        self.second = Question.objects.create(survey=self.survey, text="Cucumbers?", position=9)
        self.yes = Choice.objects.create(question=self.first, text="Yes", position=1)
        self.no = Choice.objects.create(question=self.first, text="No", position=2)
        self.second_yes = Choice.objects.create(question=self.second, text="Yes", position=1)
        self.url = f"/api/v1/surveys/{self.survey.pk}/"
        self.client.force_authenticate(self.user)

    def start(self):
        response = self.client.get(self.url + "next-question/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["participation_id"]

    def answer(self, participation_id, question=None, choice=None, **kwargs):
        data = {"question": (question or self.first).pk, **kwargs}
        if choice is not None:
            data["choice"] = choice.pk
        return self.client.post(
            f"/api/v1/participations/{participation_id}/answers/",
            data,
            format="json",
        )
