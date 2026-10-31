import logging
import smtplib
from datetime import timedelta
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import Client, SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from . import email_service, security, services, tokens
from .mongo import ensure_indexes
from .serializers import EmailCodeSerializer, RegistrationSerializer
from .throttles import MongoRateThrottle
from .views import LoginView, RefreshView, RegisterView


class SecurityPrimitiveTests(SimpleTestCase):
    def test_code_is_exactly_six_digits_and_preserves_leading_zeroes(self):
        with patch("accounts.security.secrets.randbelow", return_value=7):
            self.assertEqual(security.generate_email_code(), "000007")

    def test_passwords_and_email_codes_are_stored_as_bcrypt_hashes(self):
        password_hash = security.hash_password("StrongPassword!27")
        code_hash = security.hash_email_code("004207")
        self.assertNotEqual(password_hash, "StrongPassword!27")
        self.assertNotEqual(code_hash, "004207")
        self.assertTrue(security.verify_password("StrongPassword!27", password_hash))
        self.assertTrue(security.verify_email_code("004207", code_hash))
        self.assertFalse(security.verify_email_code("104207", code_hash))

    def test_serializers_normalize_user_identifiers_and_reject_weak_input(self):
        valid = RegistrationSerializer(data={
            "username": "  Cine.User ", "email": "  Cine@Example.COM ",
            "password": "StrongPassword!27", "password_confirmation": "StrongPassword!27",
        })
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertEqual(valid.validated_data["username"], "cine.user")
        self.assertEqual(valid.validated_data["email"], "cine@example.com")
        with_role = RegistrationSerializer(data={
            "username": "cineuser", "email": "cine@example.com", "password": "StrongPassword!27",
            "password_confirmation": "StrongPassword!27", "role": "admin",
        })
        self.assertFalse(with_role.is_valid())
        invalid = RegistrationSerializer(data={
            "username": "cine", "email": "not-an-email", "password": "weak",
            "password_confirmation": "different",
        })
        self.assertFalse(invalid.is_valid())

    def test_email_code_serializer_preserves_leading_zeroes(self):
        serializer = EmailCodeSerializer(data={"email": "cine@example.com", "code": "000042"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["code"], "000042")


class RegistrationServiceTests(SimpleTestCase):
    @override_settings(EMAIL_VERIFICATION_EXPIRY_MINUTES=10)
    @patch("accounts.services.send_verification_email")
    @patch("accounts.services.generate_email_code", return_value="004201")
    @patch("accounts.services.get_auth_database")
    def test_registration_stores_only_hashes_and_assigns_user_role(self, get_db, _code, send_email):
        db = MagicMock()
        user_id = ObjectId()
        db.users.insert_one.return_value.inserted_id = user_id
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        db.client.start_session.return_value.__enter__.return_value = session
        get_db.return_value = db

        user, delivered = services.register_user("cineuser", "cine@example.com", "StrongPassword!27")

        self.assertTrue(delivered)
        self.assertEqual(user["role"], "user")
        self.assertFalse(user["is_verified"])
        self.assertTrue(security.verify_password("StrongPassword!27", user["password_hash"]))
        saved_verification = db.email_verifications.insert_one.call_args.args[0]
        self.assertNotEqual(saved_verification["code_hash"], "004201")
        self.assertTrue(security.verify_email_code("004201", saved_verification["code_hash"]))
        self.assertEqual(saved_verification["expires_at"] - saved_verification["created_at"], timedelta(minutes=10))
        send_email.assert_called_once_with("cine@example.com", "004201")

    @patch("accounts.services.send_verification_email", side_effect=email_service.EmailDeliveryError)
    @patch("accounts.services.generate_email_code", return_value="004201")
    @patch("accounts.services.get_auth_database")
    def test_smtp_failure_keeps_account_resendable_and_reports_failure(self, get_db, _code, _send):
        db = MagicMock()
        db.users.insert_one.return_value.inserted_id = ObjectId()
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        db.client.start_session.return_value.__enter__.return_value = session
        get_db.return_value = db

        user, delivered = services.register_user("cineuser", "cine@example.com", "StrongPassword!27")

        self.assertFalse(delivered)
        self.assertFalse(user["is_verified"])
        self.assertEqual(db.email_verifications.insert_one.call_count, 1)

    @patch("accounts.views.register_user", return_value=({"_id": ObjectId(), "password_hash": "private", "role": "user"}, True))
    def test_registration_response_never_contains_credentials_or_tokens(self, _register):
        request = APIRequestFactory().post("/api/auth/register/", {
            "username": "cineuser", "email": "cine@example.com",
            "password": "StrongPassword!27", "password_confirmation": "StrongPassword!27",
        }, format="json")
        request._dont_enforce_csrf_checks = True
        with patch.object(RegisterView, "throttle_classes", []):
            response = RegisterView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["verification_required"])
        self.assertNotIn("access_token", response.data)
        self.assertNotIn("refresh_token", response.data)
        self.assertNotIn("password_hash", response.data)


