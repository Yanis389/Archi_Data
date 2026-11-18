"""Reproduit l'erreur PYTHON_VERSION_MISMATCH rencontrée au premier lancement (voir README, dépannage).

Session Spark créée SANS fixer PYSPARK_PYTHON : si le `python3` du PATH système n'a pas la même version
mineure que le Python du venv, les workers refusent de démarrer. La correction est dans
lib/spark_utils.get_spark (PYSPARK_PYTHON = interpréteur courant).
Usage : PYSPARK_PYTHON= python scripts/repro_erreur_python_worker.py
"""
import os
os.environ.pop("PYSPARK_PYTHON", None)
from pyspark.sql import SparkSession
spark = SparkSession.builder.master("local[1]").config("spark.ui.enabled", "false").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
try:
    spark.createDataFrame([("a", 1)], ["k", "v"]).show()
except Exception as e:
    print("ERREUR REPRODUITE :", str(e).strip().splitlines()[-2:])
finally:
    spark.stop()
