from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from beats.models import Song, Rating, FAQ, ErrorCode, SupportTicket

SAMPLE_SONGS = [
    {
        "title": "Dreams",
        "artist": "Fleetwood Mac",
        "album": "Rumours",
        "genre": "rock",
        "release_year": 1977,
        "cover_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 5.0, "liked": True, "review": "Stevie Nicks at her peak. The bassline and groove are timeless."},
            {"score": 4.5, "liked": True, "review": "One of the greatest vinyl records ever pressed. Pure magic."},
        ]
    },
    {
        "title": "Get Lucky",
        "artist": "Daft Punk ft. Pharrell Williams",
        "album": "Random Access Memories",
        "genre": "electronic",
        "release_year": 2013,
        "cover_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 4.5, "liked": True, "review": "Nile Rodgers' funk guitar riff makes it impossible not to move."},
            {"score": 5.0, "liked": True, "review": "A modern disco masterpiece. Instant 5 stars."},
        ]
    },
    {
        "title": "Money Trees",
        "artist": "Kendrick Lamar ft. Jay Rock",
        "album": "good kid, m.A.A.d city",
        "genre": "hiphop",
        "release_year": 2012,
        "cover_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 5.0, "liked": True, "review": "Silver soul sample reversed, Jay Rock's verse is legendary."},
            {"score": 4.5, "liked": True, "review": "The epitome of 2010s West Coast hip-hop storytelling."},
        ]
    },
    {
        "title": "Midnight City",
        "artist": "M83",
        "album": "Hurry Up, We're Dreaming",
        "genre": "electronic",
        "release_year": 2011,
        "cover_url": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 5.0, "liked": True, "review": "That iconic sax solo in the outro sends chills every single time."},
        ]
    },
    {
        "title": "Redbone",
        "artist": "Childish Gambino",
        "album": "\"Awaken, My Love!\"",
        "genre": "rnb",
        "release_year": 2016,
        "cover_url": "https://images.unsplash.com/photo-1487180144351-b8472da7d491?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 4.5, "liked": True, "review": "Funkadelic-inspired soul brilliance. The falsetto is outrageous."},
        ]
    },
    {
        "title": "Paranoid Android",
        "artist": "Radiohead",
        "album": "OK Computer",
        "genre": "rock",
        "release_year": 1997,
        "cover_url": "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 5.0, "liked": True, "review": "The Bohemian Rhapsody of the 90s alternative rock era."},
        ]
    },
    {
        "title": "So What",
        "artist": "Miles Davis",
        "album": "Kind of Blue",
        "genre": "jazz",
        "release_year": 1959,
        "cover_url": "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 5.0, "liked": True, "review": "Modal jazz perfection. Paul Chambers' opening bass motif is church."},
        ]
    },
    {
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "album": "After Hours",
        "genre": "pop",
        "release_year": 2020,
        "cover_url": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=600&auto=format&fit=crop&q=80",
        "ratings": [
            {"score": 4.0, "liked": True, "review": "Unbeatable 80s synth-pop revival energy."},
        ]
    }
]

# ── Minimum 10 FAQs for SQL Database ─────────────────────────────────────────

