# OAuth 2.0 Google Login — FastAPI

A minimal, working example of **Google OAuth 2.0 login** using the **Authorization Code flow**, built with FastAPI.

This project demonstrates the full OAuth handshake end to end:
1. Redirect the user to Google's login screen
2. Google redirects back with a one-time authorization code
3. Exchange that code for an access token (server-to-server, async)
4. Use the access token to fetch the user's profile
5. Store the logged-in user in a Starlette session

## Tech Stack

- **FastAPI** — async web framework
- **uvicorn** — ASGI server
- **httpx** — async HTTP client for Google's token and userinfo endpoints
- **itsdangerous** — required by Starlette's `SessionMiddleware` to sign session cookies
- **python-dotenv** — loads credentials from a `.env` file

> Unlike Flask or Django, FastAPI doesn't include session handling out of the box — this project adds Starlette's `SessionMiddleware` manually.

## Prerequisites

- Python 3.9+
- A Google Cloud project with OAuth 2.0 credentials ([console.cloud.google.com](https://console.cloud.google.com/apis/credentials))

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/<your-username>/oauth2-google-login-fastapi.git
   cd oauth2-google-login-fastapi
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # on Windows: .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Google OAuth credentials**
   - Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
   - Create an OAuth 2.0 Client ID (type: Web application)
   - Add `http://localhost:8000/callback/google` as an authorized redirect URI

5. **Create a `.env` file** (see `.env.example`)
   ```
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   SESSION_SECRET_KEY=your-random-secret-key
   ```
   Generate a random secret key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

6. **Run the app**
   ```bash
   uvicorn fastapi_google_oauth:app --reload
   ```

7. Visit **http://localhost:8000/** (use `localhost`, not `127.0.0.1` — they're treated as different cookie domains) and click "Login with Google."

## What gets printed

On successful login, the console prints:
- The raw token response (access token, refresh token, ID token, scope, expiry)
- Decoded ID token claims (email, name, picture, etc.)
- The userinfo endpoint response

## Project Structure

```
.
├── fastapi_google_oauth.py   # main application
├── requirements.txt
├── .env.example
└── .gitignore
```

## Notes

- Uses `httpx.AsyncClient` for non-blocking calls to Google's endpoints.
- Uses `access_type=offline` + `prompt=consent` to also request a refresh token.
- CSRF protection via a `state` parameter validated against the session.
- Not production-hardened — this is a learning/reference implementation.

## License

MIT