class MongoConfigurationTests(SimpleTestCase):
    def test_refresh_view_keeps_the_mongo_throttle_and_refresh_scope(self):
        self.assertEqual(RefreshView.throttle_classes, [MongoRateThrottle])
        self.assertEqual(RefreshView.throttle_scope, "auth_refresh")

    def test_authentication_collections_create_unique_and_ttl_indexes(self):
        db = MagicMock()
        ensure_indexes(db)
        calls = [call for collection in (db.users, db.email_verifications, db.refresh_sessions, db.auth_rate_limits)
                 for call in collection.create_index.call_args_list]
        names = {call.kwargs.get("name") for call in calls}
        self.assertIn("users_email_unique", names)
        self.assertIn("users_username_unique", names)
        self.assertIn("email_verifications_ttl", names)
        self.assertIn("refresh_sessions_current_jti_unique", names)
        self.assertIn("refresh_sessions_ttl", names)
        self.assertIn("auth_rate_limits_ttl", names)

    @patch("accounts.throttles.get_auth_database")
    def test_authentication_throttle_stores_a_hashed_client_key(self, get_db):
        db = MagicMock()
        db.auth_rate_limits.find_one_and_update.return_value = {"count": 1}
        get_db.return_value = db
        throttle = MongoRateThrottle()
        throttle.scope = "auth_login"
        request = APIRequestFactory().post("/api/auth/login/")
        request.META["REMOTE_ADDR"] = "192.0.2.10"
        with patch.object(throttle, "get_rate", return_value="2/minute"):
            self.assertTrue(throttle.allow_request(request, type("LoginView", (), {"throttle_scope": "auth_login"})()))
        query = db.auth_rate_limits.find_one_and_update.call_args.args[0]
        self.assertEqual(len(query["_id"]), 64)
        self.assertNotIn("192.0.2.10", query["_id"])


class OpenApiDocumentationTests(SimpleTestCase):
    def test_documentation_and_schema_do_not_require_mongodb(self):
        with patch("accounts.mongo.get_database", side_effect=AssertionError("Schema generation must not access MongoDB")):
            for path in ("/api/docs/", "/api/redoc/", "/api/schema/"):
                response = self.client.get(path, HTTP_HOST="localhost")
                self.assertEqual(response.status_code, 200, path)
                if path == "/api/redoc/":
                    self.assertIn(b"redoc@2.1.5", response.content)


class CsrfFlowTests(SimpleTestCase):
    @override_settings(
        DEBUG=True,
        CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5173", "http://127.0.0.1:5174"],
        CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    )
    def test_local_vite_origins_can_submit_with_the_issued_csrf_token(self):
        for origin in ("http://127.0.0.1:5173", "http://127.0.0.1:5174"):
            client = Client(enforce_csrf_checks=True)
            csrf_response = client.get("/api/auth/csrf/", HTTP_HOST="127.0.0.1", HTTP_ORIGIN=origin)
            self.assertEqual(csrf_response.status_code, 200)
            self.assertIn("csrftoken", client.cookies)

            with patch.object(LoginView, "throttle_classes", []):
                response = client.post(
                    "/api/auth/login/", data="{}", content_type="application/json",
                    HTTP_HOST="127.0.0.1", HTTP_ORIGIN=origin,
                    HTTP_X_CSRFTOKEN=csrf_response.json()["csrf_token"],
                )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["code"], "validation_error")


