from django.db import models

class LeaderboardEntry(models.Model):
    username = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200, blank=True)
    avatar = models.URLField(blank=True)
    score = models.IntegerField(default=0)
    rank = models.CharField(max_length=100, blank=True)
    rank_icon = models.CharField(max_length=10, blank=True)
    total_repos = models.IntegerField(default=0)
    total_stars = models.IntegerField(default=0)
    searched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-score']

    def __str__(self):
        return f"{self.username} - {self.score}"