FAQS_DATA = [
    {
        "category": "general",
        "order": 1,
        "question": "What is Beats?",
        "answer": "Beats is a Letterboxd-style social diary for music lovers. It allows listeners to log songs they listen to, assign ratings with half-star precision (0.5 to 5.0), write album reviews, and discover new tracks with the AI-powered Crate Digger assistant."
    },
    {
        "category": "ratings",
        "order": 2,
        "question": "How does the half-star rating system work?",
        "answer": "You can rate any song from 0.5 stars (½ ★) to 5.0 stars (★★★★★) in 0.5 increments. You can also heart/like tracks you love and write an optional in-depth review that appears on the public community diary feed."
    },
    {
        "category": "ai",
        "order": 3,
        "question": "What is the Crate Digger AI assistant?",
        "answer": "Crate Digger is our integrated AI music curator powered by Google Gemini. You can describe any vibe, emotion, cinema scene, or era (e.g. 'Late night rainy drive synthwave'), and Crate Digger unearths 4-5 curated vinyl tracks with musical details and 1-click addition to your diary."
    },
    {
        "category": "ai",
        "order": 4,
        "question": "Can the AI assistant explain HTTP and site error codes?",
        "answer": "Yes! The assistant has deep knowledge of all standard HTTP error codes (400, 401, 403, 404, 429, 500, 503) and our site-specific code BEATS-444. Just ask 'Explain error 404' or click the 'Ask Assistant' button on any error page."
    },
    {
        "category": "ai",
        "order": 5,
        "question": "What happens if the AI assistant cannot answer my question?",
        "answer": "When the assistant encounters an issue beyond its knowledge base or when you request human help, it automatically opens an official Support Ticket stored in our SQL database and gives you a tracking reference ID (e.g. #BEATS-12345)."
    },
    {
        "category": "general",
        "order": 6,
        "question": "How do I log and add a new song to the crate?",
        "answer": "Click the '+ Log Track' button in the navigation header, fill in the track title, artist name, optional album, genre, release year, and album cover image URL, then click '+ Add to Crate'."
    },
    {
        "category": "ratings",
        "order": 7,
        "question": "Can I edit or delete my rating after submitting?",
        "answer": "Yes. Navigate to the song's detail page. If you have already logged the track, you will see 'Edit Log' and 'Remove' buttons under your diary entry on the right-hand panel."
    },
    {
        "category": "account",
        "order": 8,
        "question": "Do I need an account to browse tracks and use the AI?",
        "answer": "Browsing tracks, viewing listener reviews, and searching the crate are completely free and open to everyone without an account. An account is only required to log ratings to your personal profile or press new songs into the crate."
    },
    {
        "category": "troubleshooting",
        "order": 9,
        "question": "Where are support tickets and chat logs stored?",
        "answer": "Support tickets are stored reliably in the relational SQL database (SQLite/PostgreSQL) for transactional integrity, while chat conversations, session interactions, and user feedback are archived into MongoDB."
    },
    {
        "category": "troubleshooting",
        "order": 10,
        "question": "How does the system ensure high availability and monitor health?",
        "answer": "Beats includes an automated request logging middleware and a dedicated /health/ endpoint that monitors database connectivity, third-party API latency, and uptime in real-time."
    },
    {
        "category": "troubleshooting",
        "order": 11,
        "question": "What third-party APIs are integrated into Beats?",
        "answer": "Beats integrates the Google Gemini API for natural language curation and error diagnostics, along with an external Live Audio Vibe & Weather API that features a strict 2.0-second timeout with an automatic fallback mechanism."
    }
]

# ── Minimum 8 Error Codes for SQL Database ───────────────────────────────────

ERROR_CODES_DATA = [
    {
        "code": "400",
        "name": "Bad Request",
        "order": 1,
        "explanation": "The server cannot process the request due to malformed syntax, invalid JSON payload, or missing required fields in the request.",
        "solution": "Verify that all required form parameters (like song title and artist) are provided and that form inputs adhere to the expected format.",
        "is_site_specific": False
    },
    {
        "code": "401",
        "name": "Unauthorized",
        "order": 2,
        "explanation": "Authentication is required and has failed or has not yet been provided to access the requested resource.",
        "solution": "Sign in with your Beats username and password. If you do not have an account, click 'Create Account' in the top right.",
        "is_site_specific": False
    },
    {
        "code": "403",
        "name": "Forbidden",
        "order": 3,
        "explanation": "The server understands the request but refuses to authorize it. You do not have permissions to access or modify this resource.",
        "solution": "Ensure you are trying to edit or delete your own ratings or support tickets, not another listener's private entries.",
        "is_site_specific": False
    },
    {
        "code": "404",
        "name": "Not Found",
        "order": 4,
        "explanation": "The requested track, album, review, or webpage could not be found on the server. The URL may be misspelled or the item was removed.",
        "solution": "Check the URL for typographical errors, browse the Crate using the search bar, or ask Crate Digger AI to find the song for you.",
        "is_site_specific": False
    },
    {
        "code": "429",
        "name": "Too Many Requests",
        "order": 5,
        "explanation": "You have sent too many requests in a given amount of time (rate limit exceeded), usually triggered by excessive AI recommendation queries.",
        "solution": "Pause for 30 to 60 seconds before submitting another prompt to allow the rate limiter window to reset.",
        "is_site_specific": False
    },
    {
        "code": "500",
        "name": "Internal Server Error",
        "order": 6,
        "explanation": "The server encountered an unexpected condition that prevented it from fulfilling the request. This indicates an unhandled server-side exception.",
        "solution": "Refresh the page after a few moments. If the problem persists, click 'Ask the assistant' on the 500 page to automatically log a support ticket.",
        "is_site_specific": False
    },
    {
        "code": "503",
        "name": "Service Unavailable",
        "order": 7,
        "explanation": "The server is currently unable to handle the request due to a temporary overloading or maintenance of upstream services (e.g. Gemini AI or database).",
        "solution": "The system automatically engages offline fallback recommendations. Wait 1-2 minutes and re-try your request.",
        "is_site_specific": False
    },
    {
        "code": "BEATS-444",
        "name": "Needle Scratch: Track Missing From Crate",
        "order": 8,
        "explanation": "Site-specific error: The vinyl turntable tonearm dropped into an empty groove because the queried song ID exists neither in our local vinyl crate nor in the streaming cache.",
        "solution": "Use our '+ Log Track' feature to add this song to the crate yourself, or prompt Crate Digger AI to curate and import it with one click.",
        "is_site_specific": True
    }
]


