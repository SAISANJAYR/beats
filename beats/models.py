from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Song(models.Model):
    GENRE_CHOICES = [
        ('pop', 'Pop'),
        ('hiphop', 'Hip-Hop / Rap'),
        ('rnb', 'R&B / Soul'),
        ('rock', 'Rock'),
        ('electronic', 'Electronic'),
        ('jazz', 'Jazz'),
        ('classical', 'Classical'),
        ('country', 'Country'),
        ('latin', 'Latin'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    album = models.CharField(max_length=200, blank=True)
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES, default='other')
    release_year = models.PositiveIntegerField(null=True, blank=True)
    cover_url = models.URLField(blank=True, help_text="URL to album art image")
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='songs_added')
    created_at = models.DateTimeField(auto_now_add=True)

    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(r.score for r in ratings) / ratings.count(), 1)
        return None

    def rating_count(self):
        return self.ratings.count()

    def __str__(self):
        return f"{self.title} — {self.artist}"

    class Meta:
        ordering = ['-created_at']


class Rating(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    score = models.FloatField(
        validators=[MinValueValidator(0.5), MaxValueValidator(5.0)]
    )
    review = models.TextField(blank=True)
    liked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('song', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} rated '{self.song.title}' {self.score}/5"

    def score_display(self):
        """Returns half-star string e.g. ★★★½"""
        full = int(self.score)
        half = (self.score * 2) % 2 == 1
        stars = '★' * full
        if half:
            stars += '½'
        return stars