class EmailDeliveryTests(SimpleTestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="CineSplit <no-reply@example.com>",
        EMAIL_HOST="smtp.example.com", EMAIL_PORT=587,
        EMAIL_HOST_USER="", EMAIL_HOST_PASSWORD="",
        EMAIL_USE_TLS=True, EMAIL_USE_SSL=False,
        EMAIL_VERIFICATION_EXPIRY_MINUTES=10,
    )
    @patch("accounts.email_service.EmailMultiAlternatives")
    def test_message_has_plain_and_html_parts(self, email_class):
        email_class.return_value.send.return_value = 1
        email_service.send_verification_email("cine@example.com", "000042")
        self.assertIn("000042", email_class.call_args.args[1])
        self.assertEqual(email_class.return_value.attach_alternative.call_count, 1)
        html = email_class.return_value.attach_alternative.call_args.args[0]
        self.assertIn("000042", html)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        EMAIL_HOST="smtp.example.com", EMAIL_PORT=587,
        EMAIL_HOST_USER="user", EMAIL_HOST_PASSWORD="secret",
        EMAIL_USE_TLS=True, EMAIL_USE_SSL=False,
    )
    @patch("accounts.email_service.EmailMultiAlternatives.send", side_effect=smtplib.SMTPAuthenticationError(535, b"rejected"))
    def test_smtp_failure_is_sanitized_and_does_not_log_the_code(self, _send):
        with self.assertLogs("accounts.email_service", logging.WARNING) as captured:
            with self.assertRaises(email_service.EmailDeliveryError):
                email_service.send_verification_email("cine@example.com", "981204")
        self.assertNotIn("981204", " ".join(captured.output))
        self.assertNotIn("secret", " ".join(captured.output))


class TokenTests(SimpleTestCase):
    @override_settings(JWT_SECRET_KEY="a-distinct-development-test-secret", SECRET_KEY="another-secret", JWT_ALGORITHM="HS256", JWT_ACCESS_TOKEN_LIFETIME=15, JWT_REFRESH_TOKEN_LIFETIME=7, JWT_ISSUER="", JWT_AUDIENCE="")
    def test_access_and_refresh_tokens_have_separate_types(self):
        user = {"_id": ObjectId()}
        access = tokens.create_access_token(user)
        refresh = tokens.create_refresh_token(user["_id"], "session-1", "family-1", "refresh-jti")
        self.assertEqual(tokens.decode_token(access, "access")["sub"], str(user["_id"]))
        self.assertEqual(tokens.decode_token(refresh, "refresh")["sid"], "session-1")
        with self.assertRaises(tokens.TokenError):
            tokens.decode_token(refresh, "access")


