# Provenance des données

## Provenance NiFi (étape 11)

Événements du flux obligatoire (`preuves/j2/nifi/13_provenance_evenements.txt`, export `provenance_evenements.json`), fichier `store_sales.dat` :

| id | Heure | Type | Composant | Détail |
|---|---|---|---|---|
| 0 | 12:30:28.601 | RECEIVE | GetFile | `file:/data/nifi/input/store_sales.dat` |
| 1 | 12:30:29.690 | SEND | PutHDFS | `hdfs://localhost:9000/retail-lake/raw/nifi/store_sales.dat` |
| 2 | 12:30:29.691 | ATTRIBUTES_MODIFIED | PutHDFS | |
| 3 | 12:30:29.691 | DROP | PutHDFS | « Auto-Terminated by success Relationship » |

FlowFile `03f0068a-c98f-4e01-9296-ee38d6e4798c`, 922 171 octets, nom `store_sales.dat`. Lignage : `14_provenance_lignage.txt`, captures `11` à `13`.

Deuxième FlowFile (`51d8bf78-adde-4e50-ad01-120e66d1ca7a`, essai de conflit) : RECEIVE 12:39:53, puis SEND vers `/data/nifi/error` (PutFile) 12:40:23 : l'événement montre **par où** il est sorti (quarantaine, pas HDFS).

**Comment reconstituer le parcours** : l'UUID relie tous les événements d'un fichier ; chaque événement donne le composant, l'heure, la taille, l'origine (URI de réception) et la destination (URI d'envoi). On sait donc d'où vient un fichier, quand il a été pris, ce qu'il est devenu et si une branche d'échec a été empruntée. Limite : la rétention du dépôt de provenance est bornée (configuration NiFi) ; elle ne remplace pas un journal d'ingestion durable.

## Provenance côté HDFS (UC-03)

- Attributs étendus sur chaque fichier Raw : `user.tpcxbb.source` (kit, dossier, fichier), `user.tpcxbb.lot`, `user.ingestion.run` (run, horodatage, méthode, utilisateur), `user.sha256` (`hdfs dfs -getfattr -d`, vérifié dans `hdfs/10`).
- Manifestes CSV : `preuves/j2/hdfs/manifeste_{initial,refresh}.csv`, copiés dans `/retail-lake/logs/ingestion/`. Colonnes : run, lot, table, fichier, chemin source, chemin HDFS, format, tailles, lignes, SHA-256 source et HDFS, statut, horodatage, méthode, utilisateur.
- Le fichier `store_sales.dat` initial, déposé à la main avant le script, porte `user.ingestion.run = depot manuel anterieur, constaté par <run>` : sa provenance a été reconstituée, pas enregistrée au moment du dépôt.

## Informations à conserver pour reproduire une ingestion

Version du kit et dossier d'origine, chemin source et destination, lot, SHA-256 et taille, date et auteur, méthode (commande ou flux), versions Hadoop/NiFi/Java, paramètres du flux (export JSON), résultat des contrôles.
