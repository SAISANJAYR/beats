import os
import json
import logging
import requests
from django.conf import settings
from .mongo_service import log_chat_interaction

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def build_system_context():
    """
    Dynamically loads all FAQs and ErrorCodes from the SQL database
    to provide authoritative context to the AI assistant.
    """
    from .models import FAQ, ErrorCode

    faq_snippets = []
    try:
        for f in FAQ.objects.all().order_by('order'):
            faq_snippets.append(f"Q: {f.question}\nA: {f.answer}")
    except Exception as e:
        logger.warning("Could not load FAQs for AI context: %s", e)

    error_snippets = []
    try:
        for err in ErrorCode.objects.all().order_by('order'):
            site_tag = "[Site-Specific]" if err.is_site_specific else "[HTTP Standard]"
            error_snippets.append(
                f"Code: {err.code} ({err.name}) {site_tag}\n"
                f"Explanation: {err.explanation}\n"
                f"Resolution: {err.solution}"
            )
    except Exception as e:
        logger.warning("Could not load ErrorCodes for AI context: %s", e)

    faq_text = "\n\n".join(faq_snippets)
    error_text = "\n\n".join(error_snippets)

    system_prompt = f"""You are "Crate Digger", the AI assistant and resident music savant for Beats (a Letterboxd-style social diary for music and songs).

Your responsibilities:
1. SONG RECOMMENDATIONS: When asked for music recommendations based on a theme, mood, scene, or genre, recommend 3-5 curated tracks with titles, artists, albums, release years, vibe tags, and vivid music criticism notes.
2. FAQ & PLATFORM SUPPORT: Answer questions about Beats using the knowledge base below.
3. ERROR CODE EXPLANATIONS: Accurately explain standard HTTP error codes (400, 401, 403, 404, 429, 500, 503) and our site-specific code BEATS-444 using the error dictionary below.
4. SUPPORT TICKET ESCALATION: If the user has an account issue, bug report, asks for human support, or if you cannot answer their request, set "ticket_required": true with a suggested subject and summary so an official SQL Support Ticket can be created.

=== SQL FAQ KNOWLEDGE BASE ===
{faq_text}

=== SQL ERROR CODES DIRECTORY ===
{error_text}

=== RESPONSE FORMAT ===
Always return your response strictly as valid JSON matching this schema:
{{
  "intro": "Conversational, stylish opening remark (1-2 sentences)",
  "text_response": "Clear explanation of the question, error code, or topic (if applicable)",
  "recommendations": [
    {{
      "title": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "year": 1999,
      "genre": "rock",
      "vibe_tag": "Analog Tape & 90s Crunch",
      "review": "Brief note on why it fits the vibe..."
    }}
  ],
  "ticket_required": false,
  "ticket_subject": null,
  "ticket_message": null,
  "outro": "Friendly closing note."
}}
"""
    return system_prompt


def get_assistant_response(prompt: str, user_api_key: str = None, user_identifier: str = "guest") -> dict:
    """
    Calls Google Gemini with the grounded SQL knowledge base.
    Auto-detects API key from environment (zero user friction).
    Falls back gracefully if the API is unreachable or key is missing.
    """
    # Prefer server environment variable first, then settings, then client
    api_key = (
        os.environ.get("GEMINI_API_KEY") or
        getattr(settings, "GEMINI_API_KEY", "") or
        os.environ.get("GOOGLE_API_KEY") or
        user_api_key or
        ""
    ).strip()

    # If no key configured, engage our local semantic rule-based assistant
    if not api_key:
        logger.info("No Gemini API key set; using built-in knowledge base assistant.")
        fallback_resp = generate_local_knowledge_response(prompt)
        log_chat_interaction(user_identifier, prompt, fallback_resp, model_used="local-knowledge-engine")
        return fallback_resp

    system_prompt = build_system_context()
    last_error = None

    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nUSER QUERY:\n\"{prompt}\""}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    continue

                text = candidates[0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]

                parsed = json.loads(text.strip())

                # Log into MongoDB
                log_chat_interaction(user_identifier, prompt, parsed, model_used=model_name)
                return parsed

            elif resp.status_code in (404, 400) and "not found" in resp.text.lower():
                last_error = resp.text
                continue
            else:
                last_error = f"Gemini status {resp.status_code}: {resp.text}"
        except Exception as e:
            last_error = str(e)
            logger.warning("Gemini model %s error: %s", model_name, e)

    # If all upstream models failed, use local knowledge base fallback so user never gets broken UX
    logger.warning("Falling back to local knowledge base after Gemini failure: %s", last_error)
    fallback_resp = generate_local_knowledge_response(prompt)
    log_chat_interaction(user_identifier, prompt, fallback_resp, model_used="local-fallback-engine")
    return fallback_resp


