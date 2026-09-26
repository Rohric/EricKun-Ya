"""Side effects for the products app: keep image files and folders tidy."""

import shutil
from pathlib import Path

from django.conf import settings
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from products_app.models import Product, ProductImage


@receiver(post_delete, sender=ProductImage)
def delete_image_file(sender, instance, **kwargs):
    """Remove the image file from disk when its record is deleted."""
    instance.image.delete(save=False)


@receiver(pre_save, sender=ProductImage)
def delete_replaced_image_file(sender, instance, **kwargs):
    """Remove the previous file when an image is replaced on an existing record."""
    if not instance.pk:
        return
    old = ProductImage.objects.filter(pk=instance.pk).first()
    if old and old.image and old.image != instance.image:
        old.image.delete(save=False)


@receiver(post_delete, sender=Product)
def delete_product_folder(sender, instance, **kwargs):
    """Remove the product's now-empty image folder after deletion."""
    folder = Path(settings.MEDIA_ROOT) / "products" / instance.sku
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
