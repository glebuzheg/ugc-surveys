from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.answer import AnswerViewSet
from .views.choice import ChoiceViewSet
from .views.question import QuestionViewSet
from .views.survey import SurveyViewSet

router = DefaultRouter()
router.register("surveys", SurveyViewSet, basename="survey")
question_list = QuestionViewSet.as_view({"get": "list", "post": "create"})
question_detail = QuestionViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
choice_list = ChoiceViewSet.as_view({"get": "list", "post": "create"})
choice_detail = ChoiceViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
urlpatterns = [
    path("", include(router.urls)),
    path("surveys/<int:survey_pk>/questions/", question_list),
    path("surveys/<int:survey_pk>/questions/<int:pk>/", question_detail),
    path("surveys/<int:survey_pk>/questions/<int:question_pk>/choices/", choice_list),
    path("surveys/<int:survey_pk>/questions/<int:question_pk>/choices/<int:pk>/", choice_detail),
    path(
        "surveys/<int:survey_pk>/questions/<int:question_pk>/reorder-choices/",
        ChoiceViewSet.as_view({"post": "reorder_choices"}),
    ),
    path(
        "participations/<int:participation_pk>/answers/", AnswerViewSet.as_view({"post": "create"})
    ),
]
