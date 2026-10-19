from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409

    def __init__(self, code, detail):
        super().__init__({"code": code, "detail": detail})
