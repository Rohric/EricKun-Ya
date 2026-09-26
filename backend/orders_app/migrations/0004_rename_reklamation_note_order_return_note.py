# Hand-written so the existing notes are kept: a non-interactive makemigrations
# would drop the old column and add a new, empty one instead of renaming it.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("orders_app", "0003_alter_orderitem_product"),
    ]

    operations = [
        migrations.RenameField(
            model_name="order",
            old_name="reklamation_note",
            new_name="return_note",
        ),
    ]
