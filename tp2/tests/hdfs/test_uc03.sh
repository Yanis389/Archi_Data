#!/usr/bin/env bash
# Tests UC-03 (section 15.1 du sujet) + contrôles de l'étape 5 : chaque test affiche OK / KO et sa preuve.
# Usage (conteneur, etudiant) : tests/hdfs/test_uc03.sh /data/tpcxbb
set -uo pipefail
. /etc/profile.d/tp2-env.sh 2>/dev/null || true
KIT=${1:-/data/tpcxbb}
pass=0; fail=0
t() { # libellé  commande-de-test
  if eval "$2" >/tmp/t.out 2>&1; then echo "[OK] $1"; pass=$((pass+1)); else echo "[KO] $1"; fail=$((fail+1)); fi
  sed 's/^/       /' /tmp/t.out | head -${3:-6}
}

echo "== T1 Accès HDFS"
t "le NameNode répond et n'est pas en safe mode" "hdfs dfsadmin -safemode get | grep -q OFF && hdfs dfs -test -d /"
t "au moins un DataNode vivant" "hdfs dfsadmin -report -live | grep -E '^Live datanodes \([1-9]'"

echo "== T2 Création de répertoires : arborescence attendue présente"
for d in raw/tpcxbb/initial raw/tpcxbb/refresh raw/nifi bronze/tpcxbb silver gold quality logs/ingestion; do
  t "/retail-lake/$d" "hdfs dfs -test -d /retail-lake/$d" 0
done

echo "== T3 Dépôt de fichier : tous les fichiers du kit sont présents avec la même taille"
attendus=$(find "$KIT/data" "$KIT/data_refresh" -type f | wc -l)
presents=$(hdfs dfs -count /retail-lake/raw/tpcxbb | awk '{print $2}')
t "nombre de fichiers : kit=$attendus HDFS=$presents" "[ $attendus -eq $presents ]"
src_octets=$(find "$KIT/data" "$KIT/data_refresh" -type f -printf '%s\n' | awk '{s+=$1} END {print s}')
hdfs_octets=$(hdfs dfs -count /retail-lake/raw/tpcxbb | awk '{print $3}')
t "volume total : kit=$src_octets o  HDFS=$hdfs_octets o" "[ $src_octets -eq $hdfs_octets ]"
hdfs dfs -ls -R /retail-lake/raw/tpcxbb | awk '$1 !~ /^d/ {print $5, $8}' | sed 's#/retail-lake/raw/tpcxbb/initial#data#; s#/retail-lake/raw/tpcxbb/refresh#data_refresh#' | sort -k2 > /tmp/hdfs_tailles
(cd "$KIT" && find data data_refresh -type f -printf '%s %p\n' | sort -k2) > /tmp/src_tailles
t "taille identique fichier par fichier (36 comparaisons)" "diff /tmp/src_tailles /tmp/hdfs_tailles && echo identiques"

echo "== T4 Lecture ou récupération : intégrité par somme de contrôle"
ok_sha=$(awk -F';' 'NR>1 && $11==$12 && $11!=""' /work/preuves/j2/hdfs/manifeste_initial.csv /work/preuves/j2/hdfs/manifeste_refresh.csv | wc -l)
t "SHA-256 source = SHA-256 relu depuis HDFS (manifestes) : $ok_sha / $attendus" "[ $ok_sha -eq $attendus ]"
rm -f /tmp/recup_item.dat
t "récupération contrôlée (hdfs dfs -get) de item.dat puis comparaison octet à octet" \
  "hdfs dfs -get /retail-lake/raw/tpcxbb/initial/item/item.dat /tmp/recup_item.dat && cmp /tmp/recup_item.dat $KIT/data/item/item.dat && sha256sum /tmp/recup_item.dat $KIT/data/item/item.dat"
rm -f /tmp/recup_item.dat
t "re-vérification indépendante du manifeste (store_sales relu maintenant)" \
  "[ \$(hdfs dfs -cat /retail-lake/raw/tpcxbb/initial/store_sales/store_sales.dat | sha256sum | cut -d' ' -f1) = \$(sha256sum $KIT/data/store_sales/store_sales.dat | cut -d' ' -f1) ]"
t "lecture : 2 premières lignes de web_sales.dat (refresh)" "(set +o pipefail; hdfs dfs -cat /retail-lake/raw/tpcxbb/refresh/web_sales/web_sales.dat 2>/dev/null | head -2 | cut -c1-110) | grep ."
t "fsck : aucun bloc manquant ou corrompu sous /retail-lake" "hdfs fsck /retail-lake 2>/dev/null | grep -E 'Status: HEALTHY|Total blocks|Missing blocks:|Corrupt blocks:'" 8

echo "== T5 Permissions cohérentes avec l'usage"
t "raw, gold, quality, logs fermés à others (drwxr-x---)" "hdfs dfs -ls -d /retail-lake/raw /retail-lake/gold /retail-lake/quality /retail-lake/logs | awk '{print \$1, \$8}' > /tmp/perm; cat /tmp/perm; ! grep -v '^drwxr-x---' /tmp/perm" 5
t "fichiers Raw en lecture seule pour groupe et others (-rw-r--r--)" "[ \$(hdfs dfs -ls -R /retail-lake/raw/tpcxbb | awk '\$1 !~ /^d/ && \$1 != \"-rw-r--r--\"' | wc -l) -eq 0 ]"
t "un utilisateur tiers ne peut pas écrire dans Raw" "! HADOOP_USER_NAME=invite hdfs dfs -touchz /retail-lake/raw/tpcxbb/initial/intrus"
t "provenance attachée aux fichiers (attributs étendus)" "hdfs dfs -getfattr -d /retail-lake/raw/tpcxbb/refresh/store_sales/store_sales.dat" 7
t "source originale conservée et non modifiable" "[ -f $KIT/data/store_sales/store_sales.dat ] && ! touch $KIT/data/store_sales/store_sales.dat 2>/dev/null"

echo "----"
echo "Bilan UC-03 : $pass OK, $fail KO"
[ "$fail" -eq 0 ]
