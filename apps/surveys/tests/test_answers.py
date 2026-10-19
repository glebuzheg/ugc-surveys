from apps.surveys.models import Answer, Participation

from .base import SurveyTestCase


class AnswerTests(SurveyTestCase):
    def test_custom_answer_is_trimmed_and_retry_is_idempotent(self):
        pid = self.start()
        first = self.answer(pid, custom_text="  With pesto  ")
        second = self.answer(pid, custom_text="With pesto")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Answer.objects.count(), 1)

    def test_cannot_change_an_accepted_answer(self):
        pid = self.start()
        self.answer(pid, choice=self.yes)
        self.assertEqual(self.answer(pid, choice=self.no).status_code, 400)

    def test_validation_at_answer_boundary(self):
        pid = self.start()
        for kwargs in (
            {},
            {"custom_text": "   "},
            {"custom_text": "x" * 2001},
            {"choice": self.yes, "custom_text": "both"},
            {"choice": self.second_yes},
        ):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.answer(pid, **kwargs).status_code, 400)
        self.assertEqual(
            self.answer(pid, question=self.second, choice=self.second_yes).status_code, 400
        )
        self.assertFalse(Answer.objects.exists())

    def test_custom_answer_requires_question_permission(self):
        pid = self.start()
        self.answer(pid, choice=self.yes)
        self.assertEqual(self.answer(pid, question=self.second, custom_text="No").status_code, 400)

    def test_foreign_participation_is_inaccessible(self):
        pid = self.start()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.answer(pid, choice=self.yes).status_code, 404)

    def test_last_answer_retry_preserves_completion_time(self):
        pid = self.start()
        self.answer(pid, choice=self.yes)
        response = self.answer(pid, question=self.second, choice=self.second_yes)
        self.assertEqual(response.status_code, 201)
        completed_at = Participation.objects.get(pk=pid).completed_at
        self.assertEqual(
            self.answer(pid, question=self.second, choice=self.second_yes).status_code, 200
        )
        self.assertEqual(Participation.objects.get(pk=pid).completed_at, completed_at)
