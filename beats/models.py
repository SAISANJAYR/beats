import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


# ── Song & Rating Models ──────────────────────────────────────────────────────

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


# ── Assessment Requirements: FAQ, ErrorCode & SupportTicket Models ────────────

class FAQ(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General & Overview'),
        ('ratings', 'Logging & Ratings'),
        ('ai', 'AI Assistant & Crate Digger'),
        ('account', 'Account & Security'),
        ('troubleshooting', 'Troubleshooting'),
    ]

    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='general')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="HTTP status code or site-specific code")
    name = models.CharField(max_length=100)
    explanation = models.TextField(help_text="Detailed explanation of what the error means")
    solution = models.TextField(help_text="Actionable steps for the user or developer to resolve it")
    is_site_specific = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"


def generate_ticket_id():
    return 'BEATS-' + ''.join(random.choices(string.digits, k=5))


class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    ]

    SOURCE_CHOICES = [
        ('AI_ASSISTANT', 'AI Assistant (Automated escalation)'),
        ('HELP_PAGE', 'Help / FAQ Page'),
        ('ERROR_PAGE', 'Custom Error Page (404/500)'),
    ]

    ticket_id = models.CharField(max_length=20, unique=True, default=generate_ticket_id)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_tickets')
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='AI_ASSISTANT')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.ticket_id}] {self.subject} ({self.status})"
