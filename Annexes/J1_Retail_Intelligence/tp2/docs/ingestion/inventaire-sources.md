# Inventaire des fichiers TPCx-BB déposés

Source : kit TPCx-BB Tools 1.7.0 fourni par le formateur (cours J2, diapo 18), dossiers `data/` (lot initial) et `data_refresh/` (lot refresh), montés **en lecture seule** dans `/data/tpcxbb`. Aucun fichier n'a été inventé ni modifié. Volume total : **36 fichiers, 1 033 993 587 octets** (977,0 Mo + 9,1 Mo).
Détail complet (chemins, tailles, lignes, SHA-256 source et HDFS, statut) : `preuves/j2/hdfs/manifeste_initial.csv` et `manifeste_refresh.csv`.

## Constats communs (vérifiés sur `store_sales.dat`, détail dans `hdfs/06_inspection_avant_depot.txt`)

- Format `.dat` : texte ASCII, séparateur `|`, **pas d'en-tête**, fins de ligne CRLF. Les noms de colonnes ne figurent pas dans les fichiers : ils sont **déduits** de TPC-DS/BigBench au TP1 (`tp1/scripts/schemas.py`).
- `store_sales.dat` : 667 579 lignes, 23 champs sur chaque ligne, 92 764 700 octets, SHA-256 `7e0a7f16…ed3d2e`.
- Deux `.csv` (`item_marketprices_audit.csv`), séparateur `,`.
- Les données sont synthétiques ; les anomalies relevées au TP1 (prix < coût, doublons de clé) ne sont pas corrigées en Raw.

## Lot initial (`data/`, 24 fichiers, 977,0 Mo)

| Domaine | Fichiers (octets) |
|---|---|
| Ventes | store_sales 92 764 700 ; web_sales 133 790 574 |
| Retours | store_returns 4 337 400 ; web_returns 5 383 513 ; reason 3 105 |
| Clients | customer 13 279 063 ; customer_address 5 387 229 ; customer_demographics 77 753 083 ; household_demographics 155 100 ; income_band 327 |
| Produits | item 6 799 286 ; item_marketprices 4 201 170 ; item_marketprices_audit.csv 273 ; promotion 46 396 |
| Stocks | inventory 424 943 678 (4 blocs HDFS) |
| Navigation et avis | web_clickstreams 178 722 140 ; web_page 8 040 ; web_site 8 838 ; product_reviews 56 355 389 |
| Référentiels | date_dim 15 395 800 ; time_dim 5 107 780 ; store 3 386 ; warehouse 584 ; ship_mode 1 220 |

## Lot refresh (`data_refresh/`, 12 fichiers, 9,1 Mo)

customer 134 360 ; customer_address 54 587 ; inventory 4 292 915 ; item 69 173 ; item_marketprices 42 547 ; item_marketprices_audit.csv 151 009 ; product_reviews 573 685 ; store_returns 48 825 ; store_sales 922 171 (6 632 lignes) ; web_clickstreams 1 821 864 ; web_returns 55 952 ; web_sales 1 378 425.

## Statut du dépôt

| Contrôle | Résultat | Preuve |
|---|---|---|
| Présence | 36/36 fichiers dans `/retail-lake/raw/tpcxbb/{initial,refresh}` | `hdfs/10` (T3) |
| Taille | identique fichier par fichier ; total identique | idem |
| Intégrité | SHA-256 source = SHA-256 relu depuis HDFS, 36/36 | `hdfs/10` (T4) |
| Source conservée | oui, non modifiable (montage lecture seule) | `hdfs/06`, `hdfs/10` |

`store_sales.dat` (initial) a été déposé à la main (`hdfs dfs -put`, `hdfs/07`) puis reconnu identique par le script ; les 35 autres par `ingestion/scripts/depot_hdfs_uc03.sh`. `data_refresh` n'est **pas fusionné** avec `data` (règles de rapprochement non établies, cf. TP1).

## Limites

Nombre de colonnes et types ne sont vérifiés en profondeur que pour `store_sales` ici ; les autres schémas viennent du profilage du TP1. Un fichier d'un même nom existe dans les deux lots : seule l'arborescence (`initial`/`refresh`) les distingue.
