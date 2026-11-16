# Contribution individuelle - TP Jour 1

**Auteur :** *(prénom et nom à compléter)*
**Module :** Architecture Data - IPSSI, Mastère Développement, Data & IA (5e année)

> Ce fichier a un squelette rempli avec des faits vérifiables sur le dépôt. Les passages entre crochets
> `[...]` ne peuvent être écrits que par l'auteur : ce qu'il a lui-même examiné, vérifié et décidé. Ne rien y
> affirmer qui n'ait pas réellement été fait.

## 1. Outils utilisés (fait)

Le travail a été réalisé avec l'assistance de Claude Code (voir les trailers `Co-Authored-By` des commits).
L'exploration des données a utilisé DuckDB, outil hors référentiel du parcours, non retenu dans l'architecture cible.
Les chiffres des livrables sont produits par des scripts reproductibles (`tp1/scripts/`), pas saisis à la main.

## 2. Ce que le dépôt contient (fait)

| Partie | Livrables |
|---|---|
| UC-01 | cadrage métier, questions décisionnelles, dictionnaire de KPI, inventaire des sources, qualification des données, limites et hypothèses, preuves |
| UC-02 | comparaison DW / Data Lake / Lakehouse, architecture cible, schéma des flux, positionnement des composants, gouvernance, local vers Azure, preuves |
| Complémentaire | UC-C1 (processus décisionnel sur les retours), UC-C2 (limites de la BI classique) |
| Avancé | UC-A1 (architecture détaillée, stratégie de données, gouvernance et supervision) |

## 3. Ce que j'ai examiné et contrôlé personnellement

- [Quels fichiers, tables ou résultats j'ai ouverts et relus moi-même.]
- [Quels chiffres j'ai recoupés (par exemple en relançant les scripts ou en comptant dans les fichiers).]
- [Quelles erreurs ou points douteux j'ai repérés.]

## 4. Ce que j'ai décidé ou arbitré

- [Choix d'architecture que je reprends à mon compte et pourquoi : Data Lake en zones Bronze / Silver / Gold, étoile en Gold.]
- [Hypothèses que j'ai acceptées, modifiées ou rejetées.]
- [Éléments que j'ai changés par rapport à la proposition initiale.]

## 5. Points à confirmer avec le formateur

Les statuts « À valider » des livrables : version et provenance du kit, rôle de `data_refresh`, devise, règle de
dédoublonnage des faits (4 136 doublons de clé en magasin), dates de fermeture de magasins incohérentes.

## 6. Ce que je sais expliquer à l'oral

- [Pourquoi le Data Lake plutôt que le Data Warehouse seul, et ses limites.]
- [Pourquoi le prix de vente inférieur au coût d'achat rend la marge non fiable.]
- [Pourquoi les 180 produits d'inventaire absents du référentiel initial posent problème.]
