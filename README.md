# Insighta Labs+ — Backend API

A secure, role-based demographic intelligence REST API built with Flask.
This is the backend service for the Insighta Labs+ platform, serving both the CLI tool and the Web Portal.

---

## System Architecture

┌─────────────────────────────────────────────────────┐
│ Insighta Labs+ │
│ │
│ ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│ │ CLI │ │ Web │ │ Direct API │ │
│ │ Tool │ │ Portal │ │ Consumers │ │
│ └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
│ │ │ │ │
│ └───────────────┼─────────────────┘ │
│ │ │
│ ┌─────────▼──────────┐ │
│ │ Flask REST API │ │
│ │ (Backend Core) │ │
│ └─────────┬──────────┘ │
│ │ │
│ ┌─────────────┼──────────────┐ │
│ │ │ │ │
│ ┌──────▼──────┐ ┌────▼────┐ ┌──────▼──────┐ │
│ │ Auth │ │Profile │ │ Rate │ │
│ │ System │ │ APIs │ │ Limiter │ │
│ └──────┬──────┘ └────┬────┘ └─────────────┘ │
│ │ │ │
│ ┌──────▼─────────────▼──────┐ │
│ │ SQLite Database │ │
│ │ users | profiles | │ │
│ │ refresh_tokens │ │
│ └───────────────────────────┘ │
└─────────────────────────────────────────────────────┘

### Tech Stack

| Layer          | Technology                                |
| -------------- | ----------------------------------------- |
| Framework      | Flask                                     |
| Database       | SQLite + Flask-SQLAlchemy                 |
| Authentication | GitHub OAuth 2.0 + PKCE                   |
| Tokens         | PyJWT (access) + DB-stored refresh tokens |
| Rate Limiting  | Flask-Limiter                             |
| HTTP Client    | httpx                                     |
| CORS           | Flask-CORS                                |

---

## Authentication Flow

### GitHub OAuth with PKCE

CLI / Browser
│
│ 1. User initiates login
▼
GET /auth/github
│
│ 2. Redirect to GitHub OAuth page
▼
GitHub Login Page
│
│ 3. User authenticates, GitHub redirects back with code
▼
GET /auth/github/callback?code=xxx
│
│ 4. Backend exchanges code for GitHub access token
│ 5. Backend fetches user info from GitHub API
│ 6. Backend creates or updates user in database
│ 7. Backend issues access token + refresh token
▼
│
├── CLI request (code_verifier present) → returns JSON
│
└── Browser request → sets HTTP-only cookies, redirects to web portal

### Token Lifecycle

Copy

Insert at cursor
Login
│
├── Access Token issued (expires in 3 minutes)
└── Refresh Token issued (expires in 5 minutes, stored in DB)

API Request
│
├── Valid access token → request proceeds
└── Expired access token → client calls POST /auth/refresh
│
├── Valid refresh token → new access + refresh token pair issued
│ Old refresh token is immediately deleted (rotation)
└── Expired refresh token → user must log in again

### Auth Endpoints

| Method | Endpoint                | Description                           |
| ------ | ----------------------- | ------------------------------------- |
| GET    | `/auth/github`          | Redirects to GitHub OAuth             |
| GET    | `/auth/github/callback` | Handles OAuth callback, issues tokens |
| POST   | `/auth/refresh`         | Rotates token pair                    |
| POST   | `/auth/logout`          | Invalidates refresh token server-side |

---

## Token Handling Approach

- Access tokens are short-lived JWTs (3 minutes), signed with `JWT_SECRET_KEY`
- Refresh tokens are random URL-safe strings stored in the `refresh_tokens` table
- On every refresh, the old refresh token is deleted and a new pair is issued (rotation)
- If a refresh token is expired or not found, the user must re-authenticate
- For the web portal, both tokens are stored in HTTP-only cookies (not accessible via JavaScript)
- For the CLI, tokens are stored locally at `~/.insighta/credentials.json`

---

## Role Enforcement Logic

Every `/api/*` endpoint is protected by the `require_auth` decorator.
Admin-only endpoints additionally use the `admin_required` decorator.

