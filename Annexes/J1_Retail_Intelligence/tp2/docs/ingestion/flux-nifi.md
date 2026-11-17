# Flux d'ingestion NiFi (UC-04)

Construit et piloté par l'API REST de NiFi 2.12.0 (`ingestion/nifi/nifi_flux.py`), visible dans l'interface. Captures : `preuves/j2/nifi/captures/`. Identifiants non versionnés.

## Découverte (étape 6, `nifi/03_decouverte_nifi.txt`)

NiFi 2.12.0, https://localhost:8443/nifi, accès monoutilisateur (identifiants générés au premier démarrage, certificat auto-signé `CN=localhost`, accès publié sur 127.0.0.1 uniquement). 304 types de processeurs ; `GetFile`, `PutHDFS` (nifi-hadoop-nar), `UpdateAttribute`, `RouteOnAttribute`, `LogAttribute`, `RetryFlowFile` disponibles.

| Concept | Rôle |
|---|---|
| FlowFile | unité de donnée : contenu + attributs (`filename`, `path`, `fileSize`, `uuid`…) |
| Processor | opération (lire, écrire, router, modifier un attribut) |
| Connection | file d'attente entre deux processeurs, porte une ou plusieurs relations (`success`, `failure`) |
| Process Group | conteneur logique d'un flux (un groupe par flux ici) |
| Controller Service | service partagé (aucun nécessaire pour ce flux) |
| Provenance Repository | historique des événements de chaque FlowFile (RECEIVE, SEND, DROP…) |

## Flux obligatoire : `GetFile -> PutHDFS` (étape 8) — exécuté

```
GetFile --success--> PutHDFS --failure--> LogAttribute --success--> PutFile (quarantaine)
                       `-- success : auto-terminé
```

| Processeur | Propriétés principales |
|---|---|
| GetFile | Input Directory `/data/nifi/input` ; Keep Source File `false` ; Recurse `false` ; planification 10 s |
| PutHDFS | Hadoop Configuration Resources `/opt/hadoop/etc/hadoop/core-site.xml,…/hdfs-site.xml` ; Directory `/retail-lake/raw/nifi` ; Conflict Resolution `fail` (jamais d'écrasement silencieux) |
| LogAttribute | niveau `warn`, préfixe `ECHEC-PutHDFS ` |
| PutFile | Directory `/data/nifi/error`, Conflict `fail` |

Essai : copie de travail de `data_refresh/store_sales.dat` (922 171 octets) dans `/data/nifi/input`, démarrage PutHDFS puis GetFile. Résultat (`nifi/05_execution_flux_obligatoire.txt`) : le dossier d'entrée est vidé, `/retail-lake/raw/nifi/store_sales.dat` (922 171 o) existe, checksum HDFS identique au dépôt manuel UC-03, SHA-256 et 6 632 lignes identiques à la source. L'original du kit est intact. Capture : `02_flux_obligatoire_apres_execution.png`.

## Tableau des erreurs et corrections (étape 10)

| # | Erreur provoquée | Observation | Correction | Preuve |
|---|---|---|---|---|
| A | `Input Directory` = dossier inexistant | GetFile **invalide** (triangle jaune), message « Directory does not exist », impossible à démarrer ; modification refusée tant que démarrage demandé (HTTP 400) | arrêt, `Input Directory=/data/nifi/input`, redémarrage : valide, Running | `nifi/06`, `07`, captures 08, 09 |
| B | `chmod 000` sur le fichier d'entrée | **Aucune erreur** : GetFile ignore le fichier illisible (resté dans le dossier, aucun bulletin, aucune mention dans `nifi-app.log`). Échec silencieux : à surveiller par l'âge des fichiers en entrée | `chmod 644` : fichier pris en charge au cycle suivant | `nifi/10` |
| C | Relance avec un fichier déjà déposé (non prévue au départ, conséquence de la correction de B) | PutHDFS route en `failure` (« file with same name already exists »), FlowFile pénalisé, attributs écrits par LogAttribute, contenu conservé dans `/data/nifi/error`. HDFS **non écrasé** | résolution humaine : le fichier est identique, pas de re-dépôt | `nifi/11`, `12`, capture 10 |

Aucun droit HDFS partagé n'a été modifié pendant ces tests.

## Flux enrichi (étape 12, avec défis AV-01 à AV-04 en bonus, hors socle) — exécuté sur un lot de 10 fichiers

```
GetFile(lot, récursif) -> UpdateAttribute(tpcxbb.table/lot/extension, date, chemin source)
 -> CryptographicHashContent(SHA-256) -> RouteOnAttribute(contrôles : taille>0, extension dat|csv, nom valide)
      |matched -> RouteOnAttribute(domaine : ventes, retours, clients, produits, stocks, navigation, avis, referentiels)
      |             |domaine reconnu -> PutHDFS(/retail-lake/raw/nifi/<domaine>/<lot>/<table>)
      |             |unmatched -> UpdateAttribute(rejet.motif) -> LogAttribute -> PutFile(/data/nifi/error/<date>)
      |unmatched -> UpdateAttribute(rejet.motif) ----^
 PutHDFS --failure--> RetryFlowFile(3 tentatives) --retry--> PutHDFS ; retries_exceeded --> rejet
```

Lot : 7 fichiers TPCx-BB réels du refresh + 3 fichiers **synthétiques** `SYNTHETIQUE_*` (vide, extension `.txt`, table inconnue), créés uniquement pour éprouver les rejets et non issus de TPCx-BB. Résultat (`nifi/15_flux_enrichi_lot_multi_fichiers.txt`) : 10 lus, 7 déposés dans HDFS par domaine, 3 rejetés avec motif dans `/data/nifi/error/2026-11-17/` (2 par les contrôles, 1 par le routage). Les compteurs et files finissent à 0.

**Non exécuté** : la branche `PutHDFS failure -> RetryFlowFile` (aucune panne HDFS simulée dans le flux enrichi) est conçue mais non éprouvée. La provenance du flux enrichi n'a pas été capturée.

## Limites

Un `GetFile` avec `Keep Source File=false` consomme l'entrée : l'original doit être ailleurs. Pas d'idempotence automatique (la stratégie `fail` évite l'écrasement mais produit un `failure` à chaque relance). Le contrôle « structure attendue » (nombre de colonnes) n'est pas implémenté dans NiFi. Un flux fonctionnel ne garantit pas la qualité métier.
