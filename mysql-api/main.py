"""
API MySQL - Entreprises SIREN
Format JSON-LD avec pagination Hydra
"""

import os
import base64
import httpx
import mysql.connector
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configuration
OAUTH2_INTROSPECT_URL = os.getenv("OAUTH2_INTROSPECT_URL", "http://oauth2-server:4000/oauth/introspect")
OAUTH2_CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID", "mysql-api-client")
OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET", "mysql_api_secret")
DEFAULT_PAGE_SIZE = 20

# MySQL config
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "db"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "sirenuser"),
    "password": os.getenv("MYSQL_PASSWORD", "12345678"),
    "database": os.getenv("MYSQL_DATABASE", "siren")
}

# JSON-LD Context
JSON_LD_CONTEXT = {
    "@context": {
        "@vocab": "https://schema.org/",
        "siren": "https://www.sirene.fr/sirene/public/variable/siren",
        "denominationUniteLegale": "https://schema.org/legalName",
        "activitePrincipale": "https://www.sirene.fr/sirene/public/variable/activitePrincipaleUniteLegale",
        "hydra": "http://www.w3.org/ns/hydra/core#",
        "totalItems": "hydra:totalItems",
        "member": "hydra:member",
        "view": "hydra:view",
        "first": "hydra:first",
        "last": "hydra:last",
        "next": "hydra:next",
        "previous": "hydra:previous"
    }
}

app = FastAPI(
    title="API Entreprises SIREN",
    description="""
API REST pour accéder aux données des entreprises françaises (base SIREN).

## Format JSON-LD
Toutes les réponses sont au format JSON-LD avec le contexte Hydra pour la pagination.

## Authentification
Cette API nécessite un token OAuth2 valide. Utilisez le header:
`Authorization: Bearer <votre_token>`

## Endpoints
- `/entreprises/siren/{siren}` - Recherche par numéro SIREN
- `/entreprises/activite/{code}` - Recherche par code activité
- `/entreprises/search` - Recherche par nom (filtre)
    """,
    version="1.0.0",
    docs_url="/api-docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_db():
    return mysql.connector.connect(**MYSQL_CONFIG)

async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valide le token via introspection OAuth2"""
    token = credentials.credentials
    try:
        auth_header = base64.b64encode(f"{OAUTH2_CLIENT_ID}:{OAUTH2_CLIENT_SECRET}".encode()).decode()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OAUTH2_INTROSPECT_URL,
                data={"token": token},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {auth_header}"
                }
            )
            if response.status_code != 200 or not response.json().get("active", False):
                raise HTTPException(status_code=401, detail="Token invalide ou expiré")
            return response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Serveur OAuth2 indisponible")

def to_json_ld(row: dict) -> dict:
    """Convertit une ligne en format JSON-LD"""
    return {
        "@type": "Organization",
        "siren": row.get("siren"),
        "denominationUniteLegale": row.get("denominationUniteLegale"),
        "activitePrincipale": row.get("activitePrincipaleUniteLegale"),
        "nomenclature": row.get("nomenclatureActivitePrincipaleUniteLegale")
    }

def create_paginated_response(items: list, total: int, page: int, page_size: int, base_url: str) -> dict:
    """Crée une réponse paginée au format Hydra"""
    total_pages = max(1, (total + page_size - 1) // page_size)
    response = {
        **JSON_LD_CONTEXT,
        "@type": "hydra:Collection",
        "totalItems": total,
        "member": items,
        "view": {
            "@type": "hydra:PartialCollectionView",
            "@id": f"{base_url}?page={page}&pageSize={page_size}",
            "first": f"{base_url}?page=1&pageSize={page_size}",
            "last": f"{base_url}?page={total_pages}&pageSize={page_size}"
        }
    }
    if page > 1:
        response["view"]["previous"] = f"{base_url}?page={page-1}&pageSize={page_size}"
    if page < total_pages:
        response["view"]["next"] = f"{base_url}?page={page+1}&pageSize={page_size}"
    return response

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mysql-api"}

@app.get("/entreprises/siren/{siren}")
async def get_by_siren(siren: str, token_info: dict = Depends(validate_token)):
    """
    Recherche une entreprise par son numéro SIREN
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT siren, denominationUniteLegale, activitePrincipaleUniteLegale, nomenclatureActivitePrincipaleUniteLegale FROM unite_legale WHERE siren = %s",
        (siren,)
    )
    row = cursor.fetchone()
    cursor.close()
    db.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Entreprise SIREN {siren} non trouvée")

    return JSONResponse(
        content={**JSON_LD_CONTEXT, **to_json_ld(row)},
        media_type="application/ld+json"
    )

