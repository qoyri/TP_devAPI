"""
Serveur OAuth2 simple - Utilise MySQL
Supporte: client_credentials, authorization_code, introspection
"""

import os
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional
import mysql.connector
from fastapi import FastAPI, Form, HTTPException, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from passlib.context import CryptContext

# Configuration
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "db"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "sirenuser"),
    "password": os.getenv("MYSQL_PASSWORD", "12345678"),
    "database": os.getenv("MYSQL_DATABASE", "siren")
}

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__truncate_error=False
)
security = HTTPBasic()

app = FastAPI(
    title="OAuth2 Server",
    description="Serveur OAuth2 avec support client_credentials et introspection",
    version="1.0.0",
    docs_url="/api-docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return mysql.connector.connect(**MYSQL_CONFIG)

def init_db():
    """Crée les tables OAuth2 si elles n'existent pas"""
    db = get_db()
    cursor = db.cursor()

    # Table des clients OAuth2
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_clients (
            id VARCHAR(36) PRIMARY KEY,
            secret_hash VARCHAR(255) NOT NULL,
            name VARCHAR(100) NOT NULL,
            redirect_uri VARCHAR(500),
            scopes VARCHAR(500) DEFAULT 'read',
            grant_types VARCHAR(200) DEFAULT 'client_credentials',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table des tokens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            token VARCHAR(255) PRIMARY KEY,
            client_id VARCHAR(36) NOT NULL,
            scopes VARCHAR(500),
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_expires (expires_at)
        )
    """)

    # Table des codes d'autorisation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_codes (
            code VARCHAR(255) PRIMARY KEY,
            client_id VARCHAR(36) NOT NULL,
            redirect_uri VARCHAR(500),
            scopes VARCHAR(500),
            code_challenge VARCHAR(255),
            code_challenge_method VARCHAR(10),
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Clients par défaut
    clients = [
        ("mysql-api-client", "mysql_api_secret", "MySQL API Client", "client_credentials,introspect"),
        ("spark-api-client", "spark_api_secret", "Spark API Client", "client_credentials,introspect"),
        ("frontend-client", "frontend_secret", "Frontend Application", "authorization_code,refresh_token"),
    ]

    for client_id, secret, name, grants in clients:
        secret_hash = pwd_context.hash(secret)
        cursor.execute("""
            INSERT IGNORE INTO oauth_clients (id, secret_hash, name, grant_types, scopes)
            VALUES (%s, %s, %s, %s, 'read write')
        """, (client_id, secret_hash, name, grants))

    db.commit()
    cursor.close()
    db.close()

def create_access_token(client_id: str, scopes: str = "read") -> tuple[str, int]:
    """Crée un access token JWT"""
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    payload = {
        "sub": client_id,
        "scope": scopes,
        "exp": expires,
        "iat": datetime.utcnow(),
        "type": "access_token"
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # Stocker le token
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO oauth_tokens (token, client_id, scopes, expires_at)
        VALUES (%s, %s, %s, %s)
    """, (token, client_id, scopes, expires))
    db.commit()
    cursor.close()
    db.close()

    return token, expires_in

def verify_client(client_id: str, client_secret: str) -> bool:
    """Vérifie les credentials d'un client"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT secret_hash FROM oauth_clients WHERE id = %s", (client_id,))
    row = cursor.fetchone()
    cursor.close()
    db.close()

    if not row:
        return False
    return pwd_context.verify(client_secret, row["secret_hash"])

def get_client_from_basic_auth(credentials: HTTPBasicCredentials) -> Optional[str]:
    """Extrait et vérifie le client depuis Basic Auth"""
    if verify_client(credentials.username, credentials.password):
        return credentials.username
    return None

@app.on_event("startup")
async def startup():
    """Initialise la base de données au démarrage"""
    try:
        init_db()
        print("OAuth2 database initialized")
    except Exception as e:
        print(f"Warning: Could not initialize DB: {e}")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "oauth2-server"}

@app.post("/oauth/token")
async def token(
    grant_type: str = Form(...),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    scope: str = Form("read"),
    request: Request = None
):
    """
    Endpoint OAuth2 Token
    Supporte: client_credentials, authorization_code
    """
    # Essayer d'extraire client_id/secret depuis Basic Auth si non fournis
    if not client_id or not client_secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                client_id, client_secret = decoded.split(":", 1)
            except:
                pass

    if not client_id or not client_secret:
        raise HTTPException(status_code=401, detail="Client credentials required")

    if not verify_client(client_id, client_secret):
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    if grant_type == "client_credentials":
        token, expires_in = create_access_token(client_id, scope)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": scope
        }

    elif grant_type == "authorization_code":
        if not code:
            raise HTTPException(status_code=400, detail="Code required")

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM oauth_codes
            WHERE code = %s AND client_id = %s AND expires_at > NOW()
        """, (code, client_id))
        auth_code = cursor.fetchone()

        if not auth_code:
            cursor.close()
            db.close()
            raise HTTPException(status_code=400, detail="Invalid or expired code")

        # Vérifier PKCE si présent
        if auth_code["code_challenge"]:
            if not code_verifier:
                raise HTTPException(status_code=400, detail="Code verifier required")

            if auth_code["code_challenge_method"] == "S256":
                computed = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).decode().rstrip("=")
            else:
                computed = code_verifier

            if computed != auth_code["code_challenge"]:
                raise HTTPException(status_code=400, detail="Invalid code verifier")

        # Supprimer le code utilisé
        cursor.execute("DELETE FROM oauth_codes WHERE code = %s", (code,))
        db.commit()
        cursor.close()
        db.close()

        token, expires_in = create_access_token(client_id, auth_code["scopes"] or "read")
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": auth_code["scopes"] or "read"
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant type: {grant_type}")

