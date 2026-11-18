# Jointures et agrégations (UC-06, étape 5)

Preuve d'exécution : `preuves/07_gold.txt`, détail chiffré : `outputs/jointures_verifiees.csv`.

**Règle appliquée** : aucune jointure sur « noms de colonnes similaires ». Chaque relation a été validée par les
contrôles d'intégrité référentielle (0 orphelin, voir `docs/quality/rapport_qualite.md`), et chaque jointure est
re-vérifiée à l'exécution par `jointure_verifiee` : clé du côté « un » unique, nombre de lignes avant = après,
lignes non rapprochées comptées. Une jointure N:1 qui multiplierait ou perdrait des lignes **arrête le traitement**.

| # | Jointure | Colonnes | Relation / cardinalité attendue | Lignes avant → après | Non rapprochées | Verdict |
|---|---|---|---|---|---|---|
| 1 | `store_sales` → `date_dim` (inner) | `ss_sold_date_sk` = `d_date_sk` | N:1 : plusieurs lignes de vente par jour | 667 579 → 667 579 | 0 | OK |
| 2 | résultat 1 → `store` (inner) | `ss_store_sk` = `s_store_sk` | N:1 : plusieurs ventes par magasin | 667 579 → 667 579 | 0 | OK |
| 3 | `store_sales` → `item` (inner) | `ss_item_sk` = `i_item_sk` | N:1 : plusieurs lignes par produit | 667 579 → 667 579 | 0 | OK |
| 4 | `store_returns` → `reason` (**left**) | `sr_reason_sk` = `r_reason_sk` | N:1 ; 11 retours sans motif conservés | 37 902 → 37 902 | 0 (11 clés vides) | OK |
| 5 | ventes par magasin → retours par magasin (inner) | `magasin_sk` = `retour_magasin_sk` | 1:1 : un agrégat par magasin de chaque côté | 12 → 12 | 0 | OK |
| 6 | résultat 5 → `store` (inner) | `magasin_sk` = `s_store_sk` | N:1 | 12 → 12 | 0 | OK |

Pourquoi ces clés : ce sont les clés de substitution (`*_sk`) des tables de dimension TPC-DS, uniques côté dimension
(vérifié : `cle_droite_unique = True` pour les 6 jointures). `i_item_sk` est unique (17 820 lignes, 17 820 `i_item_sk`
distincts) : la jointure ne démultiplie donc pas les ventes, contrairement à une jointure sur `i_item_id` qui, elle,
peut porter plusieurs versions d'un produit (historisation de type 2).

Jointure **non faite volontairement** : `web_clickstreams` ↔ ventes (aucun identifiant fiable, voir sujet §4.8.4),
et `store_returns` ↔ `store_sales` au niveau ligne : la clé (ticket, article) n'est pas unique côté ventes
(4 136 lignes en excès), la jointure multiplierait les lignes. Les retours et les ventes sont donc agrégés par magasin
**avant** d'être rapprochés (jointure 5).

## Agrégations et granularité

| Jeu Gold | Regroupement | Granularité (1 ligne =) | Lignes | Unicité de la granularité |
|---|---|---|---|---|
| `ventes_par_magasin_mois` | magasin, année, mois | un magasin sur un mois | 720 | vérifiée |
| `ventes_par_categorie_annee` | catégorie, année | une catégorie sur une année | 45 | vérifiée |
| `retours_par_motif` | motif | un motif de retour | 36 | vérifiée |
| `taux_retour_par_magasin` | magasin | un magasin | 12 | vérifiée |

Règles de calcul de chaque mesure : `docs/data-dictionary/gold_jeux_analytiques.md`.