@app.get("/entreprises/activite/{code}")
async def get_by_activity(
    code: str,
    request: Request,
    page: int = Query(1, ge=1, description="Numéro de page"),
    pageSize: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100, description="Taille de page"),
    token_info: dict = Depends(validate_token)
):
    """
    Recherche les entreprises par code activité
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Compter le total
    cursor.execute(
        "SELECT COUNT(*) as total FROM unite_legale WHERE activitePrincipaleUniteLegale = %s",
        (code,)
    )
    total = cursor.fetchone()["total"]

    # Récupérer la page
    offset = (page - 1) * pageSize
    cursor.execute(
        """SELECT siren, denominationUniteLegale, activitePrincipaleUniteLegale, nomenclatureActivitePrincipaleUniteLegale
        FROM unite_legale WHERE activitePrincipaleUniteLegale = %s
        LIMIT %s OFFSET %s""",
        (code, pageSize, offset)
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    items = [to_json_ld(row) for row in rows]
    base_url = str(request.url).split("?")[0]

    return JSONResponse(
        content=create_paginated_response(items, total, page, pageSize, base_url),
        media_type="application/ld+json"
    )

@app.get("/entreprises/search")
async def search_by_name(
    request: Request,
    nom: str = Query(..., min_length=2, description="Nom de l'entreprise (recherche partielle)"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    pageSize: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100, description="Taille de page"),
    token_info: dict = Depends(validate_token)
):
    """
    Recherche les entreprises par nom (filtre)
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    search_pattern = f"%{nom}%"

    # Compter le total
    cursor.execute(
        "SELECT COUNT(*) as total FROM unite_legale WHERE denominationUniteLegale LIKE %s",
        (search_pattern,)
    )
    total = cursor.fetchone()["total"]

    # Récupérer la page
    offset = (page - 1) * pageSize
    cursor.execute(
        """SELECT siren, denominationUniteLegale, activitePrincipaleUniteLegale, nomenclatureActivitePrincipaleUniteLegale
        FROM unite_legale WHERE denominationUniteLegale LIKE %s
        LIMIT %s OFFSET %s""",
        (search_pattern, pageSize, offset)
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    items = [to_json_ld(row) for row in rows]
    base_url = str(request.url).split("?")[0]

    return JSONResponse(
        content=create_paginated_response(items, total, page, pageSize, base_url),
        media_type="application/ld+json"
    )

@app.get("/entreprises/filter/activite")
async def filter_by_activity_pattern(
    request: Request,
    pattern: str = Query(..., description="Pattern de code activité (ex: 62% pour tous les codes commençant par 62)"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    pageSize: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100, description="Taille de page"),
    token_info: dict = Depends(validate_token)
):
    """
    Recherche les entreprises avec un filtre par code activité
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Compter le total
    cursor.execute(
        "SELECT COUNT(*) as total FROM unite_legale WHERE activitePrincipaleUniteLegale LIKE %s",
        (pattern,)
    )
    total = cursor.fetchone()["total"]

    # Récupérer la page
    offset = (page - 1) * pageSize
    cursor.execute(
        """SELECT siren, denominationUniteLegale, activitePrincipaleUniteLegale, nomenclatureActivitePrincipaleUniteLegale
        FROM unite_legale WHERE activitePrincipaleUniteLegale LIKE %s
        LIMIT %s OFFSET %s""",
        (pattern, pageSize, offset)
    )
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    items = [to_json_ld(row) for row in rows]
    base_url = str(request.url).split("?")[0]

    return JSONResponse(
        content=create_paginated_response(items, total, page, pageSize, base_url),
        media_type="application/ld+json"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
