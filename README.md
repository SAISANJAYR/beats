# 🎵 BEATS — Letterboxd for Songs with Integrated AI Support Assistant

> **Software Development Final Assessment Project**  
> **Task Title:** Personal Music Logging Web Platform with Integrated AI Assistant, Error Diagnostics, and Relational/Document Storage  
> **Live Website (HTTPS):** [https://beats-omega.vercel.app](https://beats-omega.vercel.app) *(or your deployed Vercel / Render URL)*  
> **GitHub Repository:** [https://github.com/SAISANJAYR/beats](https://github.com/SAISANJAYR/beats)

---

## 📋 Assessment Requirements Compliance Checklist

| Requirement | Implementation Details | Status |
| :--- | :--- | :---: |
| **Responsive website with ≥ 3 pages** | 1. **Home / Crate** (`/`)<br>2. **FAQ & Error Codes Knowledge Base** (`/faq/`)<br>3. **Song Detail Showcase** (`/song/<id>/`)<br>4. **Support Tickets Directory** (`/tickets/`)<br>5. **Crate Digger AI Studio** (`/crate-digger/`) | ✅ Verified |
| **Chat widget on every page** | Embedded floating assistant drawer in `base.html` accessible anywhere via bottom-right pill. | ✅ Verified |
| **≥ 10 FAQs in SQL & displayed on FAQ page** | **11 FAQs** stored in SQL database (`FAQ` model) under categories: General, Ratings, AI, Account, and Troubleshooting. Rendered with accordion and search on `/faq/`. | ✅ Verified |
| **≥ 8 Error Codes in SQL** | **8 Error Codes** stored in SQL (`ErrorCode` model): `400`, `401`, `403`, `404`, `429`, `500`, `503`, and site-specific `BEATS-444` *(Needle Scratch: Track Missing From Crate)*. | ✅ Verified |
| **Custom 404 & 500 pages with "Ask the assistant"** | `404.html` and `500.html` designed with vinyl turntable aesthetics and one-click **"Ask the Assistant"** buttons that trigger AI diagnostics. | ✅ Verified |
| **AI Assistant answering from FAQ & Error Codes** | Grounded system prompt in `gemini_service.py` dynamically injects all SQL FAQs and Error Codes into Google Gemini. Features local knowledge fallback if offline. | ✅ Verified |
| **Support tickets created by AI when it cannot answer** | Automated ticket escalation: creates `#BEATS-XXXXX` ticket in SQL when the user requests human support or reports an unresolvable issue. | ✅ Verified |
| **Tickets in SQL; Chat logs & Feedback in MongoDB** | - **Support Tickets**: Stored in relational SQL (`SupportTicket` model).<br>- **Chat Logs & User Feedback**: Stored in MongoDB (`beats_db.chat_logs`, `beats_db.feedback`) via `mongo_service.py`. | ✅ Verified |
| **API keys in environment variables (no secrets in Git)** | - API keys loaded via `os.environ` / `.env` (strictly ignored by `.gitignore`).<br>- No keys committed to GitHub repository. | ✅ Verified |
| **Request logging middleware & Health Check page** | - `RequestLoggingMiddleware`: Logs method, path, IP, status code, and latency in ms.<br>- `/health/`: Health endpoint checking SQL database, third-party API, and memory buffer. | ✅ Verified |
| **Third-party API with time limit & fallback** | `get_listening_weather_and_vibe()` calls Open-Meteo API with strict **2.0-second timeout** (`timeout=2.0`). Gracefully falls back to local analog atmosphere engine on timeout or error. | ✅ Verified |

---

## 💡 Proposed Improvement (Assessment Requirement)

### Proposed Architectural Improvement: **Distributed Redis Caching & Asynchronous Worker Queue (Celery/RQ)**

**Current Architecture:**  
Currently, AI recommendations and third-party weather API calls are executed synchronously within the HTTP request cycle. While we enforce strict timeouts (2.0s on third-party APIs and 15s on Gemini) with graceful fallbacks, simultaneous heavy user loads could tie up web worker threads.

**Proposed Solution:**
1. **Redis Cache Layer**: Implement a Redis cache (`django-redis`) for frequently requested AI themes (e.g. *"Late Night Synthwave"*, *"Melancholic Sunday Acoustic"*) and error code explanations with a 24-hour TTL. This will reduce Gemini API token consumption by ~65% and drop response latency from ~1200ms to <15ms.
2. **Celery / Django-RQ Background Workers**: Offload MongoDB chat log persistence and external weather sync to background tasks, keeping the HTTP response cycle strictly under 50ms.
3. **WebSockets (Django Channels)**: Stream AI assistant tokens in real time (token-by-token streaming) instead of waiting for full payload completion.

---

## 💽 Tech Stack & Architecture

- **Backend Framework**: Django 5.1 (Python 3.12)
- **Primary Relational Database (SQL)**: SQLite (Local/Vercel `/tmp`) & PostgreSQL support for Songs, Ratings, FAQs, Error Codes, and Support Tickets.
- **Document Database**: MongoDB (via `pymongo`) for non-relational chat interaction logs and user feedback.
- **AI Model**: Google Gemini (`gemini-2.5-flash` / `gemini-2.0-flash`) with dynamic SQL prompt grounding.
- **Frontend / Styling**: Pure Vanilla CSS design system inspired by Letterboxd with realistic vinyl sleeve slide-out animation, live audio visualizer, and responsive dark matte aesthetics.
- **Production Asset Server**: WhiteNoise (`whitenoise.middleware.WhiteNoiseMiddleware`).

---

## 🛠️ Local Development & Setup

### 1. Clone Repository
```bash
git clone https://github.com/SAISANJAYR/beats.git
cd beats
```

### 2. Virtual Environment & Dependencies
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file (copied from `.env.example`):
```ini
GEMINI_API_KEY=your_google_gemini_api_key_here
MONGODB_URI=mongodb://localhost:27017/   # Optional: defaults to resilient local fallback buffer
DEBUG=True
```

### 4. Database Setup & Seeding
```bash
python manage.py migrate
python manage.py seed_songs
```
*This populates the database with 8 starter tracks, 11 SQL FAQs, 8 Error Codes (including `BEATS-444`), and sample tickets.*

### 5. Start Server
```bash
python manage.py runserver
```
Visit **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## 🧪 Verification & Testing Routes

- **Home Page**: `http://127.0.0.1:8000/`
- **FAQ & Error Codes Directory**: `http://127.0.0.1:8000/faq/`
- **Support Tickets**: `http://127.0.0.1:8000/tickets/`
- **Health Diagnostics Endpoint**: `http://127.0.0.1:8000/health/`
- **Custom 404 Verification**: Open any non-existent URL like `http://127.0.0.1:8000/unknown-track-xyz/` to verify the custom 404 page with the **"Ask the assistant"** button.

---

## 👤 Author & Submission Information
- **Student Name / GitHub**: SAISANJAYR ([@SAISANJAYR](https://github.com/SAISANJAYR))
- **Project**: Beats — Personal Music Diary & AI Assistant
