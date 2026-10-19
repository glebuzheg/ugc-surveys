from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.surveys.models import Answer, Participation, Question, Survey

from .base import SurveyTestCase


class SurveyTests(SurveyTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.author)

    def test_visibility_is_a_patchable_boolean_and_does_not_block_edits(self):
        self.assertEqual(self.client.patch(self.url, {"is_published": False}).status_code, 200)
        questions = self.url + "questions/"
        self.assertEqual(self.client.post(questions, {"text": "More?"}).status_code, 201)
        self.assertEqual(self.client.patch(self.url, {"is_published": True}).status_code, 200)
        self.assertEqual(
            self.client.patch(
                questions + f"{self.first.pk}/",
                {"text": "Changed after publication"},
            ).status_code,
            200,
        )
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.patch(self.url, {"title": "Intrusion"}).status_code, 404)
        self.assertEqual(self.client.get(questions).status_code, 404)

    def test_hidden_survey_and_statistics_are_not_public(self):
        self.client.patch(self.url, {"is_published": False})
        self.client.force_authenticate(self.user)
        for suffix in ("", "start/", "next-question/", "statistics/", "questions/"):
            with self.subTest(suffix=suffix):
                self.assertEqual(
                    self.client.get(self.url + suffix).status_code
                    if suffix != "start/"
                    else self.client.post(self.url + suffix).status_code,
                    404,
                )
        self.assertEqual(self.client.get("/api/v1/surveys/").data["results"], [])
        self.client.force_authenticate(self.author)
        self.assertEqual(len(self.client.get("/api/v1/surveys/?mine=1").data["results"]), 1)

    def test_cannot_assign_another_author_or_parent_or_position(self):
        response = self.client.post("/api/v1/surveys/", {"title": "Own", "author": self.user.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["author"], self.author.pk)
        response = self.client.post(
            self.url + "questions/",
            {
                "text": "Appended",
                "survey": response.data["id"],
                "position": 1,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["survey"], self.survey.pk)
        self.assertEqual(response.data["position"], 10)

    def test_reordering_after_answer_preserves_progress_and_choice(self):
        self.client.force_authenticate(self.user)
        pid = self.start()
        self.assertEqual(self.answer(pid, choice=self.yes).status_code, 201)
        self.client.force_authenticate(self.author)
        response = self.client.post(
            self.url + "reorder-questions/",
            {
                "ids": [self.second.pk, self.first.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(
            self.url + f"questions/{self.first.pk}/reorder-choices/",
            {"ids": [self.no.pk, self.yes.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.get(self.url + "next-question/").data["question"]["id"], self.second.pk
        )
        self.assertEqual(Answer.objects.get(participation_id=pid).choice_id, self.yes.pk)

    def test_bad_reorder_is_atomic(self):
        for ids in ([self.first.pk], [self.first.pk, self.first.pk], [self.first.pk, 999999]):
            with self.subTest(ids=ids):
                response = self.client.post(
                    self.url + "reorder-questions/", {"ids": ids}, format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    list(self.survey.questions.values_list("position", flat=True)), [2, 9]
                )

    def test_nested_choices_cannot_cross_parents(self):
        path = self.url + f"questions/{self.second.pk}/choices/{self.yes.pk}/"
        self.assertEqual(self.client.patch(path, {"text": "Wrong parent"}).status_code, 404)
        response = self.client.post(
            self.url + f"questions/{self.second.pk}/choices/", {"text": "No"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["position"], 2)

    def test_deletion_preserves_collected_data(self):
        self.client.force_authenticate(self.user)
        pid = self.start()
        self.answer(pid, choice=self.yes)
        self.client.force_authenticate(self.author)
        for path in (
            self.url,
            self.url + f"questions/{self.first.pk}/",
            self.url + f"questions/{self.first.pk}/choices/{self.yes.pk}/",
        ):
            self.assertEqual(self.client.delete(path).status_code, 409)
        self.assertEqual(Answer.objects.count(), 1)

    def test_empty_survey_cannot_start(self):
        survey = Survey.objects.create(author=self.author, title="Empty", is_published=True)
        self.assertEqual(self.client.post(f"/api/v1/surveys/{survey.pk}/start/").status_code, 409)

    def test_authentication_uses_real_tokens(self):
        self.client = APIClient()
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 401)
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user.pk)

    def test_blank_text_is_rejected(self):
        self.assertEqual(self.client.patch(self.url, {"title": "   "}).status_code, 400)
        self.assertEqual(self.client.post(self.url + "questions/", {"text": "  "}).status_code, 400)

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
