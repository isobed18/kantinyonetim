from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from apps.users.utils import log_user_action
from apps.users.models import User


class UsernameOrEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Allow login using either username or email in the 'username' field
        login_identifier = attrs.get(self.username_field)
        password = attrs.get('password')

        if login_identifier and '@' in login_identifier:
            # Treat provided identifier as email, map to username for authentication
            UserModel = get_user_model()
            try:
                user = UserModel.objects.get(email__iexact=login_identifier)
                attrs[self.username_field] = getattr(user, self.username_field)
            except UserModel.DoesNotExist:
                # Fall through to default behavior, which will raise the same generic error
                pass

        attrs['password'] = password
        return super().validate(attrs)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = UsernameOrEmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            # Log successful login
            username = request.data.get(self.serializer_class.username_field)
            try:
                user = User.objects.get(**{self.serializer_class.username_field: username}) # Get the actual user object
            except User.DoesNotExist:
                user = None # Should not happen on successful login, but handle defensively
            
            if user:
                log_user_action(
                    user=user,
                    action='login',
                    resource_type='user',
                    resource_id=user.id,
                    details={'status': 'success'},
                    request=request
                )
        else:
            # Log failed login attempt
            username = request.data.get('username', 'unknown')
            # Attempt to get the user even if login failed, if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = None
            
            if user:
                log_user_action(
                    user=user,
                    action='login',
                    resource_type='user',
                    resource_id=user.id,
                    details={'status': 'failed', 'reason': response.data.get('detail', 'invalid credentials')},
                    request=request
                )
        return response


