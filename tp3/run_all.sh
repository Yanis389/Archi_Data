#!/usr/bin/env bash
# Rejoue toute la chaîne UC-06 dans l'ordre et archive une preuve par étape dans preuves/.
# Arrêt au premier échec (set -e). Usage, depuis le dossier tp3/ :
#     ./run_all.sh            # chaîne complète
#     ./run_all.sh --propre   # supprime d'abord data/{bronze,silver,gold,quarantaine,parquet_test} (régénération complète)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3.13 -m venv .venv
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -r requirements.txt
fi

if [ "${1:-}" = "--propre" ]; then
  rm -rf data/bronze data/silver data/gold data/quarantaine data/parquet_test
fi

CAP=scripts/capture.sh
$CAP preuves/01_env_check.txt        'python -m exploration.env_check'
$CAP preuves/02_inventaire.txt       'python -m exploration.inventaire'
$CAP preuves/03_exploration.txt      'python -m exploration.exploration'
$CAP preuves/04_bronze.txt           'python -m transformations.bronze'
$CAP preuves/05_silver.txt           'python -m transformations.silver'
$CAP preuves/05b_dictionnaire_silver.txt 'python scripts/generer_dictionnaire_silver.py'
$CAP preuves/06_test_regles_silver.txt 'python -m unittest tests.test_regles_silver -v'
$CAP preuves/07_gold.txt             'python -m transformations.gold'
$CAP preuves/08_parquet_formats.txt  'python -m transformations.parquet_formats'
$CAP preuves/09_qualite.txt          'python -m quality.controles_qualite'
$CAP preuves/10_tests_finaux.txt     'python -m unittest tests.test_final_uc06 -v'
echo "Chaîne UC-06 terminée : preuves dans tp3/preuves/, rapports dans tp3/outputs/ et tp3/docs/."