class Command(BaseCommand):
    help = "Seed database with songs, reviews, FAQs, error codes, and support tickets"

    def handle(self, *args, **options):
        # 1. Curator & Test Users
        curator, _ = User.objects.get_or_create(
            username="crate_curator",
            defaults={"email": "curator@beats.fm", "is_staff": True}
        )
        if _:
            curator.set_password("beats1234")
            curator.save()

        user2, _ = User.objects.get_or_create(
            username="vinyl_junkie",
            defaults={"email": "vinyl@beats.fm"}
        )
        if _:
            user2.set_password("beats1234")
            user2.save()

        users = [curator, user2]

        # 2. Seed Songs & Ratings
        song_count = 0
        for data in SAMPLE_SONGS:
            song, created = Song.objects.get_or_create(
                title=data["title"],
                artist=data["artist"],
                defaults={
                    "album": data["album"],
                    "genre": data["genre"],
                    "release_year": data["release_year"],
                    "cover_url": data["cover_url"],
                    "added_by": curator,
                }
            )
            if created:
                song_count += 1
            for i, rdata in enumerate(data.get("ratings", [])):
                reviewer = users[i % len(users)]
                Rating.objects.get_or_create(
                    song=song,
                    user=reviewer,
                    defaults={
                        "score": rdata["score"],
                        "liked": rdata["liked"],
                        "review": rdata["review"],
                    }
                )

        # 3. Seed FAQs
        faq_count = 0
        for item in FAQS_DATA:
            faq, created = FAQ.objects.get_or_create(
                question=item["question"],
                defaults={
                    "answer": item["answer"],
                    "category": item["category"],
                    "order": item["order"],
                }
            )
            if created:
                faq_count += 1

        # 4. Seed Error Codes
        err_count = 0
        for item in ERROR_CODES_DATA:
            code_obj, created = ErrorCode.objects.get_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "explanation": item["explanation"],
                    "solution": item["solution"],
                    "is_site_specific": item["is_site_specific"],
                    "order": item["order"],
                }
            )
            if created:
                err_count += 1

        # 5. Seed Initial Support Ticket
        ticket, _ = SupportTicket.objects.get_or_create(
            ticket_id="BEATS-10001",
            defaults={
                "email": "listener@example.com",
                "subject": "Audio waveform visualizer query on mobile",
                "message": "The equalizer visualizer works great on desktop, testing responsiveness on mobile devices.",
                "source": "AI_ASSISTANT",
                "status": "RESOLVED",
                "resolution_notes": "Verified responsive CSS media query for mobile viewports."
            }
        )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded: {song_count} songs, {faq_count} FAQs, {err_count} Error Codes, and sample support ticket!"
        ))
