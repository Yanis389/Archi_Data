# TP Jour 3 — Transformation, qualité et organisation des données (UC-06)

IPSSI — Mastère Développement, Data & IA (5e année) — Module Architecture Data. Auteur : HELALI Yanis.
Périmètre : **partie obligatoire (UC-06)**. L'UC-05 (NoSQL / HBase) et la partie avancée (Lakehouse) ne sont **pas traitées**.

## Ce qui a été réellement exécuté

- Chaîne **Raw → Bronze → Silver → Gold** en Python / PySpark 4.3.0 sur 6 sources TPCx-BB du lot initial :
  `store_sales`, `store_returns`, `item`, `store`, `date_dim`, `reason`.
- **Mode d'exécution : Spark local (`local[*]`) sur macOS, lecture depuis un répertoire local, sans HDFS ni cluster.** C'est la solution de
  repli du sujet (§9.2, « HDFS indisponible »). Les traitements **ne sont pas** des traitements exécutés sur un cluster HDFS.
- Aucun notebook Jupyter : l'exploration et les traitements sont des **scripts** (le sujet accepte « notebook ou script », §4.6.3).
- Non traités : lot `data_refresh`, tables web / stocks / clients, UC-05, partie avancée.

## Résultats

| Étape | Résultat | Preuve |
|---|---|---|
| Environnement | Python 3.13.1, Java 20.0.1, Spark 4.3.0, `local[*]` ; incident `PYTHON_VERSION_MISMATCH` reproduit et corrigé | `preuves/00_*`, `preuves/01_*` |
| Inventaire | 6 sources, 832 921 lignes au total ; nombre de champs mesuré sur chaque ligne ; clé (ticket, article) non unique (+4 136 sur `store_sales`, +158 sur `store_returns`) | `preuves/02_inventaire.txt` |
| Exploration | 0 ligne exactement dupliquée ; 69 % des ventes sous le coût d'achat ; `s_closed_date_sk` inexploitable | `preuves/03_exploration.txt` |
| Bronze | lignes Bronze = lignes sources, 6 tables sur 6 | `preuves/04_bronze.txt` |
| Silver | Bronze = Silver + quarantaine + doublons retirés, 6 tables sur 6 ; 0 ligne rejetée sur les données réelles | `preuves/05_silver.txt` |
| Règles de rejet | démontrées sur des anomalies **injectées** (les données réelles n'en contiennent pas) | `preuves/06_test_regles_silver.txt` |
| Gold | 4 jeux, granularité unique vérifiée, 6 jointures vérifiées (lignes avant = après) | `preuves/07_gold.txt` |
| Parquet | relu : schéma identique, 0 ligne différente ; 42,2 Mo contre 144,0 Mo (CSV) et 471,9 Mo (JSON) | `preuves/08_parquet_formats.txt` |
| Qualité | 81 contrôles : 72 OK, 2 avertissements documentés, 7 observations, 0 échec ; Gold identique aux KPI du Jour 1 (DuckDB) | `preuves/09_qualite.txt` |
| Tests finaux | cases §8.1 à §8.5 du sujet | `preuves/10_tests_finaux.txt` |

## Structure

```
tp3/
|-- README.md  requirements.txt  run_all.sh
|-- lib/                  config.py (chemins, paramètres), schemas.py (schémas explicites), spark_utils.py
|-- exploration/          env_check.py, inventaire.py, exploration.py
|-- transformations/      regles.py, bronze.py, silver.py, gold.py, parquet_formats.py
|-- quality/              controles_qualite.py
|-- tests/                test_regles_silver.py (anomalies injectées), test_final_uc06.py (§8.1 à §8.5)
|-- scripts/              capture.sh (preuve datée), generer_dictionnaire_silver.py, repro_erreur_python_worker.py
|-- docs/
|   |-- environment/      fiche_environnement.md
|   |-- data-dictionary/  inventaire_technique.md, dictionnaire_silver.md, gold_jeux_analytiques.md
|   |-- transformations/  regles_nettoyage.md, jointures_et_agregations.md
|   |-- quality/          rapport_qualite.md
|   |-- lakehouse/        parquet_et_formats.md
|   `-- questions_de_recul.md
|-- data/                 bronze/ silver/ quarantaine/ parquet_test/ (générés, non versionnés) ; gold/ (versionné)
|-- outputs/              rapports CSV / JSON générés par les scripts
`-- preuves/              sortie complète de chaque exécution (date, versions, commande, code retour)
```

## Versions et prérequis

Python 3.13 (PySpark exige la même version mineure de Python côté driver et côté workers, voir dépannage), Java : 20.0.1 utilisé et fonctionnel ; les versions Java supportées par la version exacte de Spark sont à vérifier dans sa documentation (Java 17 ou 21 pour Spark 4.x d'après la documentation que nous connaissons),
PySpark 4.3.0 (`requirements.txt`), 8 Go de RAM (`spark.driver.memory=2g`), environ 1 Go de disque libre pour les zones générées.
Données TPCx-BB (~1 Go, hors dépôt) dans `<Archi_Data>/Annexes/retail_project/` (dossier `data/`).

## Reproduction

```bash
cd tp3
./run_all.sh --propre        # crée .venv si besoin, supprime les zones générées, rejoue toute la chaîne
# ou étape par étape (après : python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt && source .venv/bin/activate)
python -m exploration.env_check
python -m exploration.inventaire
python -m exploration.exploration
python -m transformations.bronze
python -m transformations.silver
python -m transformations.gold
python -m transformations.parquet_formats
python -m quality.controles_qualite
python -m unittest tests.test_regles_silver tests.test_final_uc06 -v
```

L'ordre est obligatoire : chaque étape lit la sortie de la précédente. Chaque script se termine avec un code retour non nul en cas d'échec.

## Paramètres, chemins, sorties

| Élément | Valeur |
|---|---|
| Sources (lecture seule) | `<Archi_Data>/Annexes/retail_project/data/<table>/<table>.dat`, surchargeable par la variable `TPCXBB_DIR` |
| Format des sources | texte, séparateur `\|`, sans en-tête, UTF-8 ; noms de colonnes **déduits** de TPC-DS (`lib/schemas.py`) |
| Bronze | `data/bronze/<table>` : copie fidèle, colonnes en texte, provenance (`_source_file`, `_batch`, `_ingested_at`) |
| Silver | `data/silver/<table>` : typé, nettoyé, indicateurs `qa_*`, provenance |
| Quarantaine | `data/quarantaine/<table>` : lignes rejetées avec la ligne brute (JSON) et l'identifiant de règle |
| Gold | `data/gold/<jeu>` : `ventes_par_magasin_mois`, `ventes_par_categorie_annee`, `retours_par_motif`, `taux_retour_par_magasin` |
| Tests d'écriture | `data/parquet_test/` : seul répertoire où `mode("overwrite")` est utilisé sur des copies de test |
| Paramètres Spark | `TP3_SPARK_MASTER` (défaut `local[*]`), `TP3_SPARK_MEMORY` (défaut `2g`), 8 partitions de shuffle (`lib/config.py`) |

Les données volumineuses (Bronze, Silver, quarantaine, copies de test) ne sont pas versionnées (`.gitignore`) : elles se régénèrent avec `run_all.sh`.
Le Gold (quelques Ko) est versionné comme preuve.

## Traçabilité

Chaque jeu permet de retrouver sa source (`_source_file`), son lot et son horodatage d'ingestion (`_batch`, `_ingested_at`), le traitement appliqué
(`_silver_at`, `_regles_version`), les règles (`transformations/regles.py` → `docs/transformations/regles_nettoyage.md`), les contrôles
(`docs/quality/rapport_qualite.md`), son format (Parquet) et sa localisation (tableau ci-dessus). Les jeux Gold portent `_sources` et `_gold_at`.

## Correspondance avec les livrables du sujet (§10.2)

| N° | Livrable | Où |
|---|---|---|
| 1 | Fiche environnement | `docs/environment/fiche_environnement.md` |
| 2 | Inventaire technique | `docs/data-dictionary/inventaire_technique.md`, `outputs/inventaire_*.csv` |
| 3 | Exploration | `exploration/exploration.py` (script), résultats `preuves/03_exploration.txt`, `outputs/profil_colonnes.csv`, `outputs/valeurs_atypiques.csv` |
| 4 | Règles de nettoyage | `docs/transformations/regles_nettoyage.md` (généré depuis `transformations/regles.py`) |
| 5 | Scripts PySpark | `exploration/`, `transformations/`, `quality/` |
| 6 | Données Silver | `data/silver/` (régénérable) et `docs/data-dictionary/dictionnaire_silver.md` |
| 7 | Données Gold | `data/gold/` et `docs/data-dictionary/gold_jeux_analytiques.md` |
| 8 | Données Parquet | toutes les zones ; `docs/lakehouse/parquet_et_formats.md`, `outputs/parquet_relecture.csv`, `outputs/comparaison_formats.csv` |
| 9 | Rapport qualité | `docs/quality/rapport_qualite.md`, `outputs/rapport_qualite.csv` |
| 10 | README | ce fichier |
| 11 | Preuves | `preuves/` |

Questions de recul (§11) : `docs/questions_de_recul.md`.

## Limites connues

- Exécution **locale** sur petits volumes : les durées mesurées ne se transposent pas à un cluster.
- TPCx-BB est **synthétique** : libellés de motifs et descriptions générés aléatoirement, 69 % de ventes sous le coût d'achat, dates de fermeture de
  magasins incohérentes, devise non précisée. Aucun résultat n'a de valeur de performance ni de conformité à un benchmark officiel.
- Les noms de colonnes sont **déduits** de TPC-DS (statut « déduit ») : validés par comptage de champs et jointures, pas par un dictionnaire officiel.
- Le lot initial s'arrête au 13/12/2005 : 2005 et décembre 2005 sont incomplets (le lot `data_refresh` n'est pas traité).
- Aucune ligne n'est rejetée sur les données réelles : les règles de rejet sont démontrées par un test à anomalies injectées, pas par les données.

## Dépannage

| Symptôme | Cause et correction |
|---|---|
| `PYTHON_VERSION_MISMATCH : Python in worker has different version` | les workers PySpark ont pris un autre Python (`python3` du PATH) : déjà corrigé dans `get_spark` (`PYSPARK_PYTHON`) ; reproduction : `scripts/repro_erreur_python_worker.py` |
| `Malformed CSV record` à la lecture | une ligne n'a pas le nombre de champs attendu (lecture FAILFAST volontaire) : vérifier le fichier source et `lib/schemas.py` |
| `FileNotFoundException` sur une source | définir `TPCXBB_DIR` vers le dossier qui contient `data/` |
| `OutOfMemoryError` | augmenter `TP3_SPARK_MEMORY` (ex. `3g`) |
