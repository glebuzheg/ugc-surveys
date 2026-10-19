from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

from django.db import connections
from django.urls import reverse
from rest_framework.test import APIClient

from apps.surveys.models import Answer, Choice, Participation, Question

from .base import SurveyTestCase


class ConcurrencyTests(SurveyTestCase):
    def test_choice_deleted_between_validation_and_insert_is_a_bad_request(self):
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
                Choice.objects.get(pk=self.yes.pk).delete()
                return 204
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
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Answer.objects.exists())

    def concurrent_request(self, path, payloads, method="post"):
        barrier = Barrier(len(payloads))

        def request(payload):
            try:
                client = APIClient()
                client.force_authenticate(self.user)
                barrier.wait(timeout=10)
                response = (
                    client.get(path)
                    if method == "get"
                    else client.post(path, payload, format="json")
                )
                return response.status_code, response.data
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(payloads)) as executor:
            futures = [executor.submit(request, payload) for payload in payloads]
            return [future.result(timeout=20) for future in futures]

    def test_concurrent_starts_have_one_participation(self):
        responses = self.concurrent_request(self.url, [{}, {}], method="get")
        self.assertEqual(sorted(code for code, _ in responses), [200, 200])
        self.assertEqual(Participation.objects.count(), 1)

    def test_concurrent_identical_answers_create_one_row(self):
        pid = self.start()
        payload = {"question": self.first.pk, "choice": self.yes.pk}
        responses = self.concurrent_request(
            reverse("submit-answer", kwargs={"participation_pk": pid}), [payload, payload]
        )
        self.assertEqual(sorted(code for code, _ in responses), [200, 201])
        self.assertEqual(Answer.objects.count(), 1)

    def test_concurrent_conflicting_answers_are_not_overwritten(self):
        pid = self.start()
        responses = self.concurrent_request(
            reverse("submit-answer", kwargs={"participation_pk": pid}),
            [
                {"question": self.first.pk, "choice": self.yes.pk},
                {"question": self.first.pk, "choice": self.no.pk},
            ],
        )
        self.assertEqual(sorted(code for code, _ in responses), [201, 400])
        self.assertEqual(Answer.objects.count(), 1)

    def test_concurrent_last_answer_sets_one_completion_timestamp(self):
        pid = self.start()
        self.answer(pid, choice=self.yes)
        payload = {"question": self.second.pk, "choice": self.second_yes.pk}
        responses = self.concurrent_request(
            reverse("submit-answer", kwargs={"participation_pk": pid}), [payload, payload]
        )
        self.assertEqual(sorted(code for code, _ in responses), [200, 201])
        self.assertEqual(Answer.objects.count(), 2)
        self.assertIsNotNone(Participation.objects.get(pk=pid).completed_at)

    def test_concurrent_question_appends_have_distinct_positions(self):
        barrier = Barrier(2)

        def append(text):
            try:
                barrier.wait(timeout=10)
                return Question.objects.create(survey=self.survey, text=text).position
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(append, ["One", "Two"]))
        self.assertEqual(sorted(results), [10, 11])