class VerificationServiceTests(SimpleTestCase):
    @override_settings(EMAIL_VERIFICATION_MAX_ATTEMPTS=5)
    @patch("accounts.services.get_auth_database")
    def test_successful_verification_consumes_code_and_marks_user(self, get_db):
        user_id = ObjectId()
        code_hash = security.hash_email_code("000731")
        now = security.utc_now()
        db = MagicMock()
        db.users.find_one.return_value = {"_id": user_id, "is_verified": False}
        db.email_verifications.find_one.return_value = {
            "_id": ObjectId(), "user_id": user_id, "code_hash": code_hash,
            "expires_at": now + timedelta(minutes=5), "attempts": 0,
            "invalidated_at": None, "verified_at": None,
        }
        db.email_verifications.find_one_and_update.return_value = {"_id": ObjectId()}
        db.users.update_one.return_value.modified_count = 1
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        db.client.start_session.return_value.__enter__.return_value = session
        get_db.return_value = db

        self.assertIsNone(services.verify_email("cine@example.com", "000731"))
        self.assertIsNotNone(db.email_verifications.find_one_and_update.call_args.kwargs["session"])
        self.assertTrue(db.users.update_one.called)

    @override_settings(EMAIL_VERIFICATION_MAX_ATTEMPTS=5)
    @patch("accounts.services.get_auth_database")
    def test_wrong_code_increments_attempt_count(self, get_db):
        user_id = ObjectId()
        now = security.utc_now()
        db = MagicMock()
        db.users.find_one.return_value = {"_id": user_id, "is_verified": False}
        db.email_verifications.find_one.return_value = {
            "_id": ObjectId(), "user_id": user_id, "code_hash": security.hash_email_code("000731"),
            "expires_at": now + timedelta(minutes=5), "attempts": 0,
            "invalidated_at": None, "verified_at": None,
        }
        db.email_verifications.find_one_and_update.return_value = {"attempts": 1}
        get_db.return_value = db

        with self.assertRaises(services.VerificationFailure):
            services.verify_email("cine@example.com", "999999")
        self.assertEqual(db.email_verifications.find_one_and_update.call_args.args[1], {"$inc": {"attempts": 1}})

    @override_settings(EMAIL_VERIFICATION_MAX_ATTEMPTS=5)
    @patch("accounts.services.get_auth_database")
    def test_attempt_limit_and_expiration_are_checked_before_comparison(self, get_db):
        now = security.utc_now()
        db = MagicMock()
        db.users.find_one.return_value = {"_id": ObjectId(), "is_verified": False}
        db.email_verifications.find_one.return_value = {
            "_id": ObjectId(), "user_id": db.users.find_one.return_value["_id"],
            "code_hash": "not-checked", "expires_at": now - timedelta(seconds=1),
            "attempts": 0, "invalidated_at": None, "verified_at": None,
        }
        get_db.return_value = db
        with self.assertRaises(services.VerificationFailure) as caught:
            services.verify_email("cine@example.com", "000731")
        self.assertEqual(caught.exception.code, "expired_code")
        db.email_verifications.find_one_and_update.assert_not_called()

    @override_settings(EMAIL_VERIFICATION_MAX_ATTEMPTS=5)
    @patch("accounts.services.verify_email_code", return_value=True)
    @patch("accounts.services.get_auth_database")
    def test_concurrent_consumption_cannot_verify_a_code_twice(self, get_db, _compare):
        user_id = ObjectId()
        now = security.utc_now()
        db = MagicMock()
        db.users.find_one.return_value = {"_id": user_id, "is_verified": False}
        db.email_verifications.find_one.return_value = {
            "_id": ObjectId(), "user_id": user_id, "code_hash": "hash",
            "expires_at": now + timedelta(minutes=5), "attempts": 0,
            "invalidated_at": None, "verified_at": None,
        }
        db.email_verifications.find_one_and_update.return_value = None
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        db.client.start_session.return_value.__enter__.return_value = session
        get_db.return_value = db
        with self.assertRaises(services.VerificationFailure):
            services.verify_email("cine@example.com", "000731")
        db.users.update_one.assert_not_called()


class AuthenticationServiceTests(SimpleTestCase):
    @override_settings(JWT_SECRET_KEY="a-distinct-development-test-secret", SECRET_KEY="another-secret", JWT_ALGORITHM="HS256", JWT_ACCESS_TOKEN_LIFETIME=15, JWT_REFRESH_TOKEN_LIFETIME=7, JWT_ISSUER="", JWT_AUDIENCE="")
    @patch("accounts.services.get_auth_database")
    def test_unverified_user_never_receives_tokens(self, get_db):
        db = MagicMock()
        db.users.find_one.return_value = {
            "_id": ObjectId(), "password_hash": security.hash_password("StrongPassword!27"),
            "is_active": True, "is_verified": False,
        }
        get_db.return_value = db
        with self.assertRaises(services.AuthenticationFailure) as caught:
            services.login("cine@example.com", "StrongPassword!27")
        self.assertEqual(caught.exception.code, "email_not_verified")
        db.refresh_sessions.insert_one.assert_not_called()

    @override_settings(JWT_SECRET_KEY="a-distinct-development-test-secret", SECRET_KEY="another-secret", JWT_ALGORITHM="HS256", JWT_ACCESS_TOKEN_LIFETIME=15, JWT_REFRESH_TOKEN_LIFETIME=7, JWT_ISSUER="", JWT_AUDIENCE="")
    @patch("accounts.services.get_auth_database")
    def test_verified_login_creates_refresh_session_without_storing_token(self, get_db):
        user = {
            "_id": ObjectId(), "email": "cine@example.com", "username": "cineuser",
            "password_hash": security.hash_password("StrongPassword!27"),
            "role": "user", "is_active": True, "is_verified": True,
        }
        db = MagicMock()
        db.users.find_one.return_value = user
        get_db.return_value = db
        access, refresh, returned_user = services.login("cine@example.com", "StrongPassword!27")
        self.assertEqual(tokens.decode_token(access, "access")["sub"], str(user["_id"]))
        self.assertEqual(tokens.decode_token(refresh, "refresh")["type"], "refresh")
        session = db.refresh_sessions.insert_one.call_args.args[0]
        self.assertNotIn("refresh_token", session)
        self.assertEqual(session["current_jti"], tokens.decode_token(refresh, "refresh")["jti"])
        self.assertEqual(session["family_id"], tokens.decode_token(refresh, "refresh")["fam"])
        self.assertIsNotNone(returned_user["last_login"])

    @patch("accounts.services.get_auth_database")
    def test_password_change_hashes_new_password_and_revokes_sessions(self, get_db):
        user_id = ObjectId()
        old_hash = security.hash_password("StrongPassword!27")
        db = MagicMock()
        db.users.find_one.return_value = {"_id": user_id, "password_hash": old_hash}
        db.users.update_one.return_value.modified_count = 1
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        db.client.start_session.return_value.__enter__.return_value = session
        get_db.return_value = db
        services.change_password(str(user_id), "StrongPassword!27", "NewStrongPass#2026")
        update = db.users.update_one.call_args.args[1]["$set"]
        self.assertNotEqual(update["password_hash"], old_hash)
        self.assertTrue(security.verify_password("NewStrongPass#2026", update["password_hash"]))
        db.refresh_sessions.update_many.assert_called_once()


