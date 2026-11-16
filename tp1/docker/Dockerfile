# Environnement Linux / Ubuntu de référence du parcours, pour explorer et profiler TPCx-BB.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends tree file python3 python3-pip ca-certificates \
 && pip3 install --no-cache-dir --break-system-packages "duckdb>=1.1" "openpyxl>=3.1" "markdown>=3.5" \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /work
