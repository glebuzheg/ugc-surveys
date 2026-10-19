from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.surveys.models import Choice, Participation, Question, Survey

from .base import SurveyTestCase


class SurveyReadTests(SurveyTestCase):
    def test_list_and_detail_include_ordered_questions_and_choices(self):
        for path in (
            reverse("survey-list"),
            reverse("survey-detail", kwargs={"pk": self.survey.pk}),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                survey = (
                    response.data["results"][0] if "results" in response.data else response.data
                )
                self.assertEqual(survey["id"], self.survey.pk)
                self.assertEqual(
                    [q["id"] for q in survey["questions"]], [self.first.pk, self.second.pk]
                )
                self.assertEqual(
                    [c["id"] for c in survey["questions"][0]["choices"]], [self.yes.pk, self.no.pk]
                )
        self.assertFalse(Participation.objects.exists())

    def test_hidden_survey_is_visible_only_to_author(self):
        self.survey.is_published = False
        self.survey.save(update_fields=["is_published"])
        detail_url = reverse("survey-detail", kwargs={"pk": self.survey.pk})
        self.assertEqual(self.client.get(reverse("survey-list")).data["results"], [])
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.client.force_authenticate(self.author)
        self.assertEqual(len(self.client.get(reverse("survey-list")).data["results"]), 1)
        self.assertEqual(self.client.get(detail_url).status_code, 200)

    def test_list_is_paginated(self):
        Survey.objects.bulk_create(
            [Survey(author=self.author, title=f"Survey {n}", is_published=True) for n in range(25)]
        )
        first_page = self.client.get(reverse("survey-list")).data
        self.assertEqual(len(first_page["results"]), 20)
        self.assertIsNotNone(first_page["next"])
        second_page = self.client.get(first_page["next"]).data
        self.assertEqual(len(second_page["results"]), 6)
        first_ids = {s["id"] for s in first_page["results"]}
        self.assertFalse(first_ids & {s["id"] for s in second_page["results"]})

    def test_nested_serialization_has_no_per_question_queries(self):
        for name, kwargs in (("survey-list", {}), ("survey-detail", {"pk": self.survey.pk})):
            path = reverse(name, kwargs=kwargs)
            with CaptureQueriesContext(connection) as initial:
                self.client.get(path)
            questions = Question.objects.bulk_create(
                [
                    Question(survey=self.survey, text=f"Extra {n}", position=n)
                    for n in range(
                        10 if name == "survey-list" else 20, 20 if name == "survey-list" else 30
                    )
                ]
            )
            Choice.objects.bulk_create(
                [Choice(question=q, text="Yes", position=1) for q in questions]
            )
            with CaptureQueriesContext(connection) as expanded:
                self.client.get(path)
            self.assertEqual(len(initial), len(expanded))
            self.assertEqual(len(expanded), 3)
