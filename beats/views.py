import json
import logging
import time
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db import connection

from .models import Song, Rating, FAQ, ErrorCode, SupportTicket
from .forms import SongForm, RatingForm, SignUpForm
from .gemini_service import get_assistant_response
from .mongo_service import log_feedback, is_mongo_connected, get_recent_chat_logs
from .third_party_service import get_listening_weather_and_vibe
from .middleware import RECENT_REQUESTS_LOG

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


# ── Crate Digger (Dedicated AI Studio) ─────────────────────────────────────────

def crate_digger_view(request):
    popular_prompts = [
        "Late night Tokyo drive through rain with neon synthwave",
        "Melancholic acoustic folk for a Sunday morning coffee",
        "Dark heavy bass cyberpunk phonk for a workout",
        "70s French & Japanese disco with infectious basslines",
        "Explain HTTP Error 404 and how it affects music playback",
        "Explain Error BEATS-444 Needle Scratch",
    ]
    return render(request, 'beats/crate_digger.html', {
        'popular_prompts': popular_prompts,
    })


# ── Assessment Requirement: FAQ & Error Code Page ──────────────────────────────

def faq_view(request):
    """
    Displays at least 10 FAQs stored in SQL and 8 error codes (400, 401, 403, 404, 429, 500, 503, BEATS-444).
    Also includes a live third-party weather/vibe widget with 2.0s timeout & fallback.
    """
    category = request.GET.get('category', '').strip()
    search_q = request.GET.get('q', '').strip()

    faqs = FAQ.objects.all().order_by('order')
    if category:
        faqs = faqs.filter(category=category)
    if search_q:
        faqs = faqs.filter(Q(question__icontains=search_q) | Q(answer__icontains=search_q))

    error_codes = ErrorCode.objects.all().order_by('order')

    # Assessment requirement: Third-party API with strict time limit and fallback
    live_vibe = get_listening_weather_and_vibe()

    categories = FAQ.CATEGORY_CHOICES

    context = {
        'faqs': faqs,
        'error_codes': error_codes,
        'categories': categories,
        'selected_category': category,
        'search_q': search_q,
        'live_vibe': live_vibe,
        'total_faqs': FAQ.objects.count(),
        'total_errors': ErrorCode.objects.count(),
    }
    return render(request, 'beats/faq.html', context)


# ── Assessment Requirement: Support Ticket Submission ──────────────────────────

def support_tickets_view(request):
    """View and search support tickets stored in the SQL database."""
    query = request.GET.get('ticket_id', '').strip()
    tickets = SupportTicket.objects.all().order_by('-created_at')

    found_ticket = None
    if query:
        found_ticket = SupportTicket.objects.filter(ticket_id__iexact=query).first()

    user_tickets = []
    if request.user.is_authenticated:
        user_tickets = SupportTicket.objects.filter(
            Q(user=request.user) | Q(email=request.user.email)
        ).order_by('-created_at')

    context = {
        'tickets': tickets[:20],
        'found_ticket': found_ticket,
        'user_tickets': user_tickets,
        'search_query': query,
    }
    return render(request, 'beats/tickets.html', context)


@require_POST
def create_ticket_api(request):
    """Creates a support ticket in SQL (called directly or escalated by AI)."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    email = (data.get('email') or '').strip()
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()
    source = data.get('source', 'HELP_PAGE')

    if not email or not message:
        return JsonResponse({'error': 'Email and message are required.'}, status=400)

    ticket = SupportTicket.objects.create(
        user=request.user if request.user.is_authenticated else None,
        email=email,
        subject=subject or 'General Inquiry / Assistance',
        message=message,
        source=source,
        status='OPEN'
    )

    return JsonResponse({
        'success': True,
        'ticket_id': ticket.ticket_id,
        'status': ticket.status,
        'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'message': f"Ticket {ticket.ticket_id} created successfully. Our team will review it shortly."
    })


# ── Assessment Requirement: MongoDB Feedback Endpoint ─────────────────────────

@require_POST
def submit_feedback_api(request):
    """
    Assessment Requirement: Feedback stored in MongoDB.
    Accepts JSON payload: { rating: 5, comment: "...", ticket_id: "..." }
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    rating = data.get('rating', 5)
    comment = (data.get('comment') or '').strip()
    ticket_id = data.get('ticket_id')

    user_ident = request.user.username if request.user.is_authenticated else "anonymous"

    success = log_feedback(
        user_identifier=user_ident,
        rating=int(rating),
        comment=comment,
        related_ticket_id=ticket_id
    )

    return JsonResponse({
        'success': success,
        'storage': 'MongoDB (beats.feedback)',
        'message': 'Thank you! Your feedback has been recorded.'
    })


# ── Assessment Requirement: Health Check Page ─────────────────────────────────

