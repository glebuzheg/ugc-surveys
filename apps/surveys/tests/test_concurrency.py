from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

from django.db import connections
from rest_framework.test import APIClient

from apps.surveys.models import Answer, Choice, Participation

from .base import SurveyTestCase


class ConcurrencyTests(SurveyTestCase):
    def test_choice_deleted_between_validation_and_insert_is_a_conflict(self):
        pid = self.start()
        checked, deleted = Event(), Event()
        original_filter = Choice.objects.filter

        def filtered(*args, **kwargs):
            queryset = original_filter(*args, **kwargs)
            if kwargs.get("pk") == self.yes.pk and "question" in kwargs:
                original_exists = queryset.exists

                def exists():
                    result = original_exists()
                    checked.set()
                    if not deleted.wait(timeout=10):
                        raise TimeoutError("Concurrent delete did not finish")
                    return result

                queryset.exists = exists
            return queryset

        def delete_choice():
            try:
                if not checked.wait(timeout=10):
                    raise TimeoutError("Answer did not validate choice")
                client = APIClient()
                client.force_authenticate(self.author)
                return client.delete(
                    self.url + f"questions/{self.first.pk}/choices/{self.yes.pk}/",
                ).status_code
            finally:
                deleted.set()
                connections.close_all()

        with (
            patch.object(Choice.objects, "filter", side_effect=filtered),
            ThreadPoolExecutor(max_workers=1) as executor,
        ):
            deletion = executor.submit(delete_choice)
            response = self.answer(pid, choice=self.yes)
            self.assertEqual(deletion.result(timeout=15), 204)
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data["code"], "structure_changed")
        self.assertFalse(Answer.objects.exists())

    def concurrent_post(self, path, payloads, user=None):
        barrier = Barrier(len(payloads))

        def request(payload):
            try:
                client = APIClient()
                client.force_authenticate(user or self.user)
                barrier.wait(timeout=10)
                response = client.post(path, payload, format="json")
                return response.status_code, response.data
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(payloads)) as executor:
            futures = [executor.submit(request, payload) for payload in payloads]
            return [future.result(timeout=20) for future in futures]

    def test_concurrent_starts_have_one_participation(self):
        responses = self.concurrent_post(self.url + "start/", [{}, {}])
        self.assertEqual(sorted(code for code, _ in responses), [200, 201])
        self.assertEqual(Participation.objects.count(), 1)

    def test_concurrent_identical_answers_create_one_row(self):
        pid = self.start()
        payload = {"question": self.first.pk, "choice": self.yes.pk}
        responses = self.concurrent_post(
            f"/api/v1/participations/{pid}/answers/", [payload, payload]
        )
        self.assertEqual(sorted(code for code, _ in responses), [200, 201])
        self.assertEqual(Answer.objects.count(), 1)

    def test_concurrent_conflicting_answers_are_not_overwritten(self):
        pid = self.start()
        responses = self.concurrent_post(
            f"/api/v1/participations/{pid}/answers/",
            [
                {"question": self.first.pk, "choice": self.yes.pk},
                {"question": self.first.pk, "choice": self.no.pk},
            ],
        )
        self.assertEqual(sorted(code for code, _ in responses), [201, 409])
        self.assertEqual(Answer.objects.count(), 1)

    def test_concurrent_last_answer_sets_one_completion_timestamp(self):
        pid = self.start()
        self.answer(pid, choice=self.yes)
        payload = {"question": self.second.pk, "choice": self.second_yes.pk}
        responses = self.concurrent_post(
            f"/api/v1/participations/{pid}/answers/", [payload, payload]
        )
        self.assertEqual(sorted(code for code, _ in responses), [200, 201])
        self.assertEqual(Answer.objects.count(), 2)
        self.assertIsNotNone(Participation.objects.get(pk=pid).completed_at)

    def test_concurrent_question_appends_have_distinct_positions(self):
        responses = self.concurrent_post(
            self.url + "questions/",
            [
                {"text": "One"},
                {"text": "Two"},
            ],
            user=self.author,
        )
        self.assertEqual([code for code, _ in responses], [201, 201])
        self.assertEqual(
            list(self.survey.questions.values_list("position", flat=True)), [2, 9, 10, 11]
        )

    def test_concurrent_reorders_leave_a_complete_permutation(self):
        responses = self.concurrent_post(
            self.url + "reorder-questions/",
            [
                {"ids": [self.first.pk, self.second.pk]},
                {"ids": [self.second.pk, self.first.pk]},
            ],
            user=self.author,
        )
        self.assertEqual([code for code, _ in responses], [200, 200])
        self.assertEqual(list(self.survey.questions.values_list("position", flat=True)), [1, 2])
