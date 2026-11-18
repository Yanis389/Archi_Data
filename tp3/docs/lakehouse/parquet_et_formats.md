# Parquet : écriture, relecture et comparaison des formats (UC-06, étape 8)

Preuve d'exécution : `preuves/08_parquet_formats.txt` · chiffres : `outputs/parquet_relecture.csv`,
`outputs/comparaison_formats.csv` · code : `transformations/parquet_formats.py`.

## Où Parquet est utilisé

Toutes les zones sont écrites en Parquet (compression snappy par défaut de Spark) : `data/bronze`, `data/silver`,
`data/gold`, `data/quarantaine`. Les tests d'écriture et de comparaison vont dans un répertoire **dédié**,
`data/parquet_test/` : `mode("overwrite")` n'est jamais appliqué aux sources ni aux zones.

## Relecture vérifiée (§4.11.2)

Un jeu Silver et les 4 jeux Gold ont été copiés en Parquet, relus, puis comparés à l'original :

| Jeu | Lignes écrites → relues | Schéma identique | Lignes différentes (`exceptAll` dans les 2 sens) | Taille |
|---|---|---|---|---|
| `silver.store_sales` | 667 579 → 667 579 | oui | 0 | 44,5 Mo |
| `gold.ventes_par_magasin_mois` | 720 → 720 | oui | 0 | 25,1 Ko |
| `gold.ventes_par_categorie_annee` | 45 → 45 | oui | 0 | 4,7 Ko |
| `gold.retours_par_motif` | 36 → 36 | oui | 0 | 6,2 Ko |
| `gold.taux_retour_par_magasin` | 12 → 12 | oui | 0 | 4,8 Ko |

Le schéma est conservé **avec ses types exacts** (`DECIMAL(12,2)`, `BIGINT`, `DATE`, booléens), les valeurs sont
identiques et exploitables, le répertoire de sortie est identifié.

## Comparaison CSV / JSON / Parquet (même jeu : `silver.store_sales`, 667 579 lignes, 30 colonnes)

| Critère | Source `.dat` (texte pipe) | CSV | JSON | Parquet (snappy) | Parquet (gzip) |
|---|---|---|---|---|---|
| Volume observé | 88,5 Mo (23 col.) | 144,0 Mo | 471,9 Mo | **42,2 Mo** | 32,1 Mo |
| Durée d'écriture | — | 2,1 s | 1,3 s | 1,0 s | 2,3 s |
| Agrégat sur 1 colonne (médiane de 3) | — | 0,49 s | 1,05 s | **0,14 s** | 0,11 s |
| Types retrouvés à la relecture *sans* schéma imposé | aucun (pas d'en-tête) | 13 colonnes sur 30 altérées | 22 sur 30 altérées | **0 sur 30** | 0 sur 30 |
| Organisation | lignes, texte | lignes, texte | lignes, un objet par ligne (noms répétés) | **colonnes**, par groupes de lignes, avec statistiques | idem |
| Lisible à l'œil | oui | oui | oui | non (binaire) | non |

Exemples d'altérations de types : en CSV `ss_wholesale_cost` `decimal(12,2)` → `double` et `ss_ticket_number` `bigint` →
`int` ; en JSON tous les entiers deviennent `bigint`. Un `double` n'est pas adapté aux montants (erreurs d'arrondi dans les sommes).

**Précautions de lecture** : (1) la comparaison porte sur le Silver à 30 colonnes (23 colonnes d'origine + indicateurs `qa_*`
et provenance), pas strictement sur le fichier source à 23 colonnes ; (2) mesures faites en local, sur une seule machine, avec de petits
volumes et 3 répétitions : le **classement** est fiable, les **valeurs absolues** ne se transposent pas à un cluster et varient d'une exécution à l'autre (deux exécutions complètes : CSV 0,46 à 0,49 s, JSON 0,60 à 1,05 s, Parquet 0,14 s ; 1 colonne contre 23 : 6× puis 3,7× plus rapide). Les tailles, elles, sont identiques à chaque exécution ;
(3) l'écriture n'est pas plus rapide en Parquet : l'avantage porte sur le volume, la lecture et les types.

## Pourquoi un format colonne convient aux usages analytiques (preuves)

- **Lecture sélective** : agréger une colonne prend 0,10 s contre 0,37 s pour agréger les 23 colonnes numériques (médianes de 3) :
  Parquet ne lit que les colonnes demandées. En CSV ou JSON, il faut lire et analyser toutes les lignes en entier.
- **Pushdown de filtre** : le plan d'exécution d'un filtre sur `ss_store_sk` ne lit que 3 colonnes (`ReadSchema` réduit)
  et transmet le filtre au lecteur Parquet (`DataFilters` dans `FileScan parquet`, voir la preuve). Les statistiques min/max
  par groupe de lignes permettent de sauter des blocs.
- **Compression** : valeurs d'une même colonne stockées ensemble (peu d'entropie) : 42,2 Mo contre 144 Mo en CSV.
- **Schéma embarqué** : pas de schéma à redonner, pas de type deviné.

## Limites de Parquet seul (démonstration, section 4 du script)

Un dossier Parquet n'est **pas** une table transactionnelle ACID. Démonstration minimale sur un petit jeu :

1. un second lot avec une colonne en plus est **accepté sans erreur** par `append` : par défaut, la relecture ne voit que
   `['id', 'valeur']` (la colonne en plus est invisible sans `mergeSchema`) ;
2. le rejeu du même lot **duplique** les lignes (5 lignes au lieu de 3, `id = 1` en double) : aucune protection ;
3. pas d'historique ni de retour arrière, pas d'isolation entre un écrivain et un lecteur, pas de `UPDATE`/`DELETE`/`MERGE`.

Ces garanties relèvent d'un format de table Lakehouse (Delta Lake, Apache Iceberg, Apache Hudi) qui ajoute un **journal de
transactions** au-dessus de fichiers Parquet. Ce TP n'en installe aucun et ne présente donc pas ses dossiers Parquet comme des tables ACID.
