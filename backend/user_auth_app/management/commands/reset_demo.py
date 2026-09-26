from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from board_app.models import Board
from task_app.models import Comment, Task
from user_auth_app.models import DemoResetState

from .seed_demo import DEMO_EMAIL


class Command(BaseCommand):
    help = (
        "Resets the demo account (guest login): deletes all demo data "
        "and seeds it again. Registered users are left untouched. "
        "Triggered by DemoResetMiddleware roughly every 20 minutes."
    )

    def handle(self, *args, **options):
        demo_user = User.objects.filter(username=DEMO_EMAIL).first()

        if demo_user:
            # Cascade removes memberships, tasks and comments of the demo boards.
            boards_deleted, _ = Board.objects.filter(owner=demo_user).delete()
            # Traces the guest may have left outside their own boards.
            tasks_deleted, _ = Task.objects.filter(creator=demo_user).delete()
            comments_deleted, _ = Comment.objects.filter(user=demo_user).delete()
            self.stdout.write(
                f"Demo data deleted ({boards_deleted + tasks_deleted + comments_deleted} objects)."
            )

        call_command("seed_demo")

        DemoResetState.objects.update_or_create(
            pk=1, defaults={"last_reset": timezone.now()}
        )
        self.stdout.write(self.style.SUCCESS("Demo account freshly reset."))
