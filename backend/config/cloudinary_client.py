import os

import cloudinary


def is_cloudinary_configured():
    return all(os.getenv(name, "").strip() for name in (
        "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"
    ))


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