def generate_local_knowledge_response(prompt: str) -> dict:
    """
    Local knowledge engine: parses FAQs, Error Codes, and prompts directly
    from the SQL database when Gemini is offline or unconfigured.
    """
    from .models import FAQ, ErrorCode
    p_lower = prompt.lower()

    # 1. Check for error code query (e.g. 404, 500, beats-444, "error 429")
    for err in ErrorCode.objects.all():
        if err.code.lower() in p_lower or err.name.lower() in p_lower:
            return {
                "intro": f"Here is the breakdown for error {err.code}:",
                "text_response": f"**{err.code} — {err.name}**\n\n**What it means:** {err.explanation}\n\n**How to resolve it:** {err.solution}",
                "recommendations": [],
                "ticket_required": False,
                "outro": "Need more help with this error? Just reply 'open a support ticket'."
            }

    # 2. Check for FAQ match
    for faq in FAQ.objects.all():
        words = [w for w in faq.question.lower().split() if len(w) > 3]
        if any(w in p_lower for w in words):
            return {
                "intro": "I found an answer in the Beats Knowledge Base:",
                "text_response": f"**Q: {faq.question}**\n\n{faq.answer}",
                "recommendations": [],
                "ticket_required": False,
                "outro": "Let me know if you need any additional clarification!"
            }

    # 3. Check for support ticket request
    if any(k in p_lower for k in ["ticket", "support", "help", "human", "contact", "bug", "broken", "locked"]):
        return {
            "intro": "I can certainly create an official support ticket for you.",
            "text_response": "I've flagged this for our support team. An official support ticket will be generated in our SQL database.",
            "recommendations": [],
            "ticket_required": True,
            "ticket_subject": prompt[:60],
            "ticket_message": prompt,
            "outro": "Your support ticket reference will be saved to your dashboard."
        }

    # 4. Default Music Curation response
    return {
        "intro": "Here are some classic selections from the Beats vinyl vault:",
        "text_response": "I've matched your request against our offline curated vinyl collection.",
        "recommendations": [
            {
                "title": "Dreams",
                "artist": "Fleetwood Mac",
                "album": "Rumours",
                "year": 1977,
                "genre": "rock",
                "vibe_tag": "Warm 70s Acoustic • Analog Tape",
                "review": "A masterclass in subtle rhythm and acoustic guitars."
            },
            {
                "title": "Get Lucky",
                "artist": "Daft Punk",
                "album": "Random Access Memories",
                "year": 2013,
                "genre": "electronic",
                "vibe_tag": "Disco Funk • Nile Rodgers Riff",
                "review": "Irresistible grooves recorded with state-of-the-art analog gear."
            },
            {
                "title": "So What",
                "artist": "Miles Davis",
                "album": "Kind of Blue",
                "year": 1959,
                "genre": "jazz",
                "vibe_tag": "Modal Jazz • Late Night Mood",
                "review": "The quintessential late-night listening experience."
            }
        ],
        "ticket_required": False,
        "outro": "Log these tracks to your Beats diary or ask about any error code!"
    }


# Backwards compatibility alias
get_song_recommendations = get_assistant_response
