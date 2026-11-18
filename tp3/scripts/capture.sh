#!/usr/bin/env bash
# Exécute une commande depuis tp3/ avec l'environnement virtuel et conserve une preuve datée :
# en-tête (date, utilisateur, hôte), commande exacte, sortie complète (stdout + stderr), code retour.
#
# Usage (depuis tp3/) :
#   scripts/capture.sh preuves/01_env_check.txt 'python -m exploration.env_check'
set -u
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
[ -f .venv/bin/activate ] && . .venv/bin/activate
export PYSPARK_PYTHON="$(command -v python)"

out="$1"; shift
cmd="$*"
mkdir -p "$(dirname "$out")"

{
  echo "# TP3 - preuve générée le $(date '+%Y-%m-%d %H:%M:%S %Z') - utilisateur=$(whoami) - hôte=$(hostname -s)"
  echo "# python=$(python --version 2>&1) | java=$(java -version 2>&1 | head -1)"
  echo "\$ $cmd"
  # filtre uniquement les barres de progression Spark (\r), pas les messages
  bash -c "$cmd" 2>&1 | tr '\r' '\n' | grep -v -E '^\[Stage [0-9]+:|^\s*$|WARNING: Using incubator|^Using Spark.s default log4j|^To adjust logging level'
  code=${PIPESTATUS[0]}
  echo "# code retour : $code"
} > "$out"
cat "$out"
