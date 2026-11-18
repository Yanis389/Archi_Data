# Fiche d'environnement — TP Jour 3 (UC-06)

Relevé réel produit par `python -m exploration.env_check` (preuve : `preuves/01_env_check.txt`,
données brutes : `outputs/fiche_environnement.json`).

## Versions observées

| Élément | Valeur observée |
|---|---|
| Système | macOS (Darwin 27.0.0, arm64) |
| Python | 3.13.1 (environnement virtuel `tp3/.venv`) |
| Java | OpenJDK 20.0.1 (Amazon Corretto) |
| PySpark / Spark | 4.3.0 / 4.3.0 |
| Mode d'exécution | `local[*]` (Spark embarqué dans le processus, aucun cluster) |
| Parallélisme par défaut | 8 (8 cœurs CPU) |
| Mémoire machine / driver Spark | 8 Go / 2 Go (`spark.driver.memory=2g`) |
| Disque libre au relevé | 3,7 Go |

## Écart avec l'environnement de référence du sujet

Le sujet vise Ubuntu. Le TP a été exécuté **sur macOS, en local**, sans Docker ni HDFS (le conteneur
Hadoop du Jour 2 n'a pas été relancé). Ce choix correspond aux solutions de repli du §9.2 du sujet
(« HDFS indisponible → lire les données depuis un répertoire local autorisé, en documentant
l'environnement »). **Les traitements n'ont donc pas été exécutés sur un cluster HDFS** : Spark tourne en mode local,
sur les fichiers du lot initial TPCx-BB déposés sur le disque.

Java 20 n'est pas une version LTS. Il a fonctionné sans erreur sur ce périmètre (preuve : `preuves/01_env_check.txt`).
Les versions Java supportées officiellement par Spark 4.3.0 n'ont pas été vérifiées dans sa documentation : pour une
reproduction sûre, utiliser une version LTS (17 ou 21, d'après la documentation de Spark 4.x que nous connaissons).

## Chemins utilisés

| Rôle | Chemin |
|---|---|
| Données sources (lecture seule) | `<Archi_Data>/Annexes/retail_project/data/<table>/<table>.dat` (surchargeable par `TPCXBB_DIR`) |
| Bronze / Silver / Gold | `tp3/data/{bronze,silver,gold}/<jeu>` (Parquet) |
| Lignes mises à l'écart | `tp3/data/quarantaine/<table>` |
| Sorties de test | `tp3/data/parquet_test/` (répertoire dédié, jamais les sources) |
| Rapports générés | `tp3/outputs/` |
| Preuves d'exécution | `tp3/preuves/` |

## Vérifications attendues (§4.4.2) — toutes OK

lancer un interpréteur Python ✔ · initialiser une session Spark ✔ · lire un fichier de test (`reason`, 35 lignes) ✔ ·
afficher un schéma ✔ · écrire un résultat de test dans un répertoire autorisé et le relire ✔ ·
sources non modifiées et sortie distincte des sources ✔.

## Incident rencontré : `PYTHON_VERSION_MISMATCH`

Au premier lancement, Spark a démarré (la JVM fonctionne) mais les workers ont échoué :

```
[PYTHON_VERSION_MISMATCH] Python in worker has different version: 3.15 than that in driver: 3.13
```

Cause : les workers PySpark utilisent le `python3` du PATH. Sur cette machine, il pointe vers Python 3.15 alors que le
venv utilise 3.13. Correction : `lib/spark_utils.get_spark` fixe `PYSPARK_PYTHON` et `PYSPARK_DRIVER_PYTHON` sur
l'interpréteur courant. Reproduction et correction : `scripts/repro_erreur_python_worker.py`,
preuve `preuves/00_erreur_version_python_worker.txt`.
