from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from board_app.models import Board, BoardMembership
from task_app.models import Comment, Task

# Must match GUEST_LOGIN in frontend/shared/js/config.js.
DEMO_EMAIL = "guest@kanmind.de"
DEMO_PASSWORD = "asdasdasd"
DEMO_FULLNAME = "Guest User"

DEMO_BOARD_TITLE = "Demo Board"

DEMO_TASKS = [
    {
        "title": "Set up project structure",
        "description": "Create the Django project with board_app, task_app and user_auth_app.",
        "status": "done",
        "priority": "low",
        "due_in_days": -3,
    },
    {
        "title": "Implement token login",
        "description": "Provide registration and login via DRF token authentication.",
        "status": "done",
        "priority": "medium",
        "due_in_days": -1,
    },
    {
        "title": "Document the REST API",
        "description": "Describe all endpoints with example requests in the README.",
        "status": "review",
        "priority": "high",
        "due_in_days": 2,
    },
    {
        "title": "Test drag & drop",
        "description": "Move tasks between columns and verify the status changes.",
        "status": "in-progress",
        "priority": "high",
        "due_in_days": 4,
    },
    {
        "title": "Build dashboard statistics",
        "description": "Show task counters and the next deadline on the dashboard.",
        "status": "in-progress",
        "priority": "medium",
        "due_in_days": 7,
    },
    {
        "title": "Prepare deployment",
        "description": "Build the Docker setup with PostgreSQL and Nginx for the Hetzner server.",
        "status": "to-do",
        "priority": "high",
        "due_in_days": 10,
    },
    {
        "title": "Incorporate feedback",
        "description": "Review and address the notes from the code review.",
        "status": "to-do",
        "priority": "low",
        "due_in_days": 14,
    },
]

DEMO_COMMENTS = {
    "Document the REST API": [
        "The auth endpoints are already covered, boards are still missing.",
        "Don't forget an example for the token header!",
    ],
}


class Command(BaseCommand):
    help = "Creates the demo user (guest login) with board, tasks and comments. Idempotent."

    def handle(self, *args, **options):
        demo_user, created = User.objects.get_or_create(
            username=DEMO_EMAIL,
            defaults={"email": DEMO_EMAIL, "first_name": DEMO_FULLNAME},
        )
        if created:
            demo_user.set_password(DEMO_PASSWORD)
            demo_user.save()
            self.stdout.write(f"Demo user created: {DEMO_EMAIL}")
        elif demo_user.first_name != DEMO_FULLNAME:
            demo_user.first_name = DEMO_FULLNAME
            demo_user.save()
            self.stdout.write(f"Demo user renamed to: {DEMO_FULLNAME}")

        board, board_created = Board.objects.get_or_create(
            owner=demo_user, title=DEMO_BOARD_TITLE
        )
        # Without a membership, BoardsList.get_queryset() filters the board out.
        BoardMembership.objects.get_or_create(
            user=demo_user, board=board, defaults={"role": "owner"}
        )
        if board_created:
            self.stdout.write(f"Board created: {DEMO_BOARD_TITLE}")

        today = date.today()
        tasks_created = 0
        for entry in DEMO_TASKS:
            _, task_created = Task.objects.get_or_create(
                board=board,
                title=entry["title"],
                defaults={
                    "description": entry["description"],
                    "status": entry["status"],
                    "priority": entry["priority"],
                    "due_date": today + timedelta(days=entry["due_in_days"]),
                    "assignee": demo_user,
                    "reviewer": demo_user,
                    "creator": demo_user,
                },
            )
            tasks_created += task_created

        comments_created = 0
        for task_title, contents in DEMO_COMMENTS.items():
            task = Task.objects.filter(board=board, title=task_title).first()
            if not task:
                continue
            for content in contents:
                _, comment_created = Comment.objects.get_or_create(
                    task=task, user=demo_user, content=content
                )
                comments_created += comment_created

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready ({tasks_created} tasks, "
                f"{comments_created} comments newly created)."
            )
        )
