from bson import ObjectId
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from pymongo.errors import DuplicateKeyError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_serializers import (
    AccessTokenResponseSerializer, CsrfResponseSerializer, ErrorSerializer,
    MessageSerializer, RefreshResponseSerializer, RegistrationResponseSerializer, UserProfileSerializer,
)
from .email_service import EmailDeliveryError
from .mongo import get_auth_database, safe_user
from .permissions import IsAuthenticatedUser
from .serializers import (
    ChangePasswordSerializer, EmailCodeSerializer, EmailSerializer, LoginSerializer,
    ProfileSerializer, RegistrationSerializer,
)
from .services import (
    AccountConflict, AuthenticationFailure, RefreshFailure, VerificationFailure,
    change_password, login, register_user, resend_verification, revoke_refresh_token,
    rotate_refresh_token, update_profile, verify_email,
)
from .throttles import MongoRateThrottle


def _error(code, detail, status_code):
    return Response({"code": code, "detail": detail}, status=status_code)


def _set_refresh_cookie(response, token):
    response.set_cookie(
        "cinesplit_refresh", token,
        max_age=settings.JWT_REFRESH_TOKEN_LIFETIME * 24 * 60 * 60,
        httponly=True, secure=not settings.DEBUG, samesite="Lax", path="/api/auth/",
    )
    return response


