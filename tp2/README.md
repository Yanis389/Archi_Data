# TP Jour 2 — Hadoop, HDFS et ingestion (UC-03, UC-04)

IPSSI — Mastère Développement, Data & IA (5e année) — Module Architecture Data. Auteur : HELALI Yanis.
Périmètre : **partie obligatoire** (socle). Les parties complémentaire et avancée ne sont pas traitées de façon formelle, à l'exception de l'étude des blocs (`preuves/j2/hdfs/12`) et d'un flux enrichi (`docs/ingestion/flux-nifi.md`).

## Ce qui a été réellement exécuté

HDFS 3.5.0 (mono-nœud) et NiFi 2.12.0 réels, dans un conteneur Ubuntu 24.04 aarch64 (`docker/`). Rien n'est simulé. Résultats :

- UC-03 : arborescence `/retail-lake`, **36/36 fichiers** TPCx-BB déposés dans `raw/tpcxbb/{initial,refresh}`, 23 tests OK sur 23, SHA-256 vérifié depuis HDFS.
- UC-04 : flux `GetFile -> PutHDFS` exécuté, 3 erreurs documentées, provenance relevée, flux enrichi exécuté sur 10 fichiers.
- Non exécuté : branche retry du flux enrichi après panne HDFS, parties 2 et 3 facultatives. Pas de solution de repli : NiFi a fonctionné.

## Structure

```
tp2/
|-- README.md
|-- docs/
|   |-- operations/   environnement-j2.md, questions-de-recul.md
|   |-- ingestion/    inventaire-sources.md, flux-nifi.md, provenance.md
|   `-- architecture/ architecture-data-lake.md
|-- docker/           Dockerfile + core-site.xml, hdfs-site.xml
|-- ingestion/
|   |-- scripts/depot_hdfs_uc03.sh      dépôt HDFS contrôlé, manifeste
|   `-- nifi/         nifi_flux.py (construction/pilotage), decouverte_nifi.py
|-- scripts/capture.sh                  exécute une commande et archive la preuve datée
|-- tests/hdfs/test_uc03.sh             tests UC-03
`-- preuves/j2/       hadoop/, hdfs/, nifi/ (sorties de commandes + captures PNG)
```

Les données (~1 Go) ne sont pas dans le dépôt. Aucun mot de passe n'est versionné ; les identifiants NiFi sont lus dans `~/.nifi_credentials` du conteneur.

## Versions

Ubuntu 24.04.5, OpenJDK 17.0.21 (Hadoop) et 21.0.13 (NiFi), Hadoop 3.5.0, NiFi 2.12.0 (+ NAR `nifi-hadoop-nar` et `nifi-hadoop-libraries-nar` 2.12.0), Python 3.12.3.

## Reproduction

```bash
# depuis le dossier qui contient retail_project/ (données TPCx-BB)
docker build -t retail-tp2:hadoop3.5-nifi2.12 tp2/docker
docker run -d --name tp2-retail --hostname tp2-hadoop -p 127.0.0.1:9870:9870 -p 127.0.0.1:8443:8443 \
  -v $PWD/retail_project:/data/tpcxbb:ro -v $PWD/tp2:/work retail-tp2:hadoop3.5-nifi2.12
docker exec -it -u etudiant tp2-retail bash -l
```

Dans le conteneur, en tant que `etudiant` :

```bash
# SSH sans mot de passe (une fois) puis HDFS (Java 17)
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 && cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
hdfs namenode -format -nonInteractive      # PREMIÈRE INSTALLATION UNIQUEMENT : destructif
start-dfs.sh && jps && hdfs dfsadmin -report
# arborescence (voir docs/architecture/architecture-data-lake.md) puis dépôt UC-03
hdfs dfs -mkdir -p /retail-lake/raw/tpcxbb/{initial,refresh} /retail-lake/raw/nifi /retail-lake/bronze/tpcxbb \
  /retail-lake/silver /retail-lake/gold /retail-lake/quality/integrite /retail-lake/logs/ingestion
/work/ingestion/scripts/depot_hdfs_uc03.sh /data/tpcxbb initial
/work/ingestion/scripts/depot_hdfs_uc03.sh /data/tpcxbb refresh
/work/tests/hdfs/test_uc03.sh /data/tpcxbb
# NiFi (Java 21), lancement détaché
export JAVA_HOME=$JAVA_HOME_NIFI
setsid nohup /opt/nifi/bin/nifi.sh start > ~/nifi-start.log 2>&1 < /dev/null &
grep -E "Generated (Username|Password)" /opt/nifi/logs/nifi-app.log    # puis créer ~/.nifi_credentials
. ~/.nifi_credentials               # export NIFI_USERNAME=... NIFI_PASSWORD=...
mkdir -p /data/nifi/{input,archive,error}; cp <copie_de_travail>.dat /data/nifi/input/
python3 /work/ingestion/nifi/nifi_flux.py obligatoire
python3 /work/ingestion/nifi/nifi_flux.py demarrer-proc obligatoire "PutHDFS - ecriture /retail-lake/raw/nifi"
python3 /work/ingestion/nifi/nifi_flux.py demarrer-proc obligatoire "GetFile - lecture /data/nifi/input"
hdfs dfs -ls -h /retail-lake/raw/nifi
```

## Chemins et paramètres non sensibles

| Élément | Valeur |
|---|---|
| HDFS | `hdfs://localhost:9000`, Web http://localhost:9870 |
| Raw UC-03 | `/retail-lake/raw/tpcxbb/{initial,refresh}/<table>/` |
| Raw UC-04 | `/retail-lake/raw/nifi` (obligatoire) ; `/retail-lake/raw/nifi/<domaine>/<lot>/<table>` (enrichi) |
| NiFi | https://localhost:8443/nifi ; entrée `/data/nifi/input` ; rejets `/data/nifi/error` |
| PutHDFS | config `/opt/hadoop/etc/hadoop/{core,hdfs}-site.xml`, conflit `fail` |

## Arrêt (ordre : flux, NiFi, HDFS)

```bash
python3 /work/ingestion/nifi/nifi_flux.py arreter obligatoire
python3 /work/ingestion/nifi/nifi_flux.py arreter enrichi
export JAVA_HOME=$JAVA_HOME_NIFI; /opt/nifi/bin/nifi.sh stop
stop-dfs.sh
```

Note : `nifi.sh stop` a affiché « termination failed » lors d'un essai précoce (NiFi encore en démarrage) ; en cas de doute, vérifier avec `ps` avant de relancer.

## Livrables du sujet (12.6)

1 environnement : `docs/operations/environnement-j2.md` · 2 Hadoop/HDFS : même fiche · 3 inventaire : `docs/ingestion/inventaire-sources.md` · 4 arborescence : `docs/architecture/architecture-data-lake.md` · 5-6 commandes et preuves : `preuves/j2/hdfs/` · 7-9 flux, config, exécution : `docs/ingestion/flux-nifi.md`, `preuves/j2/nifi/` · 10 erreurs : `flux-nifi.md` · 11 provenance : `docs/ingestion/provenance.md` · 12 repli : sans objet · 13 README : ce fichier · questions de recul : `docs/operations/questions-de-recul.md`.

## Limites

Mono-nœud, réplication 1, authentification simple, environnement pédagogique. Les 3 fichiers `SYNTHETIQUE_*` du flux enrichi sont des fichiers de test, pas des données TPCx-BB.
