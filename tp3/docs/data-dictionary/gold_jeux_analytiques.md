# Jeux de données Gold (UC-06, étape 7)

Les 4 jeux Gold sont produits par `python -m transformations.gold` (preuve : `preuves/07_gold.txt`) à partir de la
zone Silver. Ils sont écrits en Parquet dans `data/gold/<jeu>/` et **versionnés** (quelques Ko). Chaque jeu répond à une
question décisionnelle du Jour 1 (`tp1/01_UC01_besoin_exploration`).

**Définition commune du chiffre d'affaires** : `SUM(ss_net_paid)` (montant net payé, taxe exclue), identique au
dictionnaire de KPI du Jour 1. La devise n'est pas précisée dans les données.

Colonnes techniques de chaque jeu : `_sources` (tables Silver utilisées), `_gold_at` (horodatage de calcul),
`_regles_version`.

## 1. `ventes_par_magasin_mois`

| Élément | Description |
|---|---|
| Finalité métier | Suivre l'évolution du CA et comparer les magasins (Q01, Q08, Q10) |
| Sources | `silver.store_sales`, `silver.date_dim`, `silver.store` |
| Granularité | **1 ligne = 1 magasin × 1 mois** (12 magasins × 60 mois = 720 lignes) |
| Dimensions | `magasin_sk`, `magasin_nom`, `magasin_etat`, `annee`, `mois`, `periode` (AAAA-MM) |
| Mesures | `nb_lignes`, `nb_tickets`, `nb_jours_avec_ventes`, `quantite_vendue`, `montant_lignes_brut`, `chiffre_affaires`, `panier_moyen` |
| Règles de calcul | `nb_lignes = COUNT(*)` ; `nb_tickets = COUNT(DISTINCT ss_ticket_number)` ; `quantite_vendue = SUM(ss_quantity)` ; `montant_lignes_brut = SUM(ss_ext_sales_price)` (quantité × prix, avant coupons) ; `chiffre_affaires = SUM(ss_net_paid)` ; `panier_moyen = chiffre_affaires / nb_tickets` |
| Limites | Les ventes du lot `data` s'arrêtent au 13/12/2005 : **décembre 2005 est incomplet** (`nb_jours_avec_ventes` le montre) ; ne pas comparer un mois partiel à un mois complet. Devise inconnue. Les 12 magasins ont des CA très proches : peu de différenciation. |

## 2. `ventes_par_categorie_annee`

| Élément | Description |
|---|---|
| Finalité métier | Identifier les catégories qui génèrent le plus de ventes (Q04) |
| Sources | `silver.store_sales`, `silver.date_dim`, `silver.item` |
| Granularité | **1 ligne = 1 catégorie × 1 année** (9 catégories × 5 ans = 45 lignes) |
| Dimensions | `categorie`, `annee` |
| Mesures | `nb_lignes`, `nb_jours_avec_ventes`, `quantite_vendue`, `chiffre_affaires`, `part_ca_annee_pct` |
| Règles de calcul | `part_ca_annee_pct = 100 × CA de la catégorie / CA de l'année` (fonction fenêtre par année) |
| Limites | Année 2005 incomplète (347 jours). Catégories très concentrées (Music et Books ≈ 72 % du CA). La marge n'est volontairement pas calculée : le prix de vente est inférieur au coût d'achat sur 69 % des lignes (Q11 jugée « non fiable » au Jour 1). |

## 3. `retours_par_motif`

| Élément | Description |
|---|---|
| Finalité métier | Quantifier les retours magasin par motif (Q05) |
| Sources | `silver.store_returns`, `silver.reason` |
| Granularité | **1 ligne = 1 motif de retour** (35 motifs + 1 ligne « Motif non renseigné » = 36 lignes) |
| Dimensions | `motif_sk`, `motif_libelle` |
| Mesures | `nb_lignes_retour`, `quantite_retournee`, `montant_rembourse`, `perte_nette`, `part_lignes_pct` |
| Règles de calcul | `montant_rembourse = SUM(sr_return_amt)` ; `perte_nette = SUM(sr_net_loss)` ; `part_lignes_pct = 100 × lignes du motif / total des lignes de retour` |
| Limites | Jointure **gauche** : les 11 retours sans motif sont conservés sous « Motif non renseigné » au lieu d'être perdus. Les libellés de `reason` sont du texte généré aléatoirement : **les motifs ne sont pas lisibles métier** (limite du jeu synthétique), seule la répartition est exploitable. |

## 4. `taux_retour_par_magasin`

| Élément | Description |
|---|---|
| Finalité métier | Rapporter les retours aux ventes de chaque magasin (Q05, Q08) |
| Sources | `silver.store_sales`, `silver.store_returns`, `silver.store` |
| Granularité | **1 ligne = 1 magasin** (12 lignes) |
| Dimensions | `magasin_sk`, `magasin_nom` |
| Mesures | `quantite_vendue`, `quantite_retournee`, `taux_retour_quantite_pct`, `montant_lignes_brut`, `montant_rembourse`, `taux_retour_montant_pct`, `chiffre_affaires` |
| Règles de calcul | `taux_retour_quantite_pct = 100 × SUM(sr_return_quantity) / SUM(ss_quantity)` ; `taux_retour_montant_pct = 100 × SUM(sr_return_amt) / SUM(ss_ext_sales_price)` (même base « quantité × prix » des deux côtés) |
| Limites | Les retours s'étendent jusqu'en 2007 alors que les ventes s'arrêtent en 2005 : le taux est un cumul sur toute la période, pas un taux par période. Les taux varient peu entre magasins (2,72 % à 3,07 % en quantité) : écarts à interpréter avec prudence. |

## Convention de nommage

- Zones : `data/{bronze,silver,gold,quarantaine}/<jeu>`, un dossier Parquet par jeu.
- Bronze, Silver et quarantaine : nom de la table source (`store_sales`…), colonnes d'origine (préfixe TPC-DS conservé).
- Gold : nom métier en français, `snake_case`, de la forme `<mesure>_par_<dimensions>`.
- Colonnes techniques préfixées `_` (provenance) ; indicateurs de qualité préfixés `qa_` ; colonnes dérivées sans préfixe (`est_version_courante`).