def _clear_refresh_cookie(response):
    response.delete_cookie("cinesplit_refresh", path="/api/auth/", samesite="Lax")
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="auth_csrf", summary="Initialize the CSRF cookie", responses={200: CsrfResponseSerializer})
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MongoRateThrottle]
    throttle_scope = "auth_register"

    @extend_schema(
        operation_id="auth_register", summary="Register an account",
        request=RegistrationSerializer,
        responses={201: RegistrationResponseSerializer, 400: ErrorSerializer, 409: ErrorSerializer, 429: ErrorSerializer, 503: ErrorSerializer},
        description="Creates a user with the fixed user role and sends a six-digit email verification code. No token is issued until verification.",
    )
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "validation_error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user, delivered = register_user(
                serializer.validated_data["username"], serializer.validated_data["email"],
                serializer.validated_data["password"],
            )
        except AccountConflict as exc:
            return _error("account_conflict", str(exc), status.HTTP_409_CONFLICT)
        except DuplicateKeyError:
            return _error("account_conflict", "An account already uses that username or email.", status.HTTP_409_CONFLICT)
        except ImproperlyConfigured:
            return _error("service_misconfigured", "The service is temporarily unavailable.", status.HTTP_503_SERVICE_UNAVAILABLE)
        if not delivered:
            return _error("email_delivery_failed", "Your account was created, but the verification email could not be delivered. Please use resend verification after the cooldown.", status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": "Account created. Verify your email to continue.", "email": serializer.validated_data["email"], "verification_required": True}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MongoRateThrottle]
    throttle_scope = "auth_verify"

    @extend_schema(
        operation_id="auth_verify_email", summary="Verify an email address", request=EmailCodeSerializer,
        responses={200: MessageSerializer, 400: ErrorSerializer, 429: ErrorSerializer, 503: ErrorSerializer},
        description="Consumes a single-use six-digit code. Codes expire after the configured interval (10 minutes by default) and allow at most five incorrect attempts.",
    )
    def post(self, request):
        serializer = EmailCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "validation_error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            verify_email(serializer.validated_data["email"], serializer.validated_data["code"])
        except VerificationFailure as exc:
            return _error(exc.code, str(exc), status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Email verified. You can now sign in."})


@method_decorator(csrf_protect, name="dispatch")
class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MongoRateThrottle]
    throttle_scope = "auth_resend"

    @extend_schema(
        operation_id="auth_resend_verification", summary="Resend an email verification code", request=EmailSerializer,
        responses={202: MessageSerializer, 400: ErrorSerializer, 429: ErrorSerializer, 503: ErrorSerializer},
        description="A code can be resent once per cooldown period (60 seconds by default). The prior active code is invalidated.",
    )
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "validation_error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            outcome = resend_verification(serializer.validated_data["email"])
        except EmailDeliveryError:
            return _error("email_delivery_failed", "The verification email could not be delivered. Please try again later.", status.HTTP_503_SERVICE_UNAVAILABLE)
        if outcome == "delivery_failed":
            return _error("email_delivery_failed", "The verification email could not be delivered. Please try again later.", status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": "If this address is eligible, a verification email has been sent."}, status=status.HTTP_202_ACCEPTED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MongoRateThrottle]
    throttle_scope = "auth_login"

    @extend_schema(
        operation_id="auth_login", summary="Sign in", request=LoginSerializer,
        responses={200: AccessTokenResponseSerializer, 400: ErrorSerializer, 401: ErrorSerializer, 403: ErrorSerializer, 429: ErrorSerializer, 503: ErrorSerializer},
        description="Verified active accounts receive a short-lived access token and an HttpOnly refresh cookie. Unverified users cannot sign in.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "validation_error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            access_token, refresh_token, user = login(serializer.validated_data["email"], serializer.validated_data["password"])
        except AuthenticationFailure as exc:
            response_status = status.HTTP_403_FORBIDDEN if exc.code == "email_not_verified" else status.HTTP_401_UNAUTHORIZED
            return _error(exc.code, str(exc), response_status)
        response = Response({"access_token": access_token, "token_type": "Bearer", "user": safe_user(user)})
        return _set_refresh_cookie(response, refresh_token)


@method_decorator(csrf_protect, name="dispatch")
class RefreshView(APIView):
    serializer_class = RefreshResponseSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MongoRateThrottle]
    throttle_scope = "auth_refresh"

    @extend_schema(
        operation_id="auth_refresh", summary="Rotate the refresh session",
        responses={200: RefreshResponseSerializer, 401: ErrorSerializer, 429: ErrorSerializer, 503: ErrorSerializer},
        description="Reads the refresh token from an HttpOnly cookie, validates and rotates it, and returns its replacement as a cookie. Reuse of a rotated token revokes its token family. Access tokens remain valid until their short expiry.",
    )
    def post(self, request):
        token = request.COOKIES.get("cinesplit_refresh", "")
        try:
            access_token, refresh_token = rotate_refresh_token(token)
        except RefreshFailure as exc:
            response = _error(exc.code, str(exc), status.HTTP_401_UNAUTHORIZED)
            return _clear_refresh_cookie(response)
        response = Response({"access_token": access_token, "token_type": "Bearer"})
        return _set_refresh_cookie(response, refresh_token)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    serializer_class = MessageSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        operation_id="auth_logout", summary="Revoke the refresh session",
        responses={200: MessageSerializer, 503: ErrorSerializer},
        description="Revokes the current refresh session and clears its HttpOnly cookie. Existing access tokens may remain valid until expiry.",
    )
    def post(self, request):
        token = request.COOKIES.get("cinesplit_refresh", "")
        if token:
            revoke_refresh_token(token)
        return _clear_refresh_cookie(Response({"detail": "Signed out."}))


class MeView(APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(operation_id="auth_me", summary="Get the current profile", responses={200: UserProfileSerializer, 401: ErrorSerializer})
    def get(self, request):
        user = get_auth_database().users.find_one({"_id": ObjectId(request.user.id)})
        if not user:
            return _error("user_unavailable", "The account is unavailable.", status.HTTP_401_UNAUTHORIZED)
        return Response(safe_user(user))

    @method_decorator(csrf_protect)
    @extend_schema(
        operation_id="auth_update_me", summary="Update permitted profile fields", request=ProfileSerializer,
        responses={200: UserProfileSerializer, 400: ErrorSerializer, 401: ErrorSerializer, 409: ErrorSerializer},
        description="Only username, full name, avatar URL, and bio can be changed. Role, account state, verification, and identifiers are immutable here.",
    )
    def patch(self, request):
        allowed = {"username", "full_name", "avatar", "bio"}
        forbidden = set(request.data) - allowed
        if forbidden:
            return _error("field_not_allowed", "Only username, full name, avatar, and bio can be updated.", status.HTTP_400_BAD_REQUEST)
        serializer = ProfileSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"code": "validation_error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = update_profile(request.user.id, serializer.validated_data)
        except AccountConflict as exc:
            return _error("account_conflict", str(exc), status.HTTP_409_CONFLICT)
        except DuplicateKeyError:
            return _error("account_conflict", "That username is already taken.", status.HTTP_409_CONFLICT)
        return Response(safe_user(user))


@method_decorator(csrf_protect, name="dispatch")
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        operation_id="auth_change_password", summary="Change password", request=ChangePasswordSerializer,
        responses={200: MessageSerializer, 400: ErrorSerializer, 401: ErrorSerializer},
        description="Verifies the current password and revokes all active refresh sessions after changing it. Current access tokens expire normally.",
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "validation_error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        try:
            change_password(request.user.id, data["current_password"], data["new_password"])
        except AuthenticationFailure as exc:
            return _error(exc.code, str(exc), status.HTTP_400_BAD_REQUEST)
        return _clear_refresh_cookie(Response({"detail": "Password changed. Sign in again on your other devices."}))

