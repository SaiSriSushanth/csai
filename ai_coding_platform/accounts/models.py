from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    streak = models.IntegerField(default=0)
    xp = models.IntegerField(default=0)       # Experience points
    level = models.IntegerField(default=1)      # Starting at level 1
    coins = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

# Automatically create or update Profile whenever a User is created or saved.
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
