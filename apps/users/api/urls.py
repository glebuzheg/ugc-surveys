from django.urls import path

from .views.user import CurrentUserView

urlpatterns = [path("users/me/", CurrentUserView.as_view(), name="current-user")]
