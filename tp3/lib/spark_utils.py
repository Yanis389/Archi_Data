"""Fonctions Spark communes : session, lecture contrôlée des .dat, écriture Parquet, journal."""
import os
import sys
import time
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from lib import config, schemas


def log(message: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def get_spark(nom: str) -> SparkSession:
    """Session Spark locale.

    PYSPARK_PYTHON est forcé sur l'interpréteur courant : sans cela, les workers Spark peuvent
    démarrer avec un autre Python du système et échouer (PYTHON_VERSION_MISMATCH, voir
    preuves/00_erreur_version_python_worker.txt).
    """
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    spark = (
        SparkSession.builder.appName(nom)
        .master(config.SPARK_MASTER)
        .config("spark.driver.memory", config.SPARK_DRIVER_MEMORY)
        .config("spark.sql.shuffle.partitions", config.SHUFFLE_PARTITIONS)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def lire_brut(spark: SparkSession, table: str):
    """Lit le .dat d'une table : sans en-tête, séparateur '|', toutes colonnes en texte.

    Le schéma est imposé (noms attendus, type STRING) et la lecture est en mode FAILFAST : si une
    ligne n'a pas le nombre de champs attendu, Spark échoue au lieu de tronquer ou compléter en
    silence. Les types sont appliqués plus tard (zone Silver), pas ici : c'est ce qui permet de
    mesurer les conversions qui échouent.
    """
    schema = StructType([StructField(c, StringType(), True) for c in schemas.colonnes(table)])
    return (
        spark.read.schema(schema)
        .option("header", False)
        .option("sep", config.SEPARATEUR)
        .option("encoding", config.ENCODAGE)
        .option("mode", "FAILFAST")
        .option("quote", "\u0000")        # aucun caractère de citation dans les .dat TPCx-BB
        .option("emptyValue", None)
        .option("nullValue", "")          # champ vide = NULL
        .csv(config.chemin_source(table))
    )


def ecrire_parquet(df, chemin: str, partition_par=None) -> float:
    """Écrit un DataFrame en Parquet (mode overwrite, uniquement sur data/ dédié au TP).

    Retourne la durée d'écriture en secondes.
    """
    debut = time.time()
    ecrivain = df.write.mode("overwrite")
    if partition_par:
        ecrivain = ecrivain.partitionBy(*partition_par)
    ecrivain.parquet(chemin)
    return time.time() - debut


def taille_octets(chemin) -> int:
    """Taille totale (octets) d'un fichier ou d'un répertoire."""
    from pathlib import Path
    p = Path(chemin)
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def humain(octets: float) -> str:
    for unite in ["o", "Ko", "Mo", "Go"]:
        if octets < 1024:
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return f"{octets:.1f} To"


def nb_nuls(df, colonnes=None):
    """Dict {colonne: nombre de NULL}, calculé en un seul passage."""
    colonnes = colonnes or df.columns
    ligne = df.agg(*[F.sum(F.col(c).isNull().cast("int")).alias(c) for c in colonnes]).first()
    return {c: int(ligne[c] or 0) for c in colonnes}


def lire_type(spark: SparkSession, table: str):
    """Lecture brute + application des types déclarés avec try_cast.

    try_cast renvoie NULL quand la conversion est impossible (au lieu de lever une erreur, ce que
    ferait cast en mode ANSI de Spark 4) : la zone Silver compare ensuite NULL avant/après pour
    détecter les conversions qui échouent.
    """
    brut = lire_brut(spark, table)
    return brut.select(*[F.col(c).try_cast(t).alias(c) for c, t in schemas.SCHEMAS[table]])


def ecrire_csv_rapport(lignes: list, chemin, entetes: list) -> None:
    """Écrit un rapport CSV (séparateur ';', UTF-8) à partir d'une liste de dictionnaires."""
    import csv
    from pathlib import Path
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=entetes, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)
