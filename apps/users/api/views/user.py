from rest_framework.generics import RetrieveAPIView

from apps.users.api.serializers.user import UserSerializer


class CurrentUserView(RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
