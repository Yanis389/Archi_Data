# Arborescence du Data Lake HDFS

Créée par `hdfs dfs -mkdir -p` (`preuves/j2/hdfs/05_creation_arborescence.txt`, vérifiée dans l'explorateur Web : `hadoop/captures/03_explorateur_retail_lake.png`).

```
/retail-lake/                 
|-- raw/              750   sources conservées telles que reçues
|   |-- tpcxbb/
|   |   |-- initial/<table>/<table>.dat    lot data/      (24 fichiers, dépôt manuel UC-03)
|   |   `-- refresh/<table>/<table>.dat    lot data_refresh/ (12 fichiers, UC-03)
|   `-- nifi/                              dépôts automatisés UC-04 (distincts de l'UC-03)
|       `-- <domaine>/<lot>/<table>/…      flux enrichi
|-- bronze/tpcxbb/    755   (vide : alimentée au Jour 3)
|-- silver/           755   (vide)
|-- gold/             750 + ACL lecture groupe « analystes » (vide)
|-- quality/integrite/ 750  contrôles qualité et d'intégrité
`-- logs/ingestion/   750   manifestes d'ingestion (CSV horodatés)
```

Droits : `raw`, `gold`, `quality`, `logs` fermés à « others » (`drwxr-x---`). Fichiers Raw en `-rw-r--r--`. Les zones Bronze et Silver restent vides à ce stade : les contenus des Jours 3 et 4 n'existent pas encore.

Écart avec le cours (diapo 30, `bronze/tpcxbb/data|data_refresh`) : la convention du sujet (section 12.2.3) est conservée, avec `initial`/`refresh` sous `raw`, ce qui revient au même (lots séparés, jamais fusionnés).

## Justifications

- **Conserver les sources** : rejouer un traitement, auditer, comparer deux dates, corriger une erreur de transformation sans perdre l'original. Raw est en lecture seule.
- **Raw et Bronze** : Raw = octets reçus, inchangés (même nom, même format). Bronze = même contenu logique mais structuré pour l'exploitation (format colonne type Parquet, en-têtes, métadonnées d'ingestion), sans nettoyage métier.
- **Silver** : données typées, dédoublonnées, harmonisées, anomalies documentées. **Gold** : jeux préparés par besoin métier (modèle en étoile du TP1, KPI validés).
- **Séparer données, qualité, journaux** : droits différents (analystes lisent Gold, pas les logs), cycle de vie différent (journaux conservés, Gold reconstruit), et un contrôle qualité ne pollue pas les données métier.
- **Provenance** : (1) chemin HDFS qui porte le lot et la table ; (2) attributs étendus `user.tpcxbb.source`, `user.tpcxbb.lot`, `user.ingestion.run`, `user.sha256` posés sur chaque fichier Raw ; (3) manifeste CSV copié dans `logs/ingestion` ; (4) provenance NiFi pour les dépôts UC-04.

## Convention de nommage retenue (CO-02, en bref)

`/retail-lake/<zone>/<source>/<lot>/<table>/<fichier>` ; noms en minuscules sans accent, nom de table TPCx-BB conservé ; lot = `initial` ou `refresh` ; date de réception dans le manifeste et l'attribut `user.ingestion.run`, pas dans le chemin.
