from django.db import models
from django.contrib.auth.models import User

class CodeSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    code = models.TextField()
    output = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CodeSubmission {self.pk} - {self.created_at}"