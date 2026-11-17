#!/usr/bin/env bash
# Tests d'ingestion NiFi (UC-03) : chaque test affiche OK / KO. Aucun identifiant en clair :
# NIFI_USERNAME / NIFI_PASSWORD viennent de l'environnement (. ~/.nifi_credentials).
# Usage (conteneur) : tests/ingestion/test_nifi_flux.sh
set -uo pipefail
. /etc/profile.d/tp2-env.sh 2>/dev/null || true
pass=0; fail=0
t() { if eval "$2" >/dev/null 2>&1; then echo "[OK] $1"; pass=$((pass+1)); else echo "[KO] $1"; fail=$((fail+1)); fi; }
HERE=$(cd "$(dirname "$0")/../.." && pwd)

t "script de flux présent et syntaxe Python valide" "python3 -m py_compile '$HERE/ingestion/nifi/nifi_flux.py'"
t "identifiants NiFi fournis par l'environnement" "[ -n \"\${NIFI_USERNAME:-}\" ] && [ -n \"\${NIFI_PASSWORD:-}\" ]"
t "aucun mot de passe en clair dans le dépôt" "! grep -rIE 'Generated Password \[[0-9a-f-]{20,}\]' '$HERE' --include='*.md' --include='*.py' --include='*.sh' --include='*.txt'"
t "fichiers ingérés par NiFi présents dans HDFS raw/nifi" "hdfs dfs -ls -R /retail-lake/raw/nifi | grep -q '^-'"
t "provenance exportée (évènements + lignage)" "[ -s '$HERE/preuves/j2/nifi/provenance_evenements.json' ] && [ -s '$HERE/preuves/j2/nifi/provenance_lignage_store_sales.json' ]"
echo "Bilan : $pass OK, $fail KO"; [ $fail -eq 0 ]
