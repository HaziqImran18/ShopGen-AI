# 🛍️ ShopGen — AI-Powered Conversational Shopping Agent

<div align="center">

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=36&pause=1000&color=14B8A6&center=true&vCenter=true&width=750&lines=ShopGen;AI+Conversational+Shopping+Agent;WhatsApp+%2B+LLM+%2B+RL+Personalization;Built+for+Pakistani+Shoppers+%F0%9F%87%B5%F0%9F%87%B0" alt="Typing SVG" />
</p>

<br/>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-4.1.0-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/LangGraph-Agentic_Workflow-FF6F61?style=for-the-badge&logo=langchain&logoColor=white"/>
  <img src="https://img.shields.io/badge/LLM-gpt--4o--mini-0EA5E9?style=for-the-badge&logo=openai&logoColor=white"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Firebase-Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black"/>
  <img src="https://img.shields.io/badge/WhatsApp-Whapi.Cloud-25D366?style=for-the-badge&logo=whatsapp&logoColor=white"/>
  <img src="https://img.shields.io/badge/SerpAPI-Google_Shopping-4285F4?style=for-the-badge&logo=google&logoColor=white"/>
  <img src="https://img.shields.io/badge/Whisper-STT-412991?style=for-the-badge&logo=openai&logoColor=white"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Reinforcement_Learning-UCB_Bandit-8B5CF6?style=for-the-badge&logo=probot&logoColor=white"/>
  <img src="https://img.shields.io/badge/Roman_Urdu_Support-✅-14B8A6?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Final_Year-Project_2026-0369A1?style=for-the-badge&logo=bookstack&logoColor=white"/>
  <img src="https://img.shields.io/badge/Made_in-Pakistan_🇵🇰-14B8A6?style=for-the-badge"/>
</p>

<br/>

<blockquote>
<strong>🛍️ ShopGen</strong> is an AI-powered conversational shopping assistant that turns WhatsApp into a full e-commerce experience. Users simply <em>type or speak</em> what they want — <em>"women lawn suits under 5000"</em> or <em>"casual shoes dikhao"</em> — and ShopGen searches live Google Shopping results, re-ranks them with a reinforcement learning personalization engine, and replies with product links, images, outfit suggestions, and even a simulated auto-order page. No app to install. No complex navigation. Just chat.
</blockquote>

<br/>