def health_check_view(request):
    """
    Assessment Requirement: Request logging and health check page.
    Monitors database connectivity, upstream API latency, and MongoDB status.
    """
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "service": "Beats Music Platform & AI Assistant",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }

    # 1. SQL Database Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        health_status["checks"]["sql_database"] = {
            "status": "UP",
            "engine": connection.settings_dict.get('ENGINE', 'sqlite3').split('.')[-1],
            "total_songs": Song.objects.count(),
            "total_faqs": FAQ.objects.count(),
            "total_error_codes": ErrorCode.objects.count(),
            "total_tickets": SupportTicket.objects.count()
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["sql_database"] = {
            "status": "DOWN",
            "error": str(e)
        }

    # 2. Third-Party Weather/Vibe API Check (with strict timeout)
    third_party_result = get_listening_weather_and_vibe()
    health_status["checks"]["third_party_api"] = {
        "status": "UP" if not third_party_result.get("fallback_used") else "FALLBACK",
        "provider": third_party_result.get("provider"),
        "latency_ms": third_party_result.get("latency_ms", 0),
        "ambient_mood": third_party_result.get("ambient_mood")
    }

    # 3. MongoDB Connectivity Check
    mongo_up = is_mongo_connected()
    health_status["checks"]["mongodb_storage"] = {
        "status": "CONNECTED" if mongo_up else "FALLBACK_BUFFER",
        "description": "MongoDB chat_logs and feedback collection storage"
    }

    # 4. Request Logging Metrics
    recent_requests = list(RECENT_REQUESTS_LOG)
    health_status["checks"]["request_logging"] = {
        "status": "ACTIVE",
        "buffered_requests_count": len(recent_requests),
        "recent_requests_sample": recent_requests[-5:] if recent_requests else []
    }

    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

    return JsonResponse(health_status, status=200 if health_status["status"] == "healthy" else 503)


# ── AI Recommendations & Assistant API Endpoint ────────────────────────────────

@require_POST
def api_recommendations(request):
    """
    Assessment Requirement: AI assistant answering from FAQ, explaining error codes,
    and creating a support ticket when it cannot answer.
    Logs chat to MongoDB automatically.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    prompt = (data.get('prompt') or '').strip()
    user_api_key = (data.get('api_key') or '').strip()

    if not prompt:
        return JsonResponse({'error': 'Please provide a prompt or question.'}, status=400)

    user_ident = request.user.username if request.user.is_authenticated else "guest"

    try:
        # Call Gemini assistant (with local knowledge base fallback)
        res_data = get_assistant_response(
            prompt,
            user_api_key=user_api_key,
            user_identifier=user_ident
        )

        # Cross-reference recommended songs with database
        rec_list = res_data.get('recommendations', [])
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

        # Check if assistant escalated to a Support Ticket in SQL
        if res_data.get('ticket_required'):
            ticket_subj = res_data.get('ticket_subject') or prompt[:50]
            ticket_msg = res_data.get('ticket_message') or prompt
            email = request.user.email if request.user.is_authenticated and request.user.email else "guest@beats.fm"

            ticket = SupportTicket.objects.create(
                user=request.user if request.user.is_authenticated else None,
                email=email,
                subject=f"[AI Escalated] {ticket_subj}",
                message=ticket_msg,
                source='AI_ASSISTANT',
                status='OPEN'
            )
            res_data['created_ticket_id'] = ticket.ticket_id
            res_data['ticket_notice'] = f"Support ticket #{ticket.ticket_id} has been opened in our SQL database. Reference this code for assistance."

        return JsonResponse({
            'success': True,
            'data': res_data
        })
    except Exception as e:
        logger.exception("Error in api_recommendations: %s", e)
        return JsonResponse({'error': f"AI service notice: {str(e)}"}, status=500)


# ── Quick Add from Recommendation API ──────────────────────────────────────────

@require_POST
def api_quick_add(request):
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

    valid_genres = dict(Song.GENRE_CHOICES).keys()
    if genre not in valid_genres:
        genre = 'other'

    try:
        release_year = int(year) if year else None
    except (ValueError, TypeError):
        release_year = None

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


# ── Assessment Requirement: Custom 404 & 500 Handlers ─────────────────────────

def custom_404_view(request, exception=None):
    """Custom 404 page with 'Ask the assistant' option."""
    error_obj = ErrorCode.objects.filter(code='404').first()
    return render(request, '404.html', {
        'error_obj': error_obj,
        'requested_path': request.path,
    }, status=404)


def custom_500_view(request):
    """Custom 500 page with 'Ask the assistant' option."""
    error_obj = ErrorCode.objects.filter(code='500').first()
    return render(request, '500.html', {
        'error_obj': error_obj,
    }, status=500)


# ── Auth Views ─────────────────────────────────────────────────────────────────

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
