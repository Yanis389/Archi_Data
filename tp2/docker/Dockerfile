# TP Jour 2 - Environnement de référence (section 1 du sujet) automatisé :
#   Ubuntu 24.04 + OpenJDK 17 (Hadoop) + OpenJDK 21 (NiFi) + Hadoop 3.5.0 (HDFS pseudo-distribué) + NiFi 2.12.0
# Poste de travail : macOS sur processeur ARM -> conteneur Ubuntu aarch64 (Docker Desktop).
# Les archives sont téléchargées depuis downloads.apache.org et vérifiées par leur somme SHA-512 publiée.
FROM ubuntu:24.04

ARG TARGETARCH
ARG HADOOP_VERSION=3.5.0
ARG NIFI_VERSION=2.12.0
ENV DEBIAN_FRONTEND=noninteractive TZ=Europe/Paris LANG=C.UTF-8

# 1.1 Préparation d'Ubuntu + 1.2 deux JDK installés côte à côte
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends \
      wget curl tar unzip openssh-server openssh-client rsync net-tools procps python3 \
      openjdk-17-jdk-headless openjdk-21-jdk-headless \
      sudo tree file less ca-certificates tzdata iproute2 \
 && rm -rf /var/lib/apt/lists/* \
 && ssh-keygen -A && mkdir -p /run/sshd

# Compte de travail non administrateur : HDFS et NiFi tournent sous "etudiant" (pas sous root).
# Seul le démarrage du démon SSH est autorisé en sudo.
RUN useradd -m -s /bin/bash etudiant \
 && echo 'etudiant ALL=(root) NOPASSWD: /usr/sbin/service ssh *' > /etc/sudoers.d/etudiant \
 && chmod 440 /etc/sudoers.d/etudiant

# 1.3 Apache Hadoop (binaire aarch64 publié par Apache sur ARM, binaire standard sinon)
RUN set -eux; cd /tmp; \
    case "${TARGETARCH:-amd64}" in arm64) H=hadoop-${HADOOP_VERSION}-aarch64.tar.gz ;; *) H=hadoop-${HADOOP_VERSION}.tar.gz ;; esac; \
    BASE=https://downloads.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}; \
    wget -q "$BASE/$H" "$BASE/$H.sha512"; \
    echo "$(tr -d ' \n' < $H.sha512 | grep -oiE '[0-9a-f]{128}' | tr A-F a-f)  $H" | sha512sum -c - | tee /opt/verif_archives.txt; \
    tar -xzf "$H"; rm -f "$H" "$H.sha512"; \
    mv hadoop-${HADOOP_VERSION}* /opt/hadoop; rm -rf /opt/hadoop/share/doc; \
    chown -R etudiant:etudiant /opt/hadoop

# 1.6 Apache NiFi 2.x + NAR Hadoop (PutHDFS n'est plus livré dans la distribution binaire de NiFi 2.x :
# les NAR nifi-hadoop-nar et nifi-hadoop-libraries-nar sont récupérés sur Maven Central et vérifiés en SHA-1)
RUN set -eux; cd /tmp; \
    Z=nifi-${NIFI_VERSION}-bin.zip; \
    wget -q "https://downloads.apache.org/nifi/${NIFI_VERSION}/$Z" "https://downloads.apache.org/nifi/${NIFI_VERSION}/$Z.sha512"; \
    echo "$(tr -d ' \n' < $Z.sha512 | grep -oiE '[0-9a-f]{128}' | tr A-F a-f)  $Z" | sha512sum -c - | tee -a /opt/verif_archives.txt; \
    unzip -q "$Z"; rm -f "$Z" "$Z.sha512"; mv nifi-${NIFI_VERSION} /opt/nifi; \
    for n in nifi-hadoop-nar nifi-hadoop-libraries-nar; do \
      U=https://repo1.maven.org/maven2/org/apache/nifi/$n/${NIFI_VERSION}/$n-${NIFI_VERSION}.nar; \
      wget -q "$U" "$U.sha1"; \
      echo "$(cat $n-${NIFI_VERSION}.nar.sha1 | grep -oiE '[0-9a-f]{40}')  $n-${NIFI_VERSION}.nar" | sha1sum -c - | tee -a /opt/verif_archives.txt; \
      mv $n-${NIFI_VERSION}.nar /opt/nifi/lib/; rm -f $n-${NIFI_VERSION}.nar.sha1; \
    done; \
    chown -R etudiant:etudiant /opt/nifi

# 1.4 Configuration HDFS pseudo-distribuée (core-site.xml, hdfs-site.xml) et Java 17 pour Hadoop
COPY conf/core-site.xml conf/hdfs-site.xml /opt/hadoop/etc/hadoop/
RUN set -eux; \
    J17=$(ls -d /usr/lib/jvm/java-17-openjdk-*); J21=$(ls -d /usr/lib/jvm/java-21-openjdk-*); \
    echo "export JAVA_HOME=$J17" >> /opt/hadoop/etc/hadoop/hadoop-env.sh; \
    echo "export HADOOP_HEAPSIZE_MAX=512m" >> /opt/hadoop/etc/hadoop/hadoop-env.sh; \
    printf '%s\n' \
      'export HADOOP_HOME=/opt/hadoop' \
      'export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop' \
      "export JAVA_HOME_HADOOP=$J17" \
      "export JAVA_HOME_NIFI=$J21" \
      'export JAVA_HOME=$JAVA_HOME_HADOOP' \
      'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin' > /etc/profile.d/tp2-env.sh; \
    # .bashrc s'arrête tôt pour les shells non interactifs : les variables sont aussi chargées par /etc/profile
    echo '. /etc/profile.d/tp2-env.sh' >> /home/etudiant/.bashrc; \
    # NiFi : écoute dans le conteneur, publication limitée à 127.0.0.1 côté hôte (docker run -p 127.0.0.1:8443:8443)
    sed -i 's/^nifi.web.https.host=.*/nifi.web.https.host=0.0.0.0/; s/^nifi.web.proxy.host=.*/nifi.web.proxy.host=localhost:8443,127.0.0.1:8443/' \
        /opt/nifi/conf/nifi.properties; \
    mkdir -p /data/nifi/input /data/nifi/archive /data/nifi/error /home/etudiant/hadoop-data/namenode /home/etudiant/hadoop-data/datanode; \
    chown -R etudiant:etudiant /data/nifi /home/etudiant /opt/hadoop/etc/hadoop

WORKDIR /home/etudiant
# Le conteneur démarre seulement le démon SSH (nécessaire à start-dfs.sh) ; HDFS et NiFi sont démarrés
# explicitement par l'étudiant, dans l'ordre du sujet (section 1.8).
CMD ["/bin/bash", "-c", "service ssh start && exec sleep infinity"]