class RefreshRotationTests(SimpleTestCase):
    @override_settings(JWT_SECRET_KEY="a-distinct-development-test-secret", SECRET_KEY="another-secret", JWT_ALGORITHM="HS256", JWT_ACCESS_TOKEN_LIFETIME=15, JWT_REFRESH_TOKEN_LIFETIME=7, JWT_ISSUER="", JWT_AUDIENCE="")
    @patch("accounts.services.get_auth_database")
    def test_rotation_replaces_jti_and_records_old_jti(self, get_db):
        user_id = ObjectId()
        old_token = tokens.create_refresh_token(user_id, "session-1", "family-1", "old-jti")
        db = MagicMock()
        db.refresh_sessions.find_one.return_value = {
            "_id": "session-1", "family_id": "family-1", "user_id": user_id,
            "current_jti": "old-jti", "used_jtis": [], "revoked_at": None,
            "expires_at": security.utc_now() + timedelta(days=6),
        }
        db.users.find_one.return_value = {"_id": user_id, "is_active": True, "is_verified": True}
        db.refresh_sessions.update_one.return_value.modified_count = 1
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        db.client.start_session.return_value.__enter__.return_value = session
        get_db.return_value = db

        access, refresh = services.rotate_refresh_token(old_token)
        self.assertEqual(tokens.decode_token(access, "access")["type"], "access")
        self.assertNotEqual(tokens.decode_token(refresh, "refresh")["jti"], "old-jti")
        self.assertEqual(db.refresh_sessions.update_one.call_args.args[1]["$addToSet"], {"used_jtis": "old-jti"})

    @override_settings(JWT_SECRET_KEY="a-distinct-development-test-secret", SECRET_KEY="another-secret", JWT_ALGORITHM="HS256", JWT_ACCESS_TOKEN_LIFETIME=15, JWT_REFRESH_TOKEN_LIFETIME=7, JWT_ISSUER="", JWT_AUDIENCE="")
    @patch("accounts.services.get_auth_database")
    def test_replayed_refresh_token_revokes_its_family(self, get_db):
        user_id = ObjectId()
        old_token = tokens.create_refresh_token(user_id, "session-1", "family-1", "old-jti")
        db = MagicMock()
        db.refresh_sessions.find_one.return_value = {
            "_id": "session-1", "family_id": "family-1", "user_id": user_id,
            "current_jti": "new-jti", "used_jtis": ["old-jti"], "revoked_at": None,
            "expires_at": security.utc_now() + timedelta(days=6),
        }
        session = MagicMock()
        session.with_transaction.side_effect = lambda callback: callback(session)
        db.client.start_session.return_value.__enter__.return_value = session
        get_db.return_value = db
        with self.assertRaises(services.RefreshFailure) as caught:
            services.rotate_refresh_token(old_token)
        self.assertEqual(caught.exception.code, "refresh_replay")
        self.assertIn("revoked_at", db.refresh_sessions.update_one.call_args.args[1]["$set"])
