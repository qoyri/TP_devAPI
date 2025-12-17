#!/bin/bash
set -e

DATA_URL="https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip"
DATA_DIR="/data"
CSV_FILE="$DATA_DIR/StockUniteLegale_utf8.csv"
ZIP_FILE="$DATA_DIR/StockUniteLegale_utf8.zip"
EXPECTED_SIZE=933190259

echo "=== INIT DATA SIREN ==="

# Attendre que MySQL soit prêt
echo "Attente de MySQL..."
until mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" &>/dev/null; do
    echo "MySQL pas encore prêt, attente 5s..."
    sleep 5
done
echo "MySQL est prêt!"

# Vérifier si les données sont déjà chargées
COUNT=$(mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -N -e "SELECT COUNT(*) FROM unite_legale" 2>/dev/null || echo "0")

if [ "$COUNT" -gt 1000000 ]; then
    echo "Données déjà chargées ($COUNT entreprises). Skip."
    exit 0
fi

echo "Données non chargées ou incomplètes ($COUNT). Chargement..."

# Télécharger si nécessaire
if [ ! -f "$CSV_FILE" ]; then
    echo "Téléchargement des données SIREN (~900MB)..."
    echo "Cela peut prendre 5-15 minutes selon votre connexion..."

    # Vérifier si ZIP existe et est complet
    if [ -f "$ZIP_FILE" ]; then
        ACTUAL_SIZE=$(stat -c%s "$ZIP_FILE" 2>/dev/null || echo "0")
        if [ "$ACTUAL_SIZE" -lt "$EXPECTED_SIZE" ]; then
            echo "ZIP incomplet ($ACTUAL_SIZE/$EXPECTED_SIZE bytes), re-téléchargement..."
            rm -f "$ZIP_FILE"
        fi
    fi

    if [ ! -f "$ZIP_FILE" ]; then
        wget --progress=dot:giga -O "$ZIP_FILE" "$DATA_URL"
        echo "Téléchargement terminé!"
    fi

    # Vérifier taille
    ACTUAL_SIZE=$(stat -c%s "$ZIP_FILE")
    echo "Taille du ZIP: $ACTUAL_SIZE bytes (attendu: $EXPECTED_SIZE)"

    echo "Décompression..."
    cd "$DATA_DIR"
    unzip -o "$ZIP_FILE"
    echo "Fichier CSV prêt!"
fi

# Créer la table
echo "Création de la table unite_legale..."
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" <<EOF
DROP TABLE IF EXISTS unite_legale;
CREATE TABLE unite_legale (
    siren VARCHAR(9) PRIMARY KEY,
    denominationUniteLegale VARCHAR(255),
    activitePrincipaleUniteLegale VARCHAR(6),
    nomenclatureActivitePrincipaleUniteLegale VARCHAR(10),
    INDEX idx_activite (activitePrincipaleUniteLegale),
    INDEX idx_denomination (denominationUniteLegale(50))
) ENGINE=InnoDB;
EOF

# Charger les données
echo "Chargement des données (29M lignes, ~5-10 minutes)..."
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" --local-infile=1 "$MYSQL_DATABASE" <<EOF
SET GLOBAL local_infile = 1;
LOAD DATA LOCAL INFILE '$CSV_FILE'
INTO TABLE unite_legale
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(siren, @d1, @d2, @d3, @d4, @d5, @d6, @d7, @d8, @d9, @d10, @d11, @d12, @d13, @d14, @d15, @d16, @d17, @d18, @d19, @d20, @d21, @d22, denominationUniteLegale, @d24, @d25, @d26, @d27, activitePrincipaleUniteLegale, nomenclatureActivitePrincipaleUniteLegale, @d30, @d31, @d32, @d33, @d34);
EOF

# Créer la table de stats pré-calculées pour Spark
echo "Création de la table stats_activite..."
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" <<EOF
DROP TABLE IF EXISTS stats_activite;
CREATE TABLE stats_activite (
    activitePrincipaleUniteLegale VARCHAR(6) PRIMARY KEY,
    siren_count INT NOT NULL,
    INDEX idx_count (siren_count)
) ENGINE=InnoDB;

INSERT INTO stats_activite (activitePrincipaleUniteLegale, siren_count)
SELECT activitePrincipaleUniteLegale, COUNT(*) as siren_count
FROM unite_legale
WHERE activitePrincipaleUniteLegale IS NOT NULL AND activitePrincipaleUniteLegale != ''
GROUP BY activitePrincipaleUniteLegale;
EOF

# Créer tables OAuth2
echo "Création des tables OAuth2..."
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" <<EOF
CREATE TABLE IF NOT EXISTS oauth_clients (
    id VARCHAR(36) PRIMARY KEY,
    secret_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    redirect_uri VARCHAR(500),
    scopes VARCHAR(500) DEFAULT 'read',
    grant_types VARCHAR(200) DEFAULT 'client_credentials',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    token VARCHAR(500) PRIMARY KEY,
    client_id VARCHAR(36) NOT NULL,
    scopes VARCHAR(500),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_expires (expires_at)
);

CREATE TABLE IF NOT EXISTS oauth_codes (
    code VARCHAR(255) PRIMARY KEY,
    client_id VARCHAR(36) NOT NULL,
    redirect_uri VARCHAR(500),
    scopes VARCHAR(500),
    code_challenge VARCHAR(255),
    code_challenge_method VARCHAR(10),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF

# Vérification finale
FINAL_COUNT=$(mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -N -e "SELECT COUNT(*) FROM unite_legale")
STATS_COUNT=$(mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -N -e "SELECT COUNT(*) FROM stats_activite")

echo "=== INIT TERMINÉE ==="
echo "Entreprises chargées: $FINAL_COUNT"
echo "Codes activité: $STATS_COUNT"
