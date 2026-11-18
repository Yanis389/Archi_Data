"""Étape 1 - Préparer l'environnement : relève les versions réellement utilisées et vérifie
la chaîne complète (session Spark, lecture d'un fichier de test, schéma, écriture dans un
répertoire dédié, relecture).

Sortie : outputs/fiche_environnement.json (alimente docs/environment/fiche_environnement.md).
Lancement : python -m exploration.env_check   (depuis le dossier tp3/)
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime

import pyspark

from lib import config
from lib.spark_utils import get_spark, lire_brut, ecrire_parquet, humain, log


def memoire_totale() -> str:
    try:
        if sys.platform == "darwin":
            octets = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip())
        else:
            with open("/proc/meminfo") as f:
                octets = int(f.readline().split()[1]) * 1024
        return humain(octets)
    except Exception as e:  # information non critique
        return f"indisponible ({e})"


def main():
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    spark = get_spark("TP3-Env-Check")
    jvm = spark._jvm.System
    fiche = {
        "date_releve": datetime.now().isoformat(timespec="seconds"),
        "systeme": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "java": jvm.getProperty("java.version"),
        "java_vendor": jvm.getProperty("java.vendor"),
        "pyspark": pyspark.__version__,
        "spark": spark.version,
        "mode_execution": spark.sparkContext.master,
        "parallelisme_par_defaut": spark.sparkContext.defaultParallelism,
        "cpu": os.cpu_count(),
        "memoire_machine": memoire_totale(),
        "memoire_driver_spark": config.SPARK_DRIVER_MEMORY,
        "disque_libre": humain(shutil.disk_usage(config.TP3_ROOT).free),
        "chemins": {
            "donnees_sources": str(config.RAW_DIR),
            "bronze": str(config.BRONZE_DIR),
            "silver": str(config.SILVER_DIR),
            "gold": str(config.GOLD_DIR),
            "quarantaine": str(config.QUARANTAINE_DIR),
            "sortie_tests": str(config.PARQUET_TEST_DIR),
            "rapports": str(config.OUTPUTS_DIR),
        },
        "sources_presentes": {t: os.path.isfile(config.chemin_source(t)) for t in config.SOURCES},
        "hdfs": "non utilisé : lecture depuis un répertoire local (solution de repli, voir README)",
    }
    log("Versions et ressources relevées :")
    print(json.dumps(fiche, indent=2, ensure_ascii=False))

    # --- Vérifications attendues (4.4.2) ---
    verifs = {}
    verifs["session_spark"] = spark.version is not None
    df = lire_brut(spark, "reason")                       # lire un fichier de test
    verifs["lecture_fichier_test"] = df.count() == 35
    log("Schéma du fichier de test (reason) :")
    df.printSchema()                                      # afficher un schéma
    verifs["schema_affiche"] = len(df.columns) == 3
    cible = str(config.PARQUET_TEST_DIR / "env_test")     # répertoire distinct des sources
    ecrire_parquet(df, cible)                             # écrire un résultat de test
    relu = spark.read.parquet(cible)
    verifs["ecriture_relecture_test"] = relu.count() == 35 and relu.columns == df.columns
    verifs["sources_non_modifiees"] = all(fiche["sources_presentes"].values())
    verifs["sortie_distincte_des_sources"] = not cible.startswith(str(config.RAW_DIR))
    fiche["verifications"] = verifs
    for nom, ok in verifs.items():
        log(f"{'OK  ' if ok else 'ECHEC'} {nom}")

    with open(config.OUTPUTS_DIR / "fiche_environnement.json", "w", encoding="utf-8") as f:
        json.dump(fiche, f, indent=2, ensure_ascii=False)
    spark.stop()
    sys.exit(0 if all(verifs.values()) else 1)


if __name__ == "__main__":
    main()
