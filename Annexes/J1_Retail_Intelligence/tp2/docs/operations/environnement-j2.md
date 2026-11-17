# Fiche d'environnement technique et Hadoop/HDFS : TP J2

Auteur : HELALI Yanis. Date des manipulations : 17/11/2026. Preuves : `preuves/j2/hadoop/`, `preuves/j2/hdfs/`.

## Environnement (réellement utilisé)

| Élément | Valeur relevée | Preuve |
|---|---|---|
| Hôte | macOS, processeur ARM, Docker Desktop (4 Go RAM, 8 CPU) | `hadoop/01_systeme.txt` |
| OS du conteneur | Ubuntu 24.04.5 LTS, noyau linuxkit aarch64 | idem |
| Java Hadoop | OpenJDK 17.0.21 (`/usr/lib/jvm/java-17-openjdk-arm64`) | `hadoop/02_java.txt` |
| Java NiFi | OpenJDK 21.0.13 (`/usr/lib/jvm/java-21-openjdk-arm64`) | idem |
| Hadoop | 3.5.0 (binaire `aarch64`), `/opt/hadoop` | `hadoop/04_hadoop_version.txt` |
| NiFi | 2.12.0, `/opt/nifi`, https://localhost:8443/nifi | `nifi/03_decouverte_nifi.txt` |
| Python | 3.12.3 | `hadoop/01_systeme.txt` |
| Utilisateur | `etudiant` (non administrateur) pour HDFS et NiFi | idem |
| Ports | NameNode 9000 (RPC) et 9870 (Web), DataNode 9864/9866/9867, 2nd NameNode 9868, NiFi 8443 | `hadoop/10_etat_services.txt` |

Archives vérifiées par somme SHA-512 publiée (Hadoop, NiFi) et SHA-1 (NAR Maven) : `hadoop/03_verification_archives.txt`.

**Écart au sujet** : NiFi 2.x ne livre plus `PutHDFS` dans la distribution binaire. Les NAR `nifi-hadoop-nar` et `nifi-hadoop-libraries-nar` 2.12.0 ont été ajoutés dans `/opt/nifi/lib` (Dockerfile). Le processeur est ensuite apparu (`nifi/03_decouverte_nifi.txt`).

## Hadoop et HDFS

- Mode **pseudo-distribué mono-nœud** (`fs.defaultFS=hdfs://localhost:9000`, `dfs.replication=1`). Environnement pédagogique, **pas** un cluster de production ni hautement disponible.
- Processus (`jps`) : NameNode, DataNode, SecondaryNameNode. Un DataNode vivant, 0 mort, safe mode OFF, 0 bloc manquant (`hadoop/08`, `09`, `10`).
- `hdfs namenode -format` exécuté **une seule fois**, sur un répertoire vide (`hadoop/07_format_namenode.txt`). Jamais relancé.
- Capacité : 223,63 Go configurés. Taille de bloc 128 Mo.
- Journaux au démarrage : 0 ERROR/FATAL. Les WARN (secret HTTP aléatoire, un seul répertoire NameNode) sont attendus en mode pédagogique (`hadoop/11`).
- Sécurité : authentification `simple` (identité déclarée, non vérifiée). Les permissions HDFS sont actives (`hdfs/03`), mais un utilisateur peut usurper une identité via `HADOOP_USER_NAME` : c'est une limite de ce mode.

## Rôles

- **NameNode** : métadonnées (arborescence, droits, liste des blocs et leur emplacement). Ne stocke pas les données.
- **DataNode** : stocke les blocs, envoie des rapports de blocs et des signaux de vie au NameNode.
- Les clients interrogent le NameNode puis lisent/écrivent directement sur les DataNodes.

## Commandes HDFS exécutées (étape 2)

`hdfs dfsadmin -report`, `hdfs dfs -ls /`, `-mkdir -p`, `-ls`, `-du -h`, `-df -h`, `-stat`, `-getfacl`, `fsck`. Sorties : `hdfs/01` à `hdfs/05`, `hdfs/11`. Erreurs provoquées volontairement (`hdfs/04`) : chemin inexistant (`No such file or directory`) et écriture par un utilisateur tiers (`Permission denied: user=invite`), sans conséquence (rien créé).

## Services au démarrage

Ordre suivi (section 1.8 du sujet) : SSH, `start-dfs.sh`, `jps` et `dfsadmin -report`, puis NiFi (Java 21). Arrêt : flux NiFi, NiFi, HDFS (voir `README.md`).
