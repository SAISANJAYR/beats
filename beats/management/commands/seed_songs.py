from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from beats.models import Song, Rating

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


class Command(BaseCommand):
    help = "Seed database with starter songs and reviews"

    def handle(self, *args, **options):
        # Create curator user if not exists
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

        created_count = 0
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
                created_count += 1
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

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} songs!"))
