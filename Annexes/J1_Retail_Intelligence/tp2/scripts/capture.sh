#!/usr/bin/env bash
# Exécute une commande dans l'environnement du TP et conserve une preuve datée :
#   en-tête (date, utilisateur, hôte), commande exacte, sortie complète (stdout + stderr), code retour.
#
# Usage (dans le conteneur, en tant qu'etudiant) :
#   /work/scripts/capture.sh preuves/j2/hdfs/01_ls_racine.txt 'hdfs dfs -ls /'
# Le chemin de preuve est relatif à /work (dossier tp2/ du dépôt monté dans le conteneur).
set -u
. /etc/profile.d/tp2-env.sh 2>/dev/null || true

out="$1"; shift
cmd="$*"
case "$out" in /*) ;; *) out="/work/$out" ;; esac
mkdir -p "$(dirname "$out")"

{
  echo "# TP J2 - preuve générée le $(date '+%Y-%m-%d %H:%M:%S %Z') - utilisateur=$(whoami) - hôte=$(hostname)"
  echo "\$ $cmd"
  bash -c "$cmd" 2>&1
  echo "# code retour : $?"
} > "$out"
cat "$out"
