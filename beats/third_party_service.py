import time
import logging
import requests

logger = logging.getLogger(__name__)

# Strict time limit for third-party API call (in seconds)
THIRD_PARTY_TIMEOUT = 2.0

# Fallback response if the third-party service times out or fails
DEFAULT_FALLBACK_VIBE = {
    "status": "fallback",
    "fallback_used": True,
    "provider": "Beats Analog Atmosphere Engine (Local Fallback)",
    "ambient_mood": "Late Night Vinyl Warmth",
    "sound_signature": "Warm analog tape saturation with 60 Hz hum",
    "suggested_tempo": "95 - 110 BPM",
    "temperature_c": 21.5,
    "weather_desc": "Cozy Overcast • Ideal for Vinyl Listening",
    "note": "Engaged fallback due to upstream latency or offline mode."
}


def get_listening_weather_and_vibe(lat: float = 40.7128, lon: float = -74.0060) -> dict:
    """
    Assessment Requirement: Third-party API with a time limit and fallback.
    Calls the Open-Meteo Weather API to synchronize listening recommendations with local weather,
    constrained by a strict 2.0s timeout. If timeout or error occurs, smoothly returns fallback.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    start_time = time.time()

    try:
        resp = requests.get(url, timeout=THIRD_PARTY_TIMEOUT)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        if resp.status_code == 200:
            data = resp.json().get("current_weather", {})
            temp = data.get("temperature", 20.0)
            windspeed = data.get("windspeed", 10.0)
            weather_code = data.get("weathercode", 0)

            # Map weather code to musical ambiance
            if weather_code in (0, 1):
                mood = "Sunny & Golden • Upbeat Disco & 70s Funk"
            elif weather_code in (2, 3):
                mood = "Cloudy Chill • Lo-Fi Beats & Ambient Electronic"
            elif weather_code in (51, 53, 55, 61, 63, 65):
                mood = "Rainy Ambiance • Melancholic Indie Folk & Acoustic Jazz"
            else:
                mood = "Atmospheric Fog • 90s Shoegaze & Deep Bass"

            return {
                "status": "success",
                "fallback_used": False,
                "provider": "Open-Meteo Live Meteorology API",
                "ambient_mood": mood,
                "temperature_c": temp,
                "windspeed_kmh": windspeed,
                "weather_code": weather_code,
                "latency_ms": duration_ms,
                "timestamp": data.get("time", "")
            }
        else:
            logger.warning("Third-party weather API returned HTTP %s", resp.status_code)
            fallback = dict(DEFAULT_FALLBACK_VIBE)
            fallback["reason"] = f"HTTP {resp.status_code}"
            fallback["latency_ms"] = duration_ms
            return fallback

    except requests.Timeout:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.warning("Third-party API timed out after %s seconds. Using fallback.", THIRD_PARTY_TIMEOUT)
        fallback = dict(DEFAULT_FALLBACK_VIBE)
        fallback["reason"] = f"Request timed out (exceeded {THIRD_PARTY_TIMEOUT}s limit)"
        fallback["latency_ms"] = duration_ms
        return fallback

    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.warning("Third-party API error (%s). Using fallback.", e)
        fallback = dict(DEFAULT_FALLBACK_VIBE)
        fallback["reason"] = str(e)
        fallback["latency_ms"] = duration_ms
        return fallback
