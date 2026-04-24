from django.db import models

class IdempotencyRecord(models.Model):
    key = models.CharField(max_length=255, unique=True)
    request_body_hash = models.CharField(max_length=64)
    response_body = models.JSONField()
    status_code = models.IntegerField()
    is_processing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.key