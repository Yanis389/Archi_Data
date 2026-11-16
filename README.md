# TP Jour 1 — Retail Intelligence Platform

**IPSSI — Mastère Développement, Data & IA (5e année) — Module Architecture Data**
Auteur : Yanis (Yanis389)

Ce dépôt contient les productions du TP J1 : **UC-01** (besoin métier et exploration des sources)
et **UC-02** (conception et justification d'une architecture Data) pour l'enseigne fictive
*Retail Intelligence*, à partir du kit de données **TPCx-BB**.

## Principe de travail

Le TP impose de distinguer ce qui est **observé** de ce qui est **supposé**. Tous les livrables
utilisent donc les statuts suivants :

| Statut | Signification |
|---|---|
| **Vérifié** | Observé directement dans un fichier (via les scripts de ce dépôt) |
| **Déduit** | Obtenu par analyse, avec justification |
| **Hypothèse** | À confirmer par une vérification complémentaire |
| **Non disponible** | Absent des données examinées |
| **À valider** | Nécessite une décision ou une vérification du formateur |

Les chiffres (volumes, nulls, doublons, couverture des jointures) ne sont **pas saisis à la main** :
ils sont produits par `scripts/profiler_tpcx_bb.py` et conservés dans les dossiers `preuves/`.

## Structure

```
J1_Retail_Intelligence/
|-- README.md
|-- scripts/                      # profilage, génération des xlsx et des PDF
|-- 01_UC01_besoin_exploration/   # UC-01 + preuves/
|-- 02_UC02_architecture/         # UC-02 + preuves/
|-- 03_complementaire/            # UC-C1, UC-C2 (facultatif)
|-- 04_avance/                    # UC-A1 (facultatif)
`-- 05_contribution_individuelle/
```

## Données

Les données TPCx-BB (~1 Go, 36 fichiers) ne sont **pas versionnées** : elles sont lues depuis
`../retail_project/` (dossiers `data/` et `data_refresh/`). Voir `.gitignore`.

## Reproduire les preuves

```bash
python3 -m venv .venv && .venv/bin/pip install openpyxl markdown
.venv/bin/python scripts/profiler_tpcx_bb.py --data ../retail_project --out 01_UC01_besoin_exploration/preuves
```

## Avancement

- [x] Squelette du dépôt
- [ ] UC-01 — exploration et qualification des données
- [ ] UC-01 — cadrage métier, KPI, limites
- [ ] UC-02 — architecture
- [ ] Compléments (UC-C1, UC-C2)
