from supabase import create_client
import os
import httpx
from dotenv import load_dotenv
import jwt
import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class serviceLogin:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    def get_auth_url(self):
        """Génère l'URL de redirection vers Google"""
        params = (
            f"?client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={GOOGLE_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope=openid email profile"
            f"&access_type=offline"
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth{params}"

    async def handle_callback(self, code: str):
        """Échange le code contre un token, récupère le profil, crée ou trouve le user"""
        async with httpx.AsyncClient() as client:

            # 1. Échanger le code contre un access token
            token_response = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                return None, "Failed to get access token"

            # 2. Récupérer le profil Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            profile = userinfo_response.json()

        google_id = profile.get("id")
        email = profile.get("email")
        username = profile.get("name")

        if not google_id or not email:
            return None, "Failed to get user info from Google"

        # 3. Chercher le user dans Supabase par google_id
        response = self.supabase.table("users").select("*").eq("google_id", google_id).execute()
        users = response.data

        if users:
            # User existe déjà → on le retourne
            user = users[0]
        else:
            # Nouveau user → on le crée
            insert_response = self.supabase.table("users").insert({
                "google_id": google_id,
                "email": email,
                "user_name": username,
                "password": None,
                "admin": False,
            }).execute()
            user = insert_response.data[0]

        return user, None
    
    def create_jwt(self, user):
        """Génère un JWT signé avec les infos du user"""
        payload = {
            "email": user["email"],
            "username": user["user_name"],
            "admin": user["admin"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    def verify_jwt(self, token):
        """Vérifie et décode un JWT"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "Token expiré"
        except jwt.InvalidTokenError:
            return None, "Token invalide"