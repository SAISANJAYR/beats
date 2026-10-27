import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import Song, Rating
from .forms import SongForm, RatingForm, SignUpForm
from .gemini_service import get_song_recommendations

logger = logging.getLogger(__name__)


# ── Home / Letterboxd Feed ────────────────────────────────────────────────────

def home(request):
    query = request.GET.get('q', '').strip()
    selected_genre = request.GET.get('genre', '').strip()
    sort = request.GET.get('sort', 'popular')

    songs = Song.objects.annotate(
        avg_rating=Avg('ratings__score'),
        num_ratings=Count('ratings')
    )

    if query:
        songs = songs.filter(
            Q(title__icontains=query) | Q(artist__icontains=query) | Q(album__icontains=query)
        )
    if selected_genre:
        songs = songs.filter(genre=selected_genre)

    if sort == 'rating':
        songs = songs.order_by('-avg_rating', '-num_ratings')
    elif sort == 'newest':
        songs = songs.order_by('-created_at')
    else:  # popular
        songs = songs.order_by('-num_ratings', '-avg_rating')

    # Popular / Trending highlight (top 6)
    popular_songs = Song.objects.annotate(
        avg_rating=Avg('ratings__score'),
        num_ratings=Count('ratings')
    ).order_by('-num_ratings', '-avg_rating')[:6]

    # Recent Community Reviews (Letterboxd activity style)
    recent_reviews = Rating.objects.select_related('song', 'user').exclude(review__exact='').order_by('-created_at')[:6]

    # Quick platform statistics
    total_songs = Song.objects.count()
    total_ratings = Rating.objects.count()

    context = {
        'songs': songs,
        'popular_songs': popular_songs,
        'recent_reviews': recent_reviews,
        'query': query,
        'selected_genre': selected_genre,
        'genre_choices': Song.GENRE_CHOICES,
        'sort': sort,
        'total_songs': total_songs,
        'total_ratings': total_ratings,
    }
    return render(request, 'beats/home.html', context)


# ── Song Detail ────────────────────────────────────────────────────────────────

def song_detail(request, pk):
    song = get_object_or_404(
        Song.objects.annotate(
            avg_rating=Avg('ratings__score'),
            num_ratings=Count('ratings')
        ),
        pk=pk
    )
    ratings = song.ratings.select_related('user').order_by('-created_at')
    user_rating = None
    if request.user.is_authenticated:
        user_rating = Rating.objects.filter(song=song, user=request.user).first()

    # Letterboxd-style rating histogram breakdown (0.5 to 5.0)
    rating_histogram = []
    total_rated = song.ratings.count()
    for star in [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5]:
        count = song.ratings.filter(score=star).count()
        pct = (count / total_rated * 100) if total_rated > 0 else 0
        rating_histogram.append({
            'score': star,
            'count': count,
            'pct': round(pct, 1)
        })

    context = {
        'song': song,
        'ratings': ratings,
        'user_rating': user_rating,
        'rating_histogram': rating_histogram,
        'total_liked': song.ratings.filter(liked=True).count(),
    }
    return render(request, 'beats/song_detail.html', context)


# ── Add Song ───────────────────────────────────────────────────────────────────

@login_required
def add_song(request):
    if request.method == 'POST':
        form = SongForm(request.POST)
        if form.is_valid():
            song = form.save(commit=False)
            song.added_by = request.user
            song.save()
            messages.success(request, f'"{song.title}" added to the crate!')
            return redirect('song_detail', pk=song.pk)
    else:
        # Pre-fill from query params if clicked from AI recommendations
        initial = {
            'title': request.GET.get('title', ''),
            'artist': request.GET.get('artist', ''),
            'album': request.GET.get('album', ''),
            'genre': request.GET.get('genre', 'other'),
            'release_year': request.GET.get('year', ''),
        }
        form = SongForm(initial=initial)

    return render(request, 'beats/add_song.html', {'form': form})


# ── Rate / Log Song ────────────────────────────────────────────────────────────

@login_required
def rate_song(request, pk):
    song = get_object_or_404(Song, pk=pk)
    existing = Rating.objects.filter(song=song, user=request.user).first()

    if request.method == 'POST':
        form = RatingForm(request.POST, instance=existing)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.song = song
            rating.user = request.user
            rating.save()
            messages.success(request, f'Logged {rating.score}★ for "{song.title}"')
            return redirect('song_detail', pk=song.pk)
    else:
        form = RatingForm(instance=existing)

    return render(request, 'beats/rate_song.html', {'form': form, 'song': song, 'existing': existing})


