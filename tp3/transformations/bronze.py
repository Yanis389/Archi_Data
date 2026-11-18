"""Zone Bronze : copie fidèle de la source, au plus près de l'original.

Règles :
 - aucune correction, aucun typage : toutes les colonnes restent en texte (STRING), exactement comme lues ;
 - seule modification : le champ vide devient NULL (convention de lecture) ;
 - provenance ajoutée : _source_file (chemin relatif du .dat), _batch (lot), _ingested_at (horodatage) ;
 - format Parquet (la source .dat n'est jamais modifiée).

Contrôle : nombre de lignes Bronze == nombre de lignes du fichier source (lignes de texte).
Sortie : data/bronze/<table>/, outputs/bronze_controle.csv
Lancement : python -m transformations.bronze
"""
import sys

from pyspark.sql import functions as F

from lib import config
from lib.spark_utils import ecrire_csv_rapport, ecrire_parquet, get_spark, lire_brut, log

LOT = "initial"


def main():
    spark = get_spark("TP3-Bronze")
    bilan = []
    for t in config.SOURCES:
        brut = lire_brut(spark, t)
        df = brut.select(
            "*",
            F.regexp_replace(F.col("_metadata.file_path"), "^.*/retail_project/", "retail_project/").alias("_source_file"),
            F.lit(LOT).alias("_batch"),
            F.current_timestamp().alias("_ingested_at"),
        )
        duree = ecrire_parquet(df, config.chemin("bronze", t))
        n_source = spark.read.text(config.chemin_source(t)).count()      # lignes du fichier source
        n_bronze = spark.read.parquet(config.chemin("bronze", t)).count()  # lignes relues en Parquet
        ok = n_source == n_bronze
        log(f"{'OK  ' if ok else 'ECART'} bronze.{t:14s} source={n_source:>8d} bronze={n_bronze:>8d} ({duree:.1f}s)")
        bilan.append({"table": t, "lignes_source": n_source, "lignes_bronze": n_bronze, "ecart": n_source - n_bronze,
                      "statut": "OK" if ok else "ECHEC", "duree_ecriture_s": round(duree, 2),
                      "chemin_bronze": f"data/bronze/{t}"})
    ecrire_csv_rapport(bilan, config.OUTPUTS_DIR / "bronze_controle.csv", list(bilan[0].keys()))
    spark.stop()
    sys.exit(0 if all(b["statut"] == "OK" for b in bilan) else 1)


if __name__ == "__main__":
    main()