[![Add](https://img.shields.io/badge/Chat_on-WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](#)
[![Thesis](https://img.shields.io/badge/Read-Final_Thesis-0EA5E9?style=for-the-badge&logo=adobeacrobatreader&logoColor=white)](#)

---

</div>

## 📌 Table of Contents

- [🌟 Project Overview](#-project-overview)
- [🎯 Problem Statement](#-problem-statement)
- [🚀 Features](#-features)
- [🧠 AI Engine — How It Works](#-ai-engine--how-it-works)
- [🗂️ Project Structure](#️-project-structure)
- [⚙️ Tech Stack](#️-tech-stack)
- [🔄 LangGraph Agent Workflow](#-langgraph-agent-workflow)
- [🎤 Voice & Multilingual Support](#-voice--multilingual-support)
- [🏆 Reinforcement Learning Personalization](#-reinforcement-learning-personalization)
- [🗄️ Database Design (Firestore)](#️-database-design-firestore)
- [🔗 Tracking & Analytics](#-tracking--analytics)
- [🛠️ Installation & Setup](#️-installation--setup)
- [📁 Environment Configuration](#-environment-configuration)
- [🧩 Module Architecture](#-module-architecture)
- [🧪 Testing](#-testing)
- [👨‍💻 Authors](#-authors)

---

## 🌟 Project Overview

**ShopGen** is a full-stack, AI-powered conversational shopping agent built as a Final Year Project for the Bachelor of Science in Artificial Intelligence at **Khwaja Fareed University of Engineering & Information Technology, Rahim Yar Khan**.

Instead of forcing users through complex e-commerce websites with dozens of filters and pages, ShopGen transforms WhatsApp — a platform already installed on nearly every smartphone in Pakistan — into an intelligent shopping concierge. Users interact naturally in **English, Urdu, or Roman Urdu**, and the system:

- 🔍 Understands natural language queries (`"kurtis under 3000"`)
- 🛒 Searches **live Google Shopping results** via SerpAPI
- 🧠 Re-ranks products using a **UCB-based reinforcement learning** engine
- 🎤 Accepts **voice notes** (transcribed via OpenAI Whisper)
- 👗 Generates **AI fashion advice** and **outfit pairings**
- 🔗 Creates **trackable short links** for every product shown
- 📦 Generates **simulated auto-order pages** for thesis demonstration
- 💾 Persists every interaction to **Firebase Firestore** for personalization

The system runs entirely on WhatsApp with no separate mobile app, no login screens, and no technical barriers — making e-commerce genuinely accessible to elderly users, low-digital-literacy users, and anyone tired of navigating bloated shopping websites.

---

## 🎯 Problem Statement

Despite the explosive growth of e-commerce in Pakistan, a large portion of potential users are locked out due to **interface complexity**:

- **Information Overload** — Thousands of products, dozens of filters, endless scrolling
- **Poor Query Understanding** — Traditional keyword search fails on natural language like *"kuch acha sa dikhao"*
- **No Personalization** — Recommendations are static and don't adapt to user behavior over time
- **Language Barrier** — Mixed Urdu/English ("Hinglish") queries are poorly handled by mainstream platforms
- **No Voice Support** — Many users prefer speaking over typing, especially in Urdu
- **App Fatigue** — Installing yet another shopping app is a major friction point
- **Complex Navigation** — Elderly and low-digital-literacy users abandon carts due to confusing UI

**ShopGen solves all of these in one WhatsApp conversation.**

---

## 🚀 Features

### 🤖 AI-Powered Conversational Shopping
- Natural language query understanding using **gpt-4o-mini** with a **regex fallback** for speed/reliability
- Extracts structured parameters: **brand, price range, gender, category, query**
- Handles Roman Urdu, English, and mixed input seamlessly
- Multi-turn conversation memory (last 10 messages persisted to Firestore)

### 🔍 Live Product Search
- Real-time Google Shopping results via **SerpAPI**
- Parses product title, price, image, brand, and URL
- Smart filtering by **price, gender, and brand** with graceful fallback messages
- Category inference (clothing / footwear / fragrance / accessories)

### 🎤 Voice Input & Output
- **Speech-to-Text** via OpenAI Whisper with a Pakistani-accent-tuned prompt
- **Text-to-Speech** replies via OpenAI TTS with **gTTS fallback** for Urdu
- Auto number-word normalization (`"five thousand"` → `"5000"`)
- Voice replies sent for short responses (< 400 chars) to reduce latency

### 👗 AI Fashion Advice
- Dedicated LLM node for styling questions (`"what to wear for Eid?"`)
- Context-aware: uses **user's selected products** and **behavior profile**
- Generates 2–3 line outfit pairing suggestions for any product
- Roman Urdu + English responses tuned for Pakistani occasions

### 🏆 Reinforcement Learning Personalization
- **UCB (Upper Confidence Bound)** bandit-based product ranking
- Tracks category affinities, brand preferences, and price patterns
- **Time-decayed** preferences (30-day half-life) so old tastes fade
- Impression counting prevents showing the same product repeatedly
- Rolling average price for budget-aware recommendations

### 📦 Simulated Auto-Order Flow
- Generates a prefilled order page hosted on GitHub Pages
- Includes product, size, address, and contact — all auto-populated
- Sends a WhatsApp confirmation via `/webhook/order` endpoint
- Clearly labeled as *demo* — no real payment or logistics

### 🔗 Click Tracking & Analytics
- Every product link is a **short tracked URL** (`/track/{short_id}`)
- Logs click events to Firestore `click_events` collection
- Feeds back into RL engine as `"click"` signal (weight = 4)
- In-memory cache for 7-day TTL with Firestore persistence

### 🧭 Smart Onboarding
- 3-step profile setup: **Name → City → Style**
- Style options: Casual / Ethnic / Formal / Streetwear
- Profile completeness gates all search features (no cold-start chaos)
- Daily greeting detection based on `last_seen_date`

### 🛡️ Production Reliability
- **Immediate acknowledgment** message to beat WhatsApp's 15-second timeout
- **Async processing** via `asyncio.create_task()` — webhook always returns fast
- **TTL-based deduplication** prevents double-processing of webhooks
- **Response cache** blocks duplicate replies within 60 seconds
- **Rate limiting** (1 msg/sec/user) protects downstream APIs
- **Graceful degradation** on every external API call

---

## 🧠 AI Engine — How It Works

ShopGen's intelligence is built on **four layers working in sequence**:

### 1. Intent Classification (LLM Router)
```
User: "second wala overcoat k sath shoes suggest kro"
              │
              ▼
    ┌───────────────────────┐
    │   smart_router (LLM)  │
    └───────────────────────┘
              │
              ▼
  {"action": "fashion_advice",
   "use_selected_products": true}
```

The router classifies every message into one of **5 actions**:
`search` · `recommend` · `fashion_advice` · `answer` · `clarify`

### 2. Parameter Extraction (Intent Parser)
```
User: "women kurtis under 5000 from Khaadi"
              │
              ▼
  {"query":    "women kurtis under 5000 from Khaadi",
   "gender":   "women",
   "price_max": 5000,
   "brand":    "Khaadi",
   "price_min": null,
   "category": "clothing"}
```

LLM-first extraction with **regex fallback** for zero-downtime parsing.

### 3. Live Product Retrieval (SerpAPI)
```
       Search Query
              │
              ▼
  ┌───────────────────────┐
  │   Google Shopping      │
  │   (SerpAPI)            │
  └───────────────────────┘
              │
              ▼
      Parse + Filter
      (price, gender, brand)
              │
              ▼
      Ranked Product List
```

### 4. Personalization (RL Ranking)
```
       Products
              │
              ▼
  ┌───────────────────────┐
  │   UCB Bandit Scorer    │
  │  ┌─────────────────┐   │
  │  │ Category match  │ +3│
  │  │ Brand match     │ +2│
  │  │ Price proximity │ +1│
  │  │ UCB exploration │ +ε│
  │  └─────────────────┘   │
  └───────────────────────┘
              │
              ▼
      Re-ranked Products
```

Every click, view, and add-to-cart updates the user's **behavior_profile** with decayed weights, making recommendations progressively sharper.

---

## 🗂️ Project Structure

```
ShopGen/
│
├── 📁 agent/                          # LangGraph agent core
│   ├── __init__.py
│   ├── graph.py                       # StateGraph definition + routing
│   ├── nodes.py                       # All node implementations
│   └── state.py                       # AgentState TypedDict
│
├── 📁 services/                       # Business logic modules
│   ├── __init__.py
│   ├── firebase_service.py            # Firestore CRUD (user profiles)
│   ├── intent_parser.py               # LLM + regex intent extraction
│   ├── live_search.py                 # SerpAPI Google Shopping search
│   ├── llm_router.py                  # OpenAI gpt-4o-mini wrapper
│   ├── rl_service.py                  # UCB ranking + decay + RL logging
│   ├── tracking_service.py            # Short link generation & click log
│   └── voice_service.py               # Whisper STT + OpenAI/gTTS TTS
│
├── 📁 static/                         # Static assets
│   └── audio/                         # Generated TTS MP3 files
│
├── 🚀 main.py                         # FastAPI server + webhook
├── 📄 firebase_service.py             # (top-level alias)
├── 📄 README.md                       # You are here
├── 📄 requirements.txt                # Python dependencies
└── 📄 .env                            # Secrets (not committed)
```

---

## ⚙️ Tech Stack

<div align="center">

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.11 | Core backend language |
| **Web Framework** | FastAPI + Uvicorn | Async webhook server |
| **Agent Orchestration** | LangGraph | State machine for conversation flow |
| **LLM** | OpenAI gpt-4o-mini | Intent routing, fashion advice, extraction |
| **STT** | OpenAI Whisper | Voice note transcription |
| **TTS** | OpenAI TTS + gTTS | Voice reply generation |
| **Product Search** | SerpAPI (Google Shopping) | Live product retrieval |
| **Database** | Firebase Firestore | User profiles, history, clicks |
| **WhatsApp Gateway** | Whapi.Cloud | Message send/receive |
| **RL Algorithm** | UCB Bandit | Product re-ranking |
| **HTTP Client** | requests (pooled) | External API calls |
| **Config** | python-dotenv | Secret management |
| **Deployment** | Docker + Nginx + VPS | Production hosting |

</div>

---

## 🔄 LangGraph Agent Workflow

ShopGen uses **LangGraph** to orchestrate a stateful, branching conversation flow:

```
                    ┌──────────────────┐
                    │ load_user_state  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ classify_intent  │  ← smart_router (LLM)
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ check_onboarding │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
     ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
     │ onboarding  │  │   search    │  │   advice    │
     │   (loop)    │  │  products   │  │  /recommend │
     └─────────────┘  └──────┬──────┘  └──────┬──────┘
                             │                │
                             └────────┬───────┘
                                      │
                             ┌────────▼─────────┐
                             │ generate_response│
                             └────────┬─────────┘
                                      │
                             ┌────────▼─────────┐
                             │ save_user_state  │
                             └────────┬─────────┘
                                      │
                                     END
```

**Key routing decisions:**
- **Incomplete profile?** → Forced onboarding loop until all 3 steps complete
- **`action == "search"`** → `search_products` node
- **`action == "fashion_advice"`** → `fashion_advice` node
- **`action == "recommend"`** → `rl_recommendations` node
- **`action == "clarify"`** → `handle_clarification` (can loop back to search)

---

## 🎤 Voice & Multilingual Support

ShopGen is built for the way Pakistanis actually communicate — **mixed Urdu, English, and Roman Urdu**:

### Speech-to-Text
```python
_WHISPER_PROMPT = (
    "Pakistani user. Urdu, English, or mixed Hinglish. Common words: "
    "chahiye, milega, dikhao, karo, bhai, yaar, acha, theek, nahi, haan, "
    "price, order, delivery, shop, kahan, kya, available, stock."
)
```

The prompt priming dramatically improves Whisper's accuracy on Pakistani accents and code-switched speech.

### Number-Word Normalization
```
"five thousand tak"  →  "5000 tak"
"do hazaar"          →  "2000"       (via numeric mapping)
```

### Text-to-Speech
- **OpenAI TTS** (`tts-1`, voice `alloy`) as primary
- **gTTS with Urdu language detection** as fallback
- URL stripping + emoji removal before synthesis
- Only generates audio for responses < 400 chars (avoids novel-length TTS)

---

## 🏆 Reinforcement Learning Personalization

ShopGen's RL engine is inspired by **contextual bandits** (Li et al., 2010):

### Behavior Profile Structure
```json
{
  "categories":         {"clothing": 12, "footwear": 5},
  "brands":             {"Khaadi": 8, "Ndure": 4},
  "subcategories":      {"shirt": 6, "kurta": 3},
  "impressions":        {"prod_abc": 3, "prod_xyz": 1},
  "total_interactions": 17,
  "avg_price":          4250.00,
  "style_preference":   "ethnic",
  "last_active":        "2026-04-28"
}
```

### UCB Scoring Formula
```
score = 3·(cat_affinity) + 2·(brand_affinity) + 1·(price_proximity)
        + C · √(ln(total + 1) / (impressions + 1))
```

Where:
- **Category affinity** rewards categories the user has engaged with
- **Brand affinity** rewards brands the user prefers
- **Price proximity** rewards products near the user's avg spend
- **UCB term** ensures exploration — prevents recommendation echo chambers

### Time Decay
```
decay_factor = 0.5 ^ (days_since_active / 30)
```

Preferences from a month ago count half as much as today's. A cached decay result (60s TTL) avoids recomputing on every request.

### Interaction Weights
| Event | Weight |
|---|---|
| **Click** (link tap) | 4 |
| **Add to cart** | 3 |
| **View** (impression) | 1 |

---

## 🗄️ Database Design (Firestore)

ShopGen uses **Google Firebase Firestore** — a serverless NoSQL document store — chosen for its **sub-100ms latency**, **automatic scaling**, and **natural fit for semi-structured user data**.

### Collections

#### 📁 `users` (keyed by WhatsApp number)
```
users/{phone_number}
├── user_profile         { name, city, style }
├── conversation_history [ { role, content }, ... ]   (max 10)
├── behavior_profile     { categories, brands, impressions, avg_price, ... }
├── last_shown_products  [ { product_id, name, price, ... } ]
├── selected_products    [ { product_id, name, ... } ]
├── last_seen_date       "2026-04-28"
├── onboarding_step      "style" | null
└── last_intent          "search" | "fashion_advice" | ...
```

#### 📁 `click_events` (auto-ID)
```
click_events/{auto_id}
├── user_id       "+92300..."
├── product_id    "prod_xyz"
├── position      3
├── search_query  "kurtis under 3000"
└── timestamp     Firestore server time
```

#### 📁 `short_links` (keyed by MD5 hash)
```
short_links/{short_id}
├── user_id       "+92300..."
├── product_id    "prod_xyz"
├── original_url  "https://daraz.pk/..."
├── query         "kurtis under 3000"
├── created_at    1714000000
└── expires_at    1714604800
```

#### 📁 `products` (fallback only)
Mock products used when SerpAPI fails — ensures the demo never goes fully dark.

---

## 🔗 Tracking & Analytics

Every product shown to a user gets a **short tracked link**:

```python
short_id = md5(f"{user_id}{product_id}{position}{url}{time}")[:16]
tracked_url = f"{BASE_URL}/track/{short_id}"
```

When a user taps the link:
1. `/track/{short_id}` looks up the payload (cache → Firestore)
2. Writes a `click_events` document
3. Updates the user's `behavior_profile` (RL feedback)
4. **302 redirects** to the original product URL

This closes the loop between **showing** products and **learning** what users actually click.

---

## 🛠️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/shopgen.git
cd shopgen
```

### 2️⃣ Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment
Create a `.env` file (see next section).

### 5️⃣ Run the Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6️⃣ Expose Webhook
Use **ngrok** (for local dev) or deploy to a VPS with a public HTTPS URL:
```bash
ngrok http 8000
```

Then set the Whapi.Cloud webhook to `https://your-url/webhook`.

---

## 📁 Environment Configuration

Create a `.env` file in the project root:

```env
# ─── OpenAI ────────────────────────────────────────
OPENAI_API_KEY=sk-...

# ─── Firebase ──────────────────────────────────────
FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccountKey.json

# ─── Whapi.Cloud (WhatsApp Gateway) ────────────────
WHAPI_TOKEN=your_whapi_token
WHAPI_URL=https://gate.whapi.cloud

# ─── Server ────────────────────────────────────────
BASE_URL=https://your-public-url.com
AUDIO_DIR=static/audio
```

> 💡 **Firebase setup:** Create a project on [Firebase Console](https://console.firebase.google.com), enable Firestore, and download a service account JSON key.

> 💡 **Whapi.Cloud setup:** Register at [whapi.cloud](https://whapi.cloud) and link your WhatsApp Business number.

---

## 🧩 Module Architecture

| Module | Responsibility |
|---|---|
| **`main.py`** | FastAPI app, `/webhook`, `/track/{id}`, deduplication, rate limiting, async dispatch |
| **`agent/graph.py`** | LangGraph construction and conditional routing |
| **`agent/nodes.py`** | All node functions: onboarding, search, advice, RL, response formatting |
| **`agent/state.py`** | `AgentState` TypedDict — the shared data contract |
| **`services/firebase_service.py`** | Firestore read/write for user data |
| **`services/llm_router.py`** | OpenAI wrapper with rate limiting + timeout |
| **`services/intent_parser.py`** | LLM + regex fallback for parameter extraction |
| **`services/live_search.py`** | SerpAPI Google Shopping with filtering |
| **`services/rl_service.py`** | UCB ranking, time decay, interaction logging |
| **`services/tracking_service.py`** | Short link generation + click logging |
| **`services/voice_service.py`** | Whisper transcription + TTS generation |

---

## 🧪 Testing

ShopGen was tested across **four complementary methods**:

### ✅ Unit Tests
- `parse_intent()` — verified parameter extraction on 50 sample queries
- `_apply_time_decay()` — confirmed decay math across simulated days
- `strip_for_speech()` — validated URL/emoji/markdown removal

### ✅ Integration Tests
- Live `live_search_products()` calls against SerpAPI
- Forced-timeout tests on `call_llm()` to verify fallback behavior
- Firestore read/write cycles with a staging user

### ✅ End-to-End Tests
- Full conversation flows simulated via a test WhatsApp number
- Verified onboarding, search, voice, advice, and recommendation paths
- Tested edge cases: empty messages, 4000+ char responses, duplicates

### ✅ Performance Tests
- **Locust** load test: 50 msg/sec for 5 minutes
- Average **acknowledgment time: 85 ms** (target < 500 ms)
- Average **full response time: 4.2 s** (well under WhatsApp's 15 s limit)
- CPU peaked at 65% on a 2-vCPU VPS; memory stable at 1.2 GB

**All 10 functional test cases and 3 non-functional test cases passed.**

---

## 👨‍💻 Authors

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=20&pause=1000&color=14B8A6&width=550&lines=Final+Year+Project+2026;BS+Artificial+Intelligence;Built+with+%E2%9D%A4%EF%B8%8F+by+the+team" alt="Authors"/>

<br/>

### 🧑‍💻 Muhammad Haziq Imran
**Reg No:** COSC-221103049

[![GitHub](https://img.shields.io/badge/GitHub-haziqimran18-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/haziqimran18)

<br/>

### 🧑‍💻 Muhammad Talha Shahid
**Reg No:** COSC-221103062

[![GitHub](https://img.shields.io/badge/GitHub-talhashahid-181717?style=for-the-badge&logo=github&logoColor=white)](#)

<br/>

---

### 🎓 Project Details

| Field | Detail |
|---|---|
| **Project Type** | Final Year Project (FYP) |
| **Year** | 2026 |
| **Department** | Data Science & Artificial Intelligence |
| **University** | Khwaja Fareed University of Engineering & IT, Rahim Yar Khan |
| **Supervisor** | Mr. Muhammad Adeel Abid |
| **Domain** | Conversational AI · E-Commerce · EdTech |
| **Core AI Techniques** | LLM · RAG · Reinforcement Learning · Speech Processing |

</div>

---

<div align="center">

<br/>

*"Turning WhatsApp into the smartest shopping mall in Pakistan — one message at a time."*

<br/>

<img src="https://img.shields.io/badge/⭐_Star_this_repo_if_it_helped_you!-14B8A6?style=for-the-badge"/>

<br/><br/>

<img src="https://img.shields.io/badge/Made_with-❤️_in_Pakistan_🇵🇰-14B8A6?style=for-the-badge"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Status-Active-22c55e?style=for-the-badge"/>

</div>
