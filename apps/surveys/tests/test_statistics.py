from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.surveys.models import Answer, Choice, Participation, Question

from .base import SurveyTestCase


class StatisticsTests(SurveyTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.author)

    def test_empty_statistics(self):
        response = self.client.get(self.url + "statistics/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["started_count"], 0)
        self.assertEqual(response.data["completion_rate"], 0)
        self.assertIsNone(response.data["average_completion_seconds"])
        self.assertEqual(response.data["questions"][0]["popular_choice_ids"], [])
        self.assertEqual(response.data["questions"][0]["choices"][0]["count"], 0)

    def test_aggregates_do_not_multiply_counts_and_include_incomplete_answers(self):
        now = timezone.now()
        for user, duration, choice in ((self.user, 10, self.yes), (self.other, 30, self.no)):
            p = Participation.objects.create(
                user=user,
                survey=self.survey,
                started_at=now,
                completed_at=now + timedelta(seconds=duration),
            )
            Answer.objects.create(participation=p, question=self.first, choice=choice)
            Answer.objects.create(participation=p, question=self.second, choice=self.second_yes)
        active = Participation.objects.create(user=self.author, survey=self.survey, started_at=now)
        Answer.objects.create(participation=active, question=self.first, custom_text="Only in soup")
        data = self.client.get(self.url + "statistics/").data
        self.assertEqual(data["started_count"], 3)
        self.assertEqual(data["completed_count"], 2)
        self.assertEqual(data["in_progress_count"], 1)
        self.assertEqual(data["answers_count"], 5)
        self.assertEqual(data["average_completion_seconds"], 20)
        self.assertAlmostEqual(data["completion_rate"], 2 / 3)
        first = data["questions"][0]
        self.assertEqual(first["custom_answers_count"], 1)
        self.assertEqual(first["popular_choice_ids"], [self.yes.pk, self.no.pk])
        self.assertAlmostEqual(first["choices"][0]["share"], 1 / 3)
        self.assertNotIn("Only in soup", str(data))

    def test_other_user_cannot_read_statistics(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.url + "statistics/").status_code, 404)

    def test_statistics_have_no_per_question_queries(self):
        with CaptureQueriesContext(connection) as initial:
            self.client.get(self.url + "statistics/")
        for n in range(10, 20):
            question = Question.objects.create(survey=self.survey, text=f"Extra {n}", position=n)
            Choice.objects.create(question=question, text="Yes", position=1)
        with CaptureQueriesContext(connection) as expanded:
            self.client.get(self.url + "statistics/")
        self.assertEqual(len(initial), len(expanded))
        self.assertLessEqual(len(expanded), 8)
