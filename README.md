# API SIREN - Architecture Microservices

Architecture de services conteneurisée pour l'accès aux données des entreprises françaises (base SIREN).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CADDY (Reverse Proxy HTTPS)                     │
│                              Port 8443                                  │
└───────────┬───────────────────┬───────────────────┬─────────────────────┘
            │                   │                   │
            ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   OAuth2 Server   │ │    MySQL API      │ │    Spark API      │
│  Python/FastAPI   │ │  Python/FastAPI   │ │  Node.js/Express  │
│     Port 4000     │ │     Port 3001     │ │     Port 3002     │
└───────────────────┘ └─────────┬─────────┘ └─────────┬─────────┘
            │                   │                     │
            │                   ▼                     ▼
            │         ┌───────────────────┐ ┌───────────────────┐
            │         │     MySQL 8.0     │ │   Spark Connect   │
            │         │   29M entreprises │ │      Scala        │
            └────────►│     Port 3306     │ │    Port 15002     │
                      └───────────────────┘ └───────────────────┘
```

## Services

| Service | Technologie | Description |
|---------|-------------|-------------|
| `oauth2-server` | Python/FastAPI | Serveur OAuth2 (client_credentials, introspection) |
| `mysql-api` | Python/FastAPI | API REST entreprises (SIREN, nom, activite) |
| `spark-api` | Node.js/Express | API REST statistiques via Spark Connect |
| `caddy` | Go | Reverse proxy HTTPS avec TLS |
| `spark` | Scala | Spark Connect Server |
| `db` | MySQL 8.0 | Base de donnees SIREN |

## Installation

### Prerequis
- Docker et Docker Compose
- ~10 Go d'espace disque (donnees SIREN)
- ~8 Go de RAM recommande

### Demarrage

```bash
# Cloner et demarrer
cd devAPI
docker-compose up -d

# Le premier demarrage telecharge automatiquement les donnees SIREN (~900 Mo)
# et charge 29 millions d'entreprises (~10-15 minutes)

# Suivre la progression
docker logs -f init_data
```

## Utilisation

### 1. Obtenir un token OAuth2

```bash
curl -sk -X POST https://localhost:8443/oauth/token \
  -d "grant_type=client_credentials&client_id=mysql-api-client&client_secret=mysql_api_secret"
```

Reponse:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read"
}
```

### 2. API Entreprises (MySQL)

```bash
TOKEN="votre_token"

# Recherche par SIREN
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/entreprises/siren/552032534"

# Recherche par code activite
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/entreprises/activite/62.01Z"

# Recherche par nom (filtre)
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/entreprises/search?nom=danone"

# Filtre par pattern code activite
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/entreprises/filter/activite?pattern=62%25"
```

### 3. API Statistiques (Spark)

```bash
# Nombre d'entreprises par code activite
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/stats/activites"

# Statistiques filtrees par pattern
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/stats/activites/filter/62"

# Top activites (les plus representees)
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/stats/top-activites?limit=10"

# Bottom activites (les moins representees)
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/stats/bottom-activites?limit=10"
```

## Documentation Swagger

| API | URL |
|-----|-----|
| OAuth2 | https://localhost:8443/docs/oauth |
| Entreprises | https://localhost:8443/docs/mysql |
| Statistiques | https://localhost:8443/docs/spark |

## Format des reponses

Toutes les reponses sont au format **JSON-LD** avec vocabulaire **Hydra** pour la pagination.

### Exemple: Recherche paginee

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "hydra": "http://www.w3.org/ns/hydra/core#",
    "totalItems": "hydra:totalItems",
    "member": "hydra:member"
  },
  "@type": "hydra:Collection",
  "totalItems": 1360,
  "member": [
    {
      "@type": "Organization",
      "siren": "552032534",
      "denominationUniteLegale": "DANONE",
      "activitePrincipale": "70.10Z"
    }
  ],
  "view": {
    "@type": "hydra:PartialCollectionView",
    "first": "?page=1&pageSize=20",
    "next": "?page=2&pageSize=20",
    "last": "?page=68&pageSize=20"
  }
}
```

## Pagination

- **Defaut**: 20 elements par page
- **Parametres**: `page` (1-based), `pageSize` (max 100)

```bash
# Page 2, 50 elements par page
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://localhost:8443/api/entreprises/search?nom=sas&page=2&pageSize=50"
```

## Clients OAuth2 preconfigures

| Client ID | Secret | Usage |
|-----------|--------|-------|
| `mysql-api-client` | `mysql_api_secret` | API Entreprises |
| `spark-api-client` | `spark_api_secret` | API Statistiques |
| `frontend-client` | `frontend_secret` | Application frontend |

## Structure du projet

```
devAPI/
├── docker-compose.yaml      # Orchestration des 6 services
├── Dockerfile               # Spark Connect Server (Scala)
├── my.cnf                   # Configuration MySQL
├── caddy/
│   ├── Caddyfile            # Configuration reverse proxy
│   └── certs/               # Certificats TLS auto-generes
├── oauth2-server/
│   ├── Dockerfile
│   ├── main.py              # Serveur OAuth2 FastAPI
│   └── requirements.txt
├── mysql-api/
│   ├── Dockerfile
│   ├── main.py              # API Entreprises FastAPI
│   └── requirements.txt
├── spark-api/
│   ├── Dockerfile
│   ├── index.js             # API Statistiques Express
│   └── package.json
├── init-data/
│   ├── Dockerfile
│   └── init.sh              # Script auto-telechargement SIREN
└── data/                    # Donnees SIREN (auto-telechargees)
```

## Commandes utiles

```bash
# Demarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arreter
docker-compose down

# Arreter et supprimer les volumes (reset complet)
docker-compose down -v

# Reconstruire apres modification
docker-compose up -d --build
```

## Tests

```bash
# Test complet de l'API
TOKEN=$(curl -sk -X POST https://localhost:8443/oauth/token \
  -d "grant_type=client_credentials&client_id=mysql-api-client&client_secret=mysql_api_secret" \
  | jq -r '.access_token')

# Verifier que tout fonctionne
curl -sk -H "Authorization: Bearer $TOKEN" "https://localhost:8443/api/entreprises/siren/552032534"
curl -sk -H "Authorization: Bearer $TOKEN" "https://localhost:8443/api/stats/top-activites?limit=5"
```

## Licence

Projet academique - TP REST API
