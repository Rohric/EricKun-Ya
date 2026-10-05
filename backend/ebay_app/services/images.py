"""Host product images on eBay (Media API), because the desktop app has no public URLs."""

from pathlib import Path

from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from ebay_app.models import EbayImage
from ebay_app.services.oauth import call

UPLOAD_PATH = "/commerce/media/v1_beta/image/create_image_from_file"
MAX_IMAGES = 24  # eBay's limit per listing
NO_IMAGES = "eBay verlangt mindestens ein Bild. Bitte zuerst ein Bild am Artikel hochladen."


def image_urls(product):
    """Return eBay-hosted URLs of the product's images, uploading missing ones first."""
    images = list(product.images.select_related("ebay_image")[:MAX_IMAGES])
    if not images:
        raise ValidationError(NO_IMAGES)
    return [_hosted_url(image) for image in images]


def _hosted_url(image):
    """Return the cached eBay URL of an image, or upload the file and remember the result."""
    hosted = getattr(image, "ebay_image", None)
    if hosted and hosted.is_valid_for(image):
        return hosted.eps_url
    data = _upload(image)
    defaults = {
        "eps_url": data["imageUrl"],
        "source_name": image.image.name,
        "expires_at": parse_datetime(data.get("expirationDate") or ""),
    }
    EbayImage.objects.update_or_create(image=image, defaults=defaults)
    return data["imageUrl"]


def _upload(image):
    """Send the image file to eBay as multipart form data."""
    with image.image.open("rb") as handle:
        files = {"image": (Path(image.image.name).name, handle)}
        return call("POST", UPLOAD_PATH, host="media", files=files)
