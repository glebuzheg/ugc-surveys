from rest_framework.pagination import CursorPagination


class SurveyPagination(CursorPagination):
    ordering = "-id"
    page_size = 20
