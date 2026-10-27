from django.contrib import admin
from .models import Song, Rating


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'album', 'genre', 'release_year', 'added_by', 'average_rating', 'rating_count')
    list_filter = ('genre',)
    search_fields = ('title', 'artist', 'album')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'score', 'liked', 'created_at')
    list_filter = ('liked', 'score')
    search_fields = ('user__username', 'song__title')
