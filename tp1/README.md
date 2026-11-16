# TP Jour 1 — Retail Intelligence Platform

**IPSSI — Mastère Développement, Data & IA (5e année) — Module Architecture Data**
Auteur : Yanis (Yanis389)

Ce dépôt contient les productions du TP J1 : **UC-01** (besoin métier et exploration des sources) et **UC-02**
(conception et justification d'une architecture Data) pour l'enseigne fictive *Retail Intelligence*, à partir du
kit de données **TPCx-BB** (~1 Go, 36 fichiers).

> **Transparence.** Ce travail a été réalisé avec l'assistance de Claude Code (voir les trailers
> `Co-Authored-By` des commits). Les chiffres ne sont pas saisis à la main : ils sont produits par des scripts
> reproductibles (voir « Régénérer »).

## Principe de travail

Le TP impose de distinguer ce qui est **observé** de ce qui est **supposé**. Tous les livrables utilisent les statuts :

| Statut | Signification |
|---|---|
| **Vérifié** | Observé directement dans un fichier (via les scripts de ce dépôt) |
| **Déduit** | Obtenu par analyse, avec justification |
| **Hypothèse** | À confirmer par une vérification complémentaire |
| **Non disponible** | Absent des données examinées |
| **À valider** | Nécessite une décision ou une vérification du formateur |

## Structure

```
tp1/
|-- README.md
|-- requirements.txt
|-- scripts/                         # profilage, schémas déduits, génération des livrables
|-- 01_UC01_besoin_exploration/
|   |-- UC01_cadrage_metier.pdf
|   |-- UC01_questions_decisionnelles.pdf
|   |-- UC01_dictionnaire_KPI.xlsx
|   |-- UC01_inventaire_sources.xlsx
|   |-- UC01_qualification_donnees.pdf
|   |-- UC01_limites_et_hypotheses.pdf
|   `-- preuves/                     # CSV, JSON, SVG et journaux générés par le profileur
|-- 02_UC02_architecture/
|   |-- UC02_comparaison_architectures.pdf
|   |-- UC02_architecture_cible.pdf
|   |-- UC02_schema_flux.pdf
|   |-- UC02_positionnement_composants.pdf
|   |-- UC02_gouvernance.pdf
|   |-- UC02_local_vers_azure.pdf
|   `-- preuves/                     # schémas SVG, matrice des composants
`-- 05_contribution_individuelle/
```

## Données

Les données TPCx-BB (~1 Go) ne sont **pas versionnées** : elles sont lues depuis un dossier `retail_project/` hors dépôt
(dossiers `data/` et `data_refresh/`). Voir `.gitignore`. Les `.dat` sont délimités par `|`, sans en-tête :
les noms de colonnes sont **déduits** de TPC-DS / BigBench (`scripts/schemas.py`).

## Régénérer les preuves et les livrables

```bash
# depuis le dossier tp1/ ; <DATA> = chemin vers le dossier retail_project
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 1. Profilage des données -> 01_UC01_besoin_exploration/preuves/ (environ 30 s)
.venv/bin/python scripts/profiler_tpcx_bb.py --data <DATA> --out 01_UC01_besoin_exploration/preuves
# 2. Livrables UC-01
.venv/bin/python scripts/build_uc01_xlsx.py
.venv/bin/python scripts/build_uc01_besoin.py
.venv/bin/python scripts/build_uc01_donnees.py
# 3. Livrables UC-02
.venv/bin/python scripts/build_uc02.py
```

Les PDF sont rendus avec Google Chrome en mode headless (macOS : `/Applications/Google Chrome.app`).
L'exploration a été faite avec **DuckDB** : outil de travail **hors référentiel du parcours**, non retenu dans
l'architecture cible (voir `UC02_positionnement_composants.pdf`).

## Résultats clés de l'UC-01 (extraits des preuves)

- 36 fichiers (34 `.dat`, 2 `.csv`), schéma cohérent pour les 34 `.dat` ; 60 relations sur 61 sans orphelin dans `data`.
- `data_refresh` complète `data` (clés disjointes, année 2005 complétée de 347 à 365 jours).
- Marge non fiable : prix de vente inférieur au coût d'achat sur 69,3 % des lignes magasin.
- Référentiel produit initial incomplet : 180 produits de l'inventaire n'existent que dans `data_refresh/item`.

## Choix d'architecture (UC-02)

**Data Lake en zones Bronze / Silver / Gold (Parquet), zone Gold modélisée en étoile.** Lakehouse (Delta Lake)
et HBase restent facultatifs. Tout est une **conception logique : rien n'est déployé ni testé**, y compris la
déclinaison Azure.
