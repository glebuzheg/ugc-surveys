from django.urls import path

from .views.answer import AnswerViewSet
from .views.survey import NextQuestionView

urlpatterns = [
    path("surveys/<int:pk>/next-question/", NextQuestionView.as_view(), name="next-question"),
    path(
        "participations/<int:participation_pk>/answers/",
        AnswerViewSet.as_view({"post": "create"}),
        name="submit-answer",
    ),
]