Incoming Request to /api/\*
│
▼
Check X-API-Version header == "1"
│
✗ Missing → 400 Bad Request
│
✓ Present
│
▼
Check Authorization: Bearer
│
✗ Missing → 401 Unauthorized
│
✓ Present → Decode JWT
│
✗ Expired / Invalid → 401 Unauthorized
│
✓ Valid → Load user from DB
│
✗ User not found → 401 Unauthorized
│
✗ is_active = false → 403 Forbidden
│
✓ Active user → attach to request.current_user
│
▼
Role Check (admin_required endpoints only)
│
✗ role != "admin" → 403 Forbidden
│
✓ role == "admin" → proceed

| Role      | Permissions                                                                      |
| --------- | -------------------------------------------------------------------------------- |
| `analyst` | Read-only: GET /api/profiles, GET /api/profiles/search, GET /api/profiles/export |
| `admin`   | Full access: all analyst permissions + POST /api/profiles                        |

Default role on signup: `analyst`

---

## Profile APIs

### API Versioning

All `/api/*` requests must include:
X-API-Version: 1
Missing header returns `400 Bad Request`.

### Endpoints

| Method | Endpoint               | Role           | Description                                     |
| ------ | ---------------------- | -------------- | ----------------------------------------------- |
| GET    | `/api/profiles`        | analyst, admin | List profiles with filters, sorting, pagination |
| GET    | `/api/profiles/search` | analyst, admin | Natural language search                         |
| POST   | `/api/profiles`        | admin only     | Create a new profile                            |
| GET    | `/api/profiles/export` | analyst, admin | Export profiles as CSV                          |

### Filtering Parameters

| Parameter    | Type    | Description                               |
| ------------ | ------- | ----------------------------------------- |
| `gender`     | string  | `male` or `female`                        |
| `age_group`  | string  | `teenager`, `adult`, `senior`             |
| `country_id` | string  | ISO 2-letter code e.g. `NG`               |
| `min_age`    | integer | Minimum age                               |
| `max_age`    | integer | Maximum age                               |
| `sort_by`    | string  | `age`, `created_at`, `gender_probability` |
| `order`      | string  | `asc` or `desc`                           |
| `page`       | integer | Page number (default: 1)                  |
| `limit`      | integer | Results per page (default: 10, max: 50)   |

### Paginated Response Shape

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "total_pages": 203,
  "links": {
    "self": "/api/profiles?page=1&limit=10",
    "next": "/api/profiles?page=2&limit=10",
    "prev": null
  },
  "data": []
}
```

Natural Language Parsing Approach
The search endpoint (GET /api/profiles/search?q=) uses a rule-based parser — no AI or NLP models.

How It Works:
Input: "young females from nigeria"
│
▼

1. Normalize → lowercase the query
   │
   ▼
2. Keyword matching
   "female" → gender = female
   "young" → min_age = 16, max_age = 24
   "nigeria" → country_id = NG
   │
   ▼
3. Combine all matched filters with AND logic
   │
   ▼
4. Run filtered query against database

Supported Keywords
Category Keyword Filter Applied
Gender male, males gender = male
Gender female, females gender = female
Age young min_age = 16, max_age = 24
Age adult age_group = adult
Age teenager age_group = teenager
Age senior age_group = senior
Age above X min_age = X
Country nigeria country_id = NG
Country kenya country_id = KE
Country angola country_id = AO
Country uganda country_id = UG
Country united states country_id = US
Limitations
No fuzzy matching — misspellings are not handled

No OR / NOT logic

No context awareness between requests

Only predefined keywords are recognized

Rate Limiting
Scope Limit
/auth/\* endpoints 10 requests per minute
All other endpoints 60 requests per minute per user
Exceeding the limit returns 429 Too Many Requests.

Environment Variables
Create a .env file in the project root:
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:5000/auth/github/callback
JWT_SECRET_KEY=your_random_secret_key
FRONTEND_URL=http://localhost:3000

Running Locally
pip install -r requirements.txt
python run.py
Server starts at http://localhost:5000

Running Tests
pytest tests/ -v