# ── Delete Rating ──────────────────────────────────────────────────────────────

@login_required
def delete_rating(request, pk):
    rating = get_object_or_404(Rating, pk=pk, user=request.user)
    song_pk = rating.song.pk
    rating.delete()
    messages.success(request, 'Rating removed from diary.')
    return redirect('song_detail', pk=song_pk)


# ── Profile ────────────────────────────────────────────────────────────────────

def profile(request, username):
    user = get_object_or_404(User, username=username)
    ratings = Rating.objects.filter(user=user).select_related('song').order_by('-created_at')
    liked = ratings.filter(liked=True)
    songs_added = Song.objects.filter(added_by=user).annotate(
        avg_rating=Avg('ratings__score'),
        num_ratings=Count('ratings')
    )

    avg_score = ratings.aggregate(avg=Avg('score'))['avg']

    context = {
        'profile_user': user,
        'ratings': ratings,
        'liked': liked,
        'songs_added': songs_added,
        'avg_score': avg_score,
    }
    return render(request, 'beats/profile.html', context)


# ── Crate Digger (Dedicated AI Chatbot Page) ───────────────────────────────────

def crate_digger_view(request):
    """Full-page experience for the Gemini-powered AI music curator."""
    popular_prompts = [
        "Late night Tokyo drive through rain with neon synthwave",
        "Melancholic acoustic folk for a Sunday morning coffee",
        "Dark heavy bass cyberpunk phonk for a workout",
        "70s French & Japanese disco with infectious basslines",
        "Songs that feel like The Cure meets Daft Punk",
        "90s shoegaze that sounds like a warm wall of sound",
    ]
    return render(request, 'beats/crate_digger.html', {
        'popular_prompts': popular_prompts,
    })


# ── Gemini Recommendation API Endpoint ─────────────────────────────────────────

@require_POST
def api_recommendations(request):
    """
    JSON API endpoint for AI song recommendations using Gemini.
    Accepts JSON body: { "prompt": "...", "api_key": "..." (optional) }
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    prompt = (data.get('prompt') or '').strip()
    user_api_key = (data.get('api_key') or '').strip()

    if not prompt:
        return JsonResponse({'error': 'Please provide a prompt or theme.'}, status=400)

    try:
        recommendations = get_song_recommendations(prompt, user_api_key=user_api_key)

        # Cross-reference with existing database songs so user knows if it's already in the crate!
        rec_list = recommendations.get('recommendations', [])
        for item in rec_list:
            existing_song = Song.objects.filter(
                title__iexact=item.get('title'),
                artist__iexact=item.get('artist')
            ).first()
            if existing_song:
                item['existing_id'] = existing_song.pk
                item['avg_rating'] = existing_song.average_rating()
            else:
                item['existing_id'] = None

        return JsonResponse({
            'success': True,
            'data': recommendations
        })
    except ValueError as val_err:
        return JsonResponse({'error': str(val_err)}, status=400)
    except Exception as e:
        logger.exception("Error in api_recommendations: %s", e)
        return JsonResponse({'error': f"AI service error: {str(e)}"}, status=500)


# ── Quick Add from Recommendation API ──────────────────────────────────────────

@require_POST
def api_quick_add(request):
    """
    Allows one-click addition of a recommended song to the database.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Sign in required to add songs.'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    title = (data.get('title') or '').strip()
    artist = (data.get('artist') or '').strip()
    album = (data.get('album') or '').strip()
    genre = (data.get('genre') or 'other').strip().lower()
    year = data.get('year')

    if not title or not artist:
        return JsonResponse({'error': 'Title and artist are required.'}, status=400)

    # Valid genre check
    valid_genres = dict(Song.GENRE_CHOICES).keys()
    if genre not in valid_genres:
        genre = 'other'

    try:
        release_year = int(year) if year else None
    except (ValueError, TypeError):
        release_year = None

    # Check if exists or create
    song, created = Song.objects.get_or_create(
        title=title,
        artist=artist,
        defaults={
            'album': album,
            'genre': genre,
            'release_year': release_year,
            'added_by': request.user,
        }
    )

    return JsonResponse({
        'success': True,
        'created': created,
        'song_id': song.pk,
        'song_url': f"/song/{song.pk}/",
        'rate_url': f"/song/{song.pk}/rate/",
        'title': song.title,
        'artist': song.artist,
    })


# ── Auth ───────────────────────────────────────────────────────────────────────

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Beats, {user.username}!')
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'beats/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'beats/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')
