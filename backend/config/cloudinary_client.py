import os

import cloudinary


REQUIRED_CLOUDINARY_VARIABLES = (
    "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"
)


def missing_cloudinary_variables():
    return [name for name in REQUIRED_CLOUDINARY_VARIABLES if not os.getenv(name, "").strip()]


def is_cloudinary_configured():
    return not missing_cloudinary_variables()


def configure_cloudinary():
    if not is_cloudinary_configured():
        return False
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"].strip(),
        api_key=os.environ["CLOUDINARY_API_KEY"].strip(),
        api_secret=os.environ["CLOUDINARY_API_SECRET"].strip(),
        secure=True,
    )
    return True
