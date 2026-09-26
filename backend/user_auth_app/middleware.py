import logging
import time
from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)

# How long the guest may play around before the account gets cleaned up.
RESET_INTERVAL = timedelta(minutes=20)

# Hit the database at most once per minute instead of on every request.
CHECK_EVERY_SECONDS = 60


class DemoResetMiddleware:
    """
    Automatically resets the demo account (guest login) once the last
    reset is older than RESET_INTERVAL.

    Piggybacks on incoming requests instead of relying on an external
    scheduler - this works identically under runserver, Gunicorn and
    inside a Docker container, without cron. If nobody visits the site,
    there is nothing to clean up either.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._next_check = 0.0

    def __call__(self, request):
        self._maybe_reset()
        return self.get_response(request)

    def _maybe_reset(self):
        now = time.monotonic()
        if now < self._next_check:
            return
        self._next_check = now + CHECK_EVERY_SECONDS

        try:
            self._reset_if_due()
        except Exception:
            # The demo reset must never break a real request.
            logger.exception("Demo reset failed")

    def _reset_if_due(self):
        from user_auth_app.models import DemoResetState

        state, created = DemoResetState.objects.get_or_create(
            pk=1, defaults={"last_reset": timezone.now()}
        )
        if created:
            # First start: create the demo data, the interval starts now.
            call_command("seed_demo")
            return

        if timezone.now() - state.last_reset >= RESET_INTERVAL:
            call_command("reset_demo")