@app.post("/oauth/introspect")
async def introspect(
    token: str = Form(...),
    request: Request = None
):
    """
    Endpoint d'introspection RFC 7662
    """
    # Vérifier l'authentification du client
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Client authentication required")

    try:
        decoded = base64.b64decode(auth_header[6:]).decode()
        client_id, client_secret = decoded.split(":", 1)
        if not verify_client(client_id, client_secret):
            raise HTTPException(status_code=401, detail="Invalid client credentials")
    except:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    # Vérifier le token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Vérifier en base
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM oauth_tokens
            WHERE token = %s AND expires_at > NOW()
        """, (token,))
        token_record = cursor.fetchone()
        cursor.close()
        db.close()

        if token_record:
            return {
                "active": True,
                "client_id": payload.get("sub"),
                "scope": payload.get("scope", "read"),
                "exp": int(payload.get("exp", 0)),
                "token_type": "Bearer"
            }
    except:
        pass

    return {"active": False}

@app.get("/oauth/authorize")
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str = "read",
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None
):
    """
    Page d'autorisation OAuth2 (pour authorization_code flow)
    """
    # Vérifier le client
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM oauth_clients WHERE id = %s", (client_id,))
    client = cursor.fetchone()
    cursor.close()
    db.close()

    if not client:
        raise HTTPException(status_code=400, detail="Unknown client")

    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only 'code' response_type supported")

    # Formulaire simple d'autorisation
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Autorisation OAuth2</title>
    <style>
        body {{ font-family: sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }}
        .btn {{ padding: 10px 20px; margin: 5px; cursor: pointer; }}
        .approve {{ background: #4CAF50; color: white; border: none; }}
        .deny {{ background: #f44336; color: white; border: none; }}
    </style>
    </head>
    <body>
        <h2>Autorisation requise</h2>
        <p><strong>{client['name']}</strong> demande l'accès à votre compte.</p>
        <p>Scopes demandés: <code>{scope}</code></p>
        <form method="post" action="/oauth/authorize/approve">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="scope" value="{scope}">
            <input type="hidden" name="state" value="{state or ''}">
            <input type="hidden" name="code_challenge" value="{code_challenge or ''}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method or ''}">
            <button type="submit" name="action" value="approve" class="btn approve">Autoriser</button>
            <button type="submit" name="action" value="deny" class="btn deny">Refuser</button>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/oauth/authorize/approve")
async def authorize_approve(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form("read"),
    state: str = Form(""),
    code_challenge: str = Form(""),
    code_challenge_method: str = Form(""),
    action: str = Form(...)
):
    """Traite la réponse d'autorisation"""
    if action == "deny":
        return RedirectResponse(
            url=f"{redirect_uri}?error=access_denied&state={state}",
            status_code=302
        )

    # Générer le code
    code = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(minutes=10)

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO oauth_codes (code, client_id, redirect_uri, scopes, code_challenge, code_challenge_method, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (code, client_id, redirect_uri, scope, code_challenge or None, code_challenge_method or None, expires))
    db.commit()
    cursor.close()
    db.close()

    redirect = f"{redirect_uri}?code={code}"
    if state:
        redirect += f"&state={state}"

    return RedirectResponse(url=redirect, status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)
