# 🎵 BEATS — Letterboxd for Songs

> **Track songs you love. Log what you listen to. Tell your friends what's good.**  
> A full-stack Django social music platform built with a Letterboxd aesthetic, vinyl culture elements, and an AI-powered Crate Digger assistant powered by **Google Gemini**.

---

## ✨ Features

- **💽 Letterboxd UI + Vinyl Aesthetics**:
  - Deep matte charcoal theme (`#14181c`, `#1b2228`, `#2c3440`).
  - Letterboxd green (`#00e054`) half-star ratings, orange hearts (`❤️`), and cyan metadata.
  - **12" Vinyl Sleeves with Realistic Slide-Out Discs**: Hover over any album card to watch a grooved vinyl record slide out and spin from behind its sleeve.
  - **Live Stereo Equalizer**: Animated bouncing audio visualizer in the header and music cards.
  - **Letterboxd Rating Histogram**: View the community ratings distribution from ½ star to 5 stars.
  - **One-Click Streaming**: Direct `🟢 Listen on Spotify` and `▶️ Watch on YouTube` buttons for every track.
  - **Community Diary Stream**: Live feed of recent reviews, ratings, and music logs.

- **🤖 Crate Digger AI (Gemini Chatbot)**:
  - Curates songs based on any prompt, theme, mood, or cinematic scenario (e.g., *"Late night neon highway drive with heavy synthwave"*, *"70s Japanese funk with a filthy bassline"*).
  - Floating drawer on every page + dedicated full-screen curation studio at `/crate-digger/`.
  - **One-Click "+ Log to Beats"**: Instantly import any AI-recommended track into your crate with a single click.
  - Flexible API key management: Set via `GEMINI_API_KEY` environment variable or directly through the UI key input (saved securely in browser session).

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/SAISANJAYR/beats.git
cd beats
```

### 2. Set up Python environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. Install requirements
```bash
pip install django requests
```

### 4. Configure Gemini API Key (Optional)
You can set your Gemini API key in two ways:
- **Option A (Environment Variable)**:
  Copy `.env.example` to `.env` or set:
  ```bash
  # Windows PowerShell
  $env:GEMINI_API_KEY="your_actual_key_here"
  ```
- **Option B (Directly in Web UI)**:
  Click the **🔑 key icon** inside the Crate Digger AI chatbot in the bottom right corner of the website and paste your key.

Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/app/apikey).

### 5. Run Migrations & Seed Initial Crate
```bash
python manage.py migrate
python manage.py seed_songs
```

### 6. Start the Server
```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser!

---

## 📁 Project Structure

```
beats/
├── manage.py
├── .gitignore
├── .env.example
├── README.md
├── sais_app/               # Django project settings & URLs
│   ├── settings.py
│   └── urls.py
└── beats/                  # Beats app
    ├── models.py           # Song & Rating models
    ├── views.py            # Letterboxd views & AI recommendation endpoints
    ├── forms.py            # Half-star ratings & song forms
    ├── gemini_service.py   # Google Gemini API integration
    ├── urls.py             # App routing
    ├── management/         # Seeding commands
    ├── template/beats/     # Letterboxd HTML templates
    └── static/beats/       # Pure CSS design system & vinyl animations
```

---

## 🔒 Security
- The `.gitignore` is pre-configured to strictly exclude `.env`, `*.key`, `db.sqlite3`, and virtual environments.
- API keys are never hardcoded in source code or pushed to Git.
