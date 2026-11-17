#!/usr/bin/env bash
# UC-03 - Dépôt manuel des fichiers TPCx-BB dans la zone Raw de HDFS (hdfs dfs -put), avec :
#   - contrôle préalable de la source (présence, lisibilité, taille, lignes, SHA-256) ;
#   - dépôt sans écrasement (un fichier déjà présent n'est jamais remplacé) ;
#   - vérification après dépôt (taille HDFS + SHA-256 relu depuis HDFS) ;
#   - provenance attachée au fichier HDFS (attributs étendus user.*) et manifeste CSV (local + HDFS).
#
# Usage : depot_hdfs_uc03.sh <racine_kit> <initial|refresh> [table ...]
#   sans table : toutes les tables du lot.  Exemple : depot_hdfs_uc03.sh /data/tpcxbb initial store_sales
# Variables : MANIFEST_DIR (défaut /work/preuves/j2/hdfs)
set -uo pipefail
. /etc/profile.d/tp2-env.sh 2>/dev/null || true

KIT=${1:?racine du kit TPCx-BB, ex. /data/tpcxbb}
LOT=${2:?lot : initial ou refresh}
shift 2
case "$LOT" in
  initial) SRC=$KIT/data ;;
  refresh) SRC=$KIT/data_refresh ;;
  *) echo "lot inconnu : $LOT (attendu initial|refresh)" >&2; exit 2 ;;
esac
[ -d "$SRC" ] || { echo "dossier source absent : $SRC" >&2; exit 2; }

DEST=/retail-lake/raw/tpcxbb/$LOT
RUN_ID=uc03_${LOT}_$(date +%Y%m%dT%H%M%S)
MANIFEST_DIR=${MANIFEST_DIR:-/work/preuves/j2/hdfs}
MANIFEST=$MANIFEST_DIR/manifeste_${LOT}.csv
WEBHDFS=http://localhost:9870/webhdfs/v1
mkdir -p "$MANIFEST_DIR"

if [ $# -gt 0 ]; then TABLES=("$@"); else mapfile -t TABLES < <(ls "$SRC"); fi

echo "run_id;lot;table;fichier;chemin_source;chemin_hdfs;format;taille_source;taille_hdfs;lignes_source;sha256_source;sha256_hdfs;statut;horodatage;methode;utilisateur" > "$MANIFEST"

setxattr() { # chemin nom valeur (WebHDFS : évite de relancer une JVM par attribut)
  curl -sf -X PUT -G "$WEBHDFS$1" --data-urlencode "op=SETXATTR" --data-urlencode "xattr.name=$2" \
       --data-urlencode "xattr.value=$3" --data-urlencode "flag=CREATE" --data-urlencode "user.name=$(whoami)" >/dev/null \
  || curl -sf -X PUT -G "$WEBHDFS$1" --data-urlencode "op=SETXATTR" --data-urlencode "xattr.name=$2" \
       --data-urlencode "xattr.value=$3" --data-urlencode "flag=REPLACE" --data-urlencode "user.name=$(whoami)" >/dev/null
}
hdfs_size() { curl -sf "$WEBHDFS$1?op=GETFILESTATUS&user.name=$(whoami)" | python3 -c 'import json,sys; print(json.load(sys.stdin)["FileStatus"]["length"])'; }

ok=0; ko=0; deja=0
for table in "${TABLES[@]}"; do
  for f in "$SRC/$table"/*; do
    [ -f "$f" ] || continue
    nom=$(basename "$f"); ext=${nom##*.}
    cible=$DEST/$table/$nom
    ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
    # 1. contrôle de la source
    if [ ! -r "$f" ]; then
      echo "$RUN_ID;$LOT;$table;$nom;$f;$cible;$ext;;;;;;ECHEC_source_illisible;$ts;hdfs dfs -put;$(whoami)" >> "$MANIFEST"; ko=$((ko+1)); continue
    fi
    taille=$(stat -c %s "$f"); lignes=$(wc -l < "$f"); sha_src=$(sha256sum "$f" | cut -d' ' -f1)
    # 2. dépôt sans écrasement
    hdfs dfs -mkdir -p "$DEST/$table"
    if hdfs dfs -test -e "$cible"; then
      sha_hdfs=$(hdfs dfs -cat "$cible" | sha256sum | cut -d' ' -f1); t_hdfs=$(hdfs_size "$cible")
      if [ "$sha_hdfs" = "$sha_src" ]; then
        statut=DEJA_PRESENT_identique; deja=$((deja+1))
        # provenance complétée sans écraser d'éventuels attributs existants (flag CREATE seul)
        for kv in "user.tpcxbb.source=TPCx-BB Tools 1.7.0 (kit formateur) / ${SRC#$KIT/}/$table/$nom" \
                  "user.tpcxbb.lot=$LOT" "user.ingestion.run=depot manuel anterieur, constate par $RUN_ID;$ts" \
                  "user.sha256=$sha_src"; do
          curl -sf -X PUT -G "$WEBHDFS$cible" --data-urlencode "op=SETXATTR" --data-urlencode "xattr.name=${kv%%=*}" \
               --data-urlencode "xattr.value=${kv#*=}" --data-urlencode "flag=CREATE" --data-urlencode "user.name=$(whoami)" >/dev/null || true
        done
      else statut=CONFLIT_present_different_non_ecrase; ko=$((ko+1)); fi
    else
      if hdfs dfs -put "$f" "$cible"; then
        # 3. vérification après dépôt
        t_hdfs=$(hdfs_size "$cible"); sha_hdfs=$(hdfs dfs -cat "$cible" | sha256sum | cut -d' ' -f1)
        if [ "$t_hdfs" = "$taille" ] && [ "$sha_hdfs" = "$sha_src" ]; then statut=DEPOSE_verifie; ok=$((ok+1))
        else statut=ECHEC_verification; ko=$((ko+1)); fi
        # 4. provenance attachée au fichier
        setxattr "$cible" user.tpcxbb.source "TPCx-BB Tools 1.7.0 (kit formateur) / ${SRC#$KIT/}/$table/$nom"
        setxattr "$cible" user.tpcxbb.lot "$LOT"
        setxattr "$cible" user.ingestion.run "$RUN_ID;$ts;hdfs dfs -put;$(whoami)"
        setxattr "$cible" user.sha256 "$sha_src"
      else
        t_hdfs=; sha_hdfs=; statut=ECHEC_put; ko=$((ko+1))
      fi
    fi
    echo "$RUN_ID;$LOT;$table;$nom;$f;$cible;$ext;$taille;$t_hdfs;$lignes;$sha_src;$sha_hdfs;$statut;$ts;hdfs dfs -put;$(whoami)" >> "$MANIFEST"
    printf '%-32s %-30s %12s o  %s\n' "$table" "$nom" "$taille" "$statut"
  done
done

# le manifeste est lui-même conservé dans la zone logs du Data Lake
hdfs dfs -mkdir -p /retail-lake/logs/ingestion
hdfs dfs -put -f "$MANIFEST" "/retail-lake/logs/ingestion/${RUN_ID}_manifeste.csv"
echo "----"
echo "run=$RUN_ID  déposés_vérifiés=$ok  déjà_présents_identiques=$deja  échecs_ou_conflits=$ko"
echo "manifeste : $MANIFEST  et  /retail-lake/logs/ingestion/${RUN_ID}_manifeste.csv"
[ "$ko" -eq 0 ]
