"""Paramètres du TP3 : chemins, sources retenues, constantes.

Aucun chemin n'est codé en dur dans les traitements : tout passe par ce module.
Les données sources (~1 Go, hors dépôt) sont localisées par la variable d'environnement
TPCXBB_DIR, sinon par défaut `<dossier Archi_Data>/Annexes/retail_project`.
"""
import os
from pathlib import Path

TP3_ROOT = Path(__file__).resolve().parents[1]

# --- Entrées (lecture seule : les fichiers sources ne sont jamais modifiés) -----------------------
_defaut_src = TP3_ROOT.parents[1] / "retail_project"
RETAIL_PROJECT = Path(os.environ.get("TPCXBB_DIR", _defaut_src))
RAW_DIR = RETAIL_PROJECT / "data"            # lot initial
RAW_REFRESH_DIR = RETAIL_PROJECT / "data_refresh"   # lot de rafraîchissement (non traité ici)

# --- Sorties -------------------------------------------------------------------------------------
DATA_DIR = TP3_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
QUARANTAINE_DIR = DATA_DIR / "quarantaine"    # lignes mises à l'écart, avec le motif du rejet
PARQUET_TEST_DIR = DATA_DIR / "parquet_test"  # répertoire dédié aux tests d'écriture
OUTPUTS_DIR = TP3_ROOT / "outputs"            # rapports CSV / Markdown générés par les scripts

# --- Sources retenues (étape 2) ------------------------------------------------------------------
SOURCES = ["store_sales", "store_returns", "item", "store", "date_dim", "reason"]

# --- Paramètres de lecture -----------------------------------------------------------------------
SEPARATEUR = "|"
ENCODAGE = "UTF-8"

# --- Paramètres Spark ----------------------------------------------------------------------------
SPARK_MASTER = os.environ.get("TP3_SPARK_MASTER", "local[*]")
SPARK_DRIVER_MEMORY = os.environ.get("TP3_SPARK_MEMORY", "2g")
SHUFFLE_PARTITIONS = "8"   # volumes modestes (< 1 M de lignes par table) : 8 suffisent en local

# --- Seuils de cohérence (étape 4/9) -------------------------------------------------------------
ECART_MONTANT = "0.02"     # tolérance d'arrondi pour quantité x prix = montant de ligne


def chemin(zone: str, nom: str) -> str:
    """Chemin (chaîne) d'un jeu de données dans une zone : bronze, silver, gold, quarantaine."""
    base = {"bronze": BRONZE_DIR, "silver": SILVER_DIR, "gold": GOLD_DIR,
            "quarantaine": QUARANTAINE_DIR}[zone]
    return str(base / nom)


def chemin_source(table: str) -> str:
    return str(RAW_DIR / table / f"{table}.dat")
