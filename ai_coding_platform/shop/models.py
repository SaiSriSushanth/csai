from django.db import models
from django.contrib.auth.models import User

class PowerUp(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    cost = models.IntegerField()
    # Optionally store an image URL for a thumbnail
    # image_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='powerup_images/', blank=True, null=True)

    def __str__(self):
        return self.name

class Inventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    powerup = models.ForeignKey(PowerUp, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ('user', 'powerup')

    def __str__(self):
        return f"{self.user.username} - {self.powerup.name} (x{self.quantity})"
