"""
Google OAuth Login — FastAPI
-------------------------------
Setup:
    pip install fastapi uvicorn httpx itsdangerous python-dotenv

Before running:
    1. Go to https://console.cloud.google.com/apis/credentials
    2. Create an OAuth 2.0 Client ID (type: Web application)
    3. Add http://localhost:8000/callback/google as an authorized redirect URI
    4. Create a .env file in this same folder containing:
           GOOGLE_CLIENT_ID=your-client-id
           GOOGLE_CLIENT_SECRET=your-client-secret
           SESSION_SECRET_KEY=your-random-secret-key

Run:
    uvicorn fastapi_google_oauth:app --reload
Then visit http://localhost:8000/

Note: FastAPI is built on Starlette and is async by default, so we use
httpx.AsyncClient instead of the `requests` library, and add Starlette's
SessionMiddleware manually (Flask/Django include session handling out
of the box; FastAPI does not).
"""

import os
import secrets
import json
import base64
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()  # reads the .env file in the current directory and loads it into os.environ

app = FastAPI()

_session_secret = os.environ.get("SESSION_SECRET_KEY")
if not _session_secret:
    raise RuntimeError("Set SESSION_SECRET_KEY in your .env file")
app.add_middleware(SessionMiddleware, secret_key=_session_secret)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "your-client-id")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "your-client-secret")
REDIRECT_URI = "http://localhost:8000/callback/google"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def decode_jwt_payload(jwt_token):
    """
    Decodes (but does NOT verify) the middle segment of a JWT to peek at
    its claims. Fine for local debugging/printing. In production, use a
    library like google-auth (google.oauth2.id_token.verify_oauth2_token)
    which actually verifies the signature — never trust an unverified
    token for real authentication decisions.
    """
    payload_segment = jwt_token.split(".")[1]
    padding = "=" * (-len(payload_segment) % 4)
    decoded_bytes = base64.urlsafe_b64decode(payload_segment + padding)
    return json.loads(decoded_bytes)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    if user:
        return f"Logged in as {user['email']} — <a href='/logout'>Logout</a>"
    return '<a href="/login/google">Login with Google</a>'


# STEP 1 + 2: Redirect to Google with a CSRF state value stored in the session
@app.get("/login/google")
async def login_google(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


# STEP 3-6: Google redirects back here with ?code=...&state=...
@app.get("/callback/google")
async def callback_google(request: Request, code: str, state: str):
    if state != request.session.get("oauth_state"):
        return HTMLResponse("Invalid state parameter — possible CSRF attempt", status_code=400)

    async with httpx.AsyncClient() as client:
        # Exchange the code for tokens (server-to-server call)
        token_response = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        })
        tokens = token_response.json()

        if "error" in tokens:
            return HTMLResponse(f"Token exchange failed: {tokens}", status_code=400)

        # Use the access token to fetch the user's profile
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        profile = userinfo_response.json()

    # ---- Print everything we have access to, to the console ----
    print("\n" + "=" * 60)
    print("RAW TOKEN RESPONSE (from Google's /token endpoint)")
    print("=" * 60)
    for key, value in tokens.items():
        print(f"{key}: {value}")

    if "id_token" in tokens:
        print("\n" + "=" * 60)
        print("DECODED ID TOKEN CLAIMS (identity info about the user)")
        print("=" * 60)
        id_token_claims = decode_jwt_payload(tokens["id_token"])
        print(json.dumps(id_token_claims, indent=2))

    print("\n" + "=" * 60)
    print("USERINFO ENDPOINT RESPONSE (profile fields)")
    print("=" * 60)
    print(json.dumps(profile, indent=2))
    print("=" * 60 + "\n")

    request.session["user"] = profile
    return RedirectResponse("/")


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/")