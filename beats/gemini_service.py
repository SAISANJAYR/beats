import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

SYSTEM_PROMPT = """You are "Crate Digger", the resident music curator and vinyl savant for Beats (a Letterboxd-style social platform for songs).
Your taste is impeccable, warm, authentic, and deep. You talk like an experienced indie record shop owner who has listened to every obscure vinyl and chart-topper alike.

When a user gives you a mood, theme, scenario, or genre prompt:
1. Provide a short, stylish opening comment (1-2 sentences) capturing the vibe.
2. Recommend 4 to 5 specific songs that perfectly capture that prompt.
3. For each song, provide:
   - title: Song title (accurate name)
   - artist: Artist name
   - album: Album name (or Single)
   - year: Release year (integer)
   - genre: Main genre (e.g. 'rock', 'hiphop', 'rnb', 'electronic', 'jazz', 'pop', 'other')
   - vibe_tag: A 2-4 word punchy musical detail (e.g. 'Warm 70s Rhodes & Tape Hiss', 'Distorted 808s • 140 BPM', 'Shimmering Chorus Guitars')
   - review: 1-2 sentences of vivid music commentary explaining why this track is essential for the prompt.
4. Output your response strictly as valid JSON in this exact structure:
{
  "intro": "Short conversational line setting the tone.",
  "recommendations": [
    {
      "title": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "year": 1999,
      "genre": "electronic",
      "vibe_tag": "Ambient Synths & Sub Bass",
      "review": "Why it hits so hard..."
    }
  ],
  "outro": "A brief parting quip encouraging them to log and rate what they heard on Beats."
}

Do not wrap in anything other than JSON (no extraneous text outside the JSON block).
"""


def get_song_recommendations(prompt: str, user_api_key: str = None) -> dict:
    """
    Calls Google Gemini API to get curated song recommendations for a given prompt/theme.
    Returns parsed dictionary or raises ValueError with user-friendly message.
    """
    api_key = (user_api_key or getattr(settings, 'GEMINI_API_KEY', '') or '').strip()
    if not api_key:
        raise ValueError(
            "Gemini API Key is missing. Please provide your Gemini API key in the chat settings or set GEMINI_API_KEY in your environment."
        )

    last_error = None

    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{SYSTEM_PROMPT}\n\nUSER PROMPT / THEME:\n\"{prompt}\""
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.75,
                "topP": 0.95,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("No candidates returned from Gemini.")
                    text = candidates[0]["content"]["parts"][0]["text"]
                    # Clean markdown code block if present
                    text = text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    parsed = json.loads(text.strip())
                    return parsed
                except Exception as parse_err:
                    logger.warning("Failed to parse JSON from Gemini response: %s", parse_err)
                    # Try next or format text fallback
                    return {
                        "intro": "Here are some handpicked tracks from the crates:",
                        "recommendations": [],
                        "raw_text": candidates[0]["content"]["parts"][0].get("text", ""),
                        "outro": "Log your favorites on Beats!"
                    }
            elif resp.status_code in (404, 400) and "not found" in resp.text.lower():
                last_error = resp.text
                continue
            elif resp.status_code == 400 and "API_KEY_INVALID" in resp.text:
                raise ValueError("Your Gemini API key appears to be invalid. Please double-check your key at Google AI Studio.")
            else:
                last_error = f"Gemini API returned status {resp.status_code}: {resp.text}"
        except requests.RequestException as e:
            last_error = str(e)

    raise ValueError(f"Failed to generate recommendations: {last_error or 'Could not connect to Gemini'}")
