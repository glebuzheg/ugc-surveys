from django.urls import reverse

from apps.surveys.models import Survey
from apps.users.models import User

from .base import SurveyTestCase


class AdminTests(SurveyTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username="admin", password="local-test-password")
        self.client.force_login(self.admin)

    def test_can_create_user_with_hashed_password(self):
        response = self.client.post(
            reverse("admin:users_user_add"),
            {
                "username": "new-user",
                "usable_password": "true",
                "password1": "a-long-test-password-293",
                "password2": "a-long-test-password-293",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", None))
        user = User.objects.get(username="new-user")
        self.assertTrue(user.check_password("a-long-test-password-293"))

    def test_can_create_survey_with_questions(self):
        response = self.client.post(
            reverse("admin:surveys_survey_add"),
            {
                "author": self.author.pk,
                "title": "Опрос из админки",
                "is_published": "on",
                "questions-TOTAL_FORMS": "2",
                "questions-INITIAL_FORMS": "0",
                "questions-0-text": "Первый?",
                "questions-0-position": "",
                "questions-0-allow_custom_answer": "on",
                "questions-1-text": "Второй?",
                "questions-1-position": "",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", None))
        survey = Survey.objects.get(title="Опрос из админки")
        self.assertEqual(list(survey.questions.values_list("position", flat=True)), [1, 2])

    def test_can_swap_questions_after_publication(self):
        response = self.client.post(
            reverse("admin:surveys_survey_change", args=[self.survey.pk]),
            {
                "author": self.author.pk,
                "title": self.survey.title,
                "is_published": "on",
                "questions-TOTAL_FORMS": "2",
                "questions-INITIAL_FORMS": "2",
                "questions-0-id": self.first.pk,
                "questions-0-text": self.first.text,
                "questions-0-position": "9",
                "questions-0-allow_custom_answer": "on",
                "questions-1-id": self.second.pk,
                "questions-1-text": self.second.text,
                "questions-1-position": "2",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", None))
        self.first.refresh_from_db()
        self.assertEqual(self.first.position, 9)
        response = self.client.get(reverse("admin:surveys_survey_change", args=[self.survey.pk]))
        self.assertContains(response, "Опубликован")
        self.assertContains(response, "Посмотреть статистику")

    def test_can_swap_choices_and_append_in_one_form(self):
        response = self.client.post(
            reverse("admin:surveys_question_change", args=[self.first.pk]),
            {
                "text": self.first.text,
                "position": self.first.position,
                "allow_custom_answer": "on",
                "choices-TOTAL_FORMS": "3",
                "choices-INITIAL_FORMS": "2",
                "choices-0-id": self.yes.pk,
                "choices-0-text": "Да",
                "choices-0-position": "2",
                "choices-1-id": self.no.pk,
                "choices-1-text": "Нет",
                "choices-1-position": "1",
                "choices-2-text": "Иногда",
                "choices-2-position": "",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context_data", None))
        self.assertEqual(
            list(self.first.choices.values_list("text", "position")),
            [("Нет", 1), ("Да", 2), ("Иногда", 3)],
        )

    def test_duplicate_positions_are_a_form_error(self):
        response = self.client.post(
            reverse("admin:surveys_question_change", args=[self.first.pk]),
            {
                "text": self.first.text,
                "position": self.first.position,
                "choices-TOTAL_FORMS": "2",
                "choices-INITIAL_FORMS": "2",
                "choices-0-id": self.yes.pk,
                "choices-0-text": "Да",
                "choices-0-position": "1",
                "choices-1-id": self.no.pk,
                "choices-1-text": "Нет",
                "choices-1-position": "1",
            },
        )
        self.assertContains(response, "Позиции должны быть уникальными")
        self.assertEqual(list(self.first.choices.values_list("position", flat=True)), [1, 2])

    def test_admin_statistics_require_permission(self):
        url = reverse("admin:surveys_survey_statistics", args=[self.survey.pk])
        response = self.client.get(url)
        self.assertContains(response, "Среднее время")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_collected_answers_cannot_be_deleted_through_admin(self):
        self.answer(self.start(), choice=self.yes)
        response = self.client.post(
            reverse("admin:surveys_survey_delete", args=[self.survey.pk]), {"post": "yes"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Survey.objects.filter(pk=self.survey.pk).exists())
