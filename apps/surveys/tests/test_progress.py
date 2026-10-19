from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.surveys.models import Participation, Question

from .base import SurveyTestCase


class ProgressTests(SurveyTestCase):
    def test_preview_does_not_create_participation(self):
        response = self.client.get(self.url + "next-question/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["state"], "not_started")
        self.assertIsNone(response.data["participation_id"])
        self.assertEqual(response.data["question"]["id"], self.first.pk)
        self.assertEqual(response.data["progress"], {"answered": 0, "total": 2})
        self.assertFalse(Participation.objects.exists())

    def test_resume_complete_and_repeat_start(self):
        pid = self.start()
        self.assertEqual(self.start(), pid)
        self.answer(pid, choice=self.yes)
        next_response = self.client.get(self.url + "next-question/")
        self.assertEqual(next_response.data["question"]["id"], self.second.pk)
        self.assertEqual(next_response.data["progress"]["answered"], 1)
        self.answer(pid, question=self.second, choice=self.second_yes)
        response = self.client.get(self.url + "next-question/")
        self.assertEqual(response.data["state"], "completed")
        self.assertIsNone(response.data["question"])
        self.assertEqual(self.start(), pid)
        self.assertIsNotNone(Participation.objects.get(pk=pid).completed_at)
        Question.objects.create(survey=self.survey, text="Later", position=15)
        self.assertEqual(self.client.get(self.url + "next-question/").data["state"], "completed")

    def test_users_have_independent_progress(self):
        self.answer(self.start(), choice=self.yes)
        self.client.force_authenticate(self.other)
        response = self.client.get(self.url + "next-question/")
        self.assertEqual(response.data["question"]["id"], self.first.pk)

    def test_hide_and_show_preserves_progress(self):
        self.answer(self.start(), choice=self.yes)
        self.survey.is_published = False
        self.survey.save(update_fields=["is_published"])
        self.assertEqual(self.client.get(self.url + "next-question/").status_code, 404)
        self.survey.is_published = True
        self.survey.save(update_fields=["is_published"])
        self.assertEqual(
            self.client.get(self.url + "next-question/").data["question"]["id"], self.second.pk
        )

    def test_next_question_query_budget_is_independent_of_survey_size(self):
        self.start()
        with CaptureQueriesContext(connection) as initial:
            self.client.get(self.url + "next-question/")
        Question.objects.bulk_create(
            [Question(survey=self.survey, text=f"Extra {n}", position=n) for n in range(10, 40)]
        )
        with CaptureQueriesContext(connection) as expanded:
            self.client.get(self.url + "next-question/")
        self.assertEqual(len(initial), len(expanded))
        self.assertLessEqual(len(expanded), 6)
