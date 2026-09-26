from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username


class DemoResetState(models.Model):
    """
    Singleton (pk=1): remembers when the demo account was last reset.
    Read by DemoResetMiddleware and updated by the reset_demo command.
    """

    last_reset = models.DateTimeField()

    def __str__(self):
        return f"Last demo reset: {self.last_reset:%Y-%m-%d %H:%M}"
