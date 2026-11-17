# Procédures de reprise (J2)

| Situation | Détection | Reprise |
|---|---|---|
| HDFS arrêté / safe mode | `hdfs dfsadmin -safemode get`, UI NameNode :9870 | `start-dfs.sh` ; attendre `Safe mode is OFF` ; relancer le dépôt (sans écrasement, les fichiers déjà présents sont ignorés) |
| Dépôt HDFS interrompu | `tests/hdfs/test_uc03.sh` (comptes, tailles, SHA-256) | Relancer `ingestion/scripts/depot_hdfs_uc03.sh <kit> <initial\|refresh> [table]` ; vérifier le manifeste CSV |
| NiFi arrêté | `nifi.sh status`, UI :8443 | `nifi.sh start` ; identifiants lus dans `~/.nifi_credentials` (jamais versionnés) ; vérifier que le flux est rétabli puis relancer `ingestion/nifi/nifi_flux.py` |
| Erreur A : dossier source inexistant | Processeur GetFile invalide (validation) | Corriger la propriété *Input Directory*, redémarrer le processeur |
| Erreur B : fichier illisible | Fichier en échec / journal NiFi | Corriger les droits ou remplacer le fichier, rejouer depuis Raw |
| Erreur C : doublon (conflit PutHDFS) | Relation `failure`, journaux | Ne pas écraser : vérifier le contenu, purger la file `failure` après analyse |
| Perte du conteneur | `docker ps` | Reconstruire depuis `docker/Dockerfile` ; ré-ingérer depuis le kit (Raw est rejouable) |

Principe : toute reprise est idempotente et suivie d'une vérification (taille + SHA-256) puis d'une trace dans `preuves/`.
