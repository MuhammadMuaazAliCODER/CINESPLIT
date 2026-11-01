from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .services import MediaConfigurationError, MediaError, upload_and_associate, validate_upload
from .views import AdminContentMediaUploadView, AdminContentMediaView


class MediaValidationTests(SimpleTestCase):
    def test_accepts_supported_signature_and_rejects_spoofed_type_and_oversize(self):
        validate_upload(SimpleUploadedFile("movie.mp4", b"\x00\x00\x00\x18ftypisom", content_type="video/mp4"), "video")
        with self.assertRaises(MediaError):
            validate_upload(SimpleUploadedFile("movie.mp4", b"not a movie", content_type="video/mp4"), "video")
        with self.assertRaises(MediaError):
            validate_upload(SimpleUploadedFile("bad.exe", b"x", content_type="application/octet-stream"), "video")
        upload = SimpleUploadedFile("large.mp4", b"\x00\x00\x00\x18ftypisom", content_type="video/mp4")
        upload.size = 500 * 1024 * 1024 + 1
        with self.assertRaises(MediaError):
            validate_upload(upload, "video")

    def test_rejects_invalid_role(self):
        with self.assertRaises(MediaError):
            validate_upload(SimpleUploadedFile("image.jpg", b"\xff\xd8\xffabc", content_type="image/jpeg"), "thumbnail")


class MediaUploadServiceTests(SimpleTestCase):
    @patch("media.services._content_ref")
    @patch("media.services.uploader.upload")
    @patch("media.services.is_cloudinary_configured", return_value=False)
    @patch("media.services.missing_cloudinary_variables", return_value=["CLOUDINARY_API_SECRET"])
    def test_missing_cloudinary_credentials_raise_a_controlled_configuration_error(self, missing, configured, upload, content_ref):
        with self.assertRaisesRegex(MediaError, "CLOUDINARY_API_SECRET"):
            upload_and_associate("movie", str(ObjectId()), "video", SimpleUploadedFile("film.mp4", b"\x00\x00\x00\x18ftypisom", content_type="video/mp4"), "admin")
        upload.assert_not_called()
        content_ref.assert_not_called()

    @patch("media.services.get_media_collection")
    @patch("media.services.configure_cloudinary")
    @patch("media.services.is_cloudinary_configured", return_value=True)
    @patch("media.services._content_ref")
    @patch("media.services.uploader.upload")
    def test_upload_persists_association_and_uses_video_resource_type(self, upload, content_ref, configured, configure, media_collection):
        content_id = ObjectId()
        content = {"_id": content_id, "status": "published"}
        content_collection = MagicMock()
        content_collection.update_one.return_value.matched_count = 1
        content_ref.return_value = (content_collection, content_id, content)
        upload.return_value = {"public_id": "cinesplit/movie/video1", "secure_url": "https://res.cloudinary.com/demo/video/upload/video1.mp4", "format": "mp4", "duration": 90.5}
        result = upload_and_associate("movie", str(content_id), "video", SimpleUploadedFile("film.mp4", b"\x00\x00\x00\x18ftypisom", content_type="video/mp4"), "admin-1")
        self.assertEqual(upload.call_args.kwargs["resource_type"], "video")
        self.assertEqual(result["resource_type"], "video")
        self.assertEqual(result["duration"], 90.5)
        self.assertEqual(result["content_id"], str(content_id))
        self.assertEqual(content_collection.update_one.call_args.args[1]["$set"]["video"]["public_id"], result["public_id"])
        self.assertEqual(media_collection.return_value.find_one_and_update.call_args.kwargs["upsert"], True)

    @patch("media.services._content_ref")
    @patch("media.services.uploader.upload")
    def test_rejects_invalid_file_before_cloudinary_upload(self, upload, content_ref):
        with self.assertRaises(MediaError):
            upload_and_associate("movie", str(ObjectId()), "video", SimpleUploadedFile("bad.mp4", b"nope", content_type="video/mp4"), "admin")
        upload.assert_not_called()
        content_ref.assert_not_called()


class MediaAuthorizationTests(SimpleTestCase):
    @patch("media.views.upload_and_associate", side_effect=MediaConfigurationError("Media uploads are not configured. Set these backend environment variables: CLOUDINARY_API_SECRET."))
    def test_missing_cloudinary_configuration_returns_service_unavailable(self, upload):
        user = type("User", (), {"id": "admin-1", "role": "admin", "is_authenticated": True})()
        request = APIRequestFactory().post(
            "/api/admin/media/movie/65f000000000000000000001/video/",
            {"file": SimpleUploadedFile("film.mp4", b"\x00\x00\x00\x18ftypisom", content_type="video/mp4")},
            format="multipart",
        )
        force_authenticate(request, user=user)
        response = AdminContentMediaUploadView.as_view()(request, content_type="movie", content_id=str(ObjectId()), role="video")
        self.assertEqual(response.status_code, 503)
        self.assertIn("CLOUDINARY_API_SECRET", response.data["detail"])
        upload.assert_called_once()

    def test_non_admin_cannot_read_or_upload_content_media(self):
        user = type("User", (), {"id": "user-1", "role": "user", "is_authenticated": True})()
        request = APIRequestFactory().get("/api/admin/media/movie/65f000000000000000000001/")
        force_authenticate(request, user=user)
        self.assertEqual(AdminContentMediaView.as_view()(request, content_type="movie", content_id=str(ObjectId())).status_code, 403)
        request = APIRequestFactory().post("/api/admin/media/movie/65f000000000000000000001/video/", {"file": "bad"})
        force_authenticate(request, user=user)
        self.assertEqual(AdminContentMediaUploadView.as_view()(request, content_type="movie", content_id=str(ObjectId()), role="video").status_code, 403)
