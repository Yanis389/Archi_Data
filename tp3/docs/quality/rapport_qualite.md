# Rapport de qualité des données (UC-06, étape 9)

Document **généré** par `python -m quality.controles_qualite` (preuve : `preuves/09_qualite.txt`, tableau complet : `outputs/rapport_qualite.csv`). Les contrôles recalculent tout depuis les fichiers Parquet et les sources ; ils ne reprennent aucun compteur des scripts de production.

**Bilan : 81 contrôles — 72 OK, 2 avertissement(s), 7 observations, 0 échec(s).**

Statuts : `OK` règle respectée · `AVERTISSEMENT` écart connu et documenté, non bloquant · `ECHEC` bloquant · `INFO` observation sans seuil.

## Complétude

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q01 | store_sales | colonnes obligatoires non nulles (ss_sold_date_sk, ss_item_sk, ss_store_sk, ss_ticket_number, ss_quantity, ss_sales_price, ss_ext_sales_price) | 0 | 0 | **OK** |  |
| Q02 | store_returns | colonnes obligatoires non nulles (sr_returned_date_sk, sr_item_sk, sr_ticket_number, sr_return_quantity, sr_return_amt) | 0 | 0 | **OK** |  |
| Q03 | item | colonnes obligatoires non nulles (i_item_sk, i_item_id, i_category) | 0 | 0 | **OK** |  |
| Q04 | store | colonnes obligatoires non nulles (s_store_sk, s_store_id, s_store_name) | 0 | 0 | **OK** |  |
| Q05 | date_dim | colonnes obligatoires non nulles (d_date_sk, d_date, d_year, d_moy) | 0 | 0 | **OK** |  |
| Q06 | reason | colonnes obligatoires non nulles (r_reason_sk, r_reason_desc) | 0 | 0 | **OK** |  |
| Q07 | store_sales | clés facultatives vides | ss_cdemo_sk=238, ss_hdemo_sk=295, ss_addr_sk=448, ss_promo_sk=158 | — | **INFO** | autorisé : client ou promotion absents ; conservé tel quel |
| Q08 | store_returns | clés facultatives vides | sr_cdemo_sk=21, sr_hdemo_sk=15, sr_addr_sk=42, sr_reason_sk=11 | — | **INFO** | autorisé : client ou promotion absents ; conservé tel quel |

## Unicité / clé candidate

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q09 | item | clé i_item_sk unique | 0 | 0 | **OK** | clé de substitution d'une dimension : doit être unique pour que les jointures ne démultiplient pas |
| Q10 | store | clé s_store_sk unique | 0 | 0 | **OK** | clé de substitution d'une dimension : doit être unique pour que les jointures ne démultiplient pas |
| Q11 | date_dim | clé d_date_sk unique | 0 | 0 | **OK** | clé de substitution d'une dimension : doit être unique pour que les jointures ne démultiplient pas |
| Q12 | reason | clé r_reason_sk unique | 0 | 0 | **OK** | clé de substitution d'une dimension : doit être unique pour que les jointures ne démultiplient pas |
| Q13 | date_dim | d_date unique (un jour = une ligne) | 0 | 0 | **OK** |  |
| Q14 | store_sales | clé ss_ticket_number+ss_item_sk unique | 4136 | 0 | **AVERTISSEMENT** | clé candidate NON unique : lignes distinctes (quantités/prix différents), conservées et signalées par qa_cle_dupliquee ; aucune clé naturelle unique sur ces tables |
| Q15 | store_sales | aucune ligne exactement dupliquée (toutes colonnes métier) | 0 | 0 | **OK** |  |
| Q16 | store_returns | clé sr_ticket_number+sr_item_sk unique | 158 | 0 | **AVERTISSEMENT** | clé candidate NON unique : lignes distinctes (quantités/prix différents), conservées et signalées par qa_cle_dupliquee ; aucune clé naturelle unique sur ces tables |
| Q17 | store_returns | aucune ligne exactement dupliquée (toutes colonnes métier) | 0 | 0 | **OK** |  |

## Validité des types

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q18 | store_sales | types Silver = schéma déclaré (23 colonnes) | 0 | 0 | **OK** |  |
| Q19 | store_sales | colonnes de provenance présentes | 0 | 0 | **OK** |  |
| Q20 | store_returns | types Silver = schéma déclaré (20 colonnes) | 0 | 0 | **OK** |  |
| Q21 | store_returns | colonnes de provenance présentes | 0 | 0 | **OK** |  |
| Q22 | item | types Silver = schéma déclaré (22 colonnes) | 0 | 0 | **OK** |  |
| Q23 | item | colonnes de provenance présentes | 0 | 0 | **OK** |  |
| Q24 | store | types Silver = schéma déclaré (29 colonnes) | 0 | 0 | **OK** |  |
| Q25 | store | colonnes de provenance présentes | 0 | 0 | **OK** |  |
| Q26 | date_dim | types Silver = schéma déclaré (28 colonnes) | 0 | 0 | **OK** |  |
| Q27 | date_dim | colonnes de provenance présentes | 0 | 0 | **OK** |  |
| Q28 | reason | types Silver = schéma déclaré (3 colonnes) | 0 | 0 | **OK** |  |
| Q29 | reason | colonnes de provenance présentes | 0 | 0 | **OK** |  |

## Cohérence

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q30 | store_sales | quantité > 0 | 0 | 0 | **OK** |  |
| Q31 | store_sales | prix de vente et montant de ligne >= 0 | 0 | 0 | **OK** |  |
| Q32 | store_sales | montant de ligne = quantité x prix (tolérance 0.02) | 0 | 0 | **OK** |  |
| Q33 | store_sales | prix de vente <= prix catalogue | 0 | 0 | **OK** |  |
| Q34 | store_returns | quantité retournée > 0 et montant remboursé >= 0 | 0 | 0 | **OK** |  |
| Q35 | date_dim | d_year et d_moy cohérents avec d_date | 0 | 0 | **OK** |  |
| Q36 | item | prix courant > 0 | 0 | 0 | **OK** |  |
| Q37 | store_returns | retour jamais antérieur à la vente d'origine | 0 | 0 | **OK** |  |
| Q38 | store_returns | quantité retournée <= quantité vendue (ticket + article) | 0 | 0 | **OK** |  |
| Q39 | store_sales | ventes à prix nul (signalées, conservées) | 3324 | — | **INFO** | valeur atypique mais plausible : jeu synthétique, voir règles de nettoyage |
| Q40 | store_sales | ventes sous le coût d'achat (signalées, conservées) | 462852 | — | **INFO** | valeur atypique mais plausible : jeu synthétique, voir règles de nettoyage |
| Q41 | store_sales | marges nettes négatives (signalées, conservées) | 495971 | — | **INFO** | valeur atypique mais plausible : jeu synthétique, voir règles de nettoyage |
| Q42 | store | dates de fermeture s_closed_date_sk | 5 magasins sur 12 antérieures à leurs ventes | — | **INFO** | colonne inexploitable (voir exploration) : exclue de toute logique |
| Q43 | gold.ventes_par_categorie_annee | parts de CA : somme par année = 100 % (±0,05) | 0 | 0 | **OK** |  |
| Q44 | gold.taux_retour_par_magasin | taux de retour compris entre 0 et 100 % | 0 | 0 | **OK** |  |

## Volumes

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q45 | store_sales | lignes Bronze = lignes du fichier source | 667579 | 667579 | **OK** |  |
| Q46 | store_sales | lignes Bronze = Silver + quarantaine (aucun doublon exact : 0 constaté en exploration) | 667579 | 667579 | **OK** |  |
| Q47 | store_returns | lignes Bronze = lignes du fichier source | 37902 | 37902 | **OK** |  |
| Q48 | store_returns | lignes Bronze = Silver + quarantaine (aucun doublon exact : 0 constaté en exploration) | 37902 | 37902 | **OK** |  |
| Q49 | item | lignes Bronze = lignes du fichier source | 17820 | 17820 | **OK** |  |
| Q50 | item | lignes Bronze = Silver + quarantaine (aucun doublon exact : 0 constaté en exploration) | 17820 | 17820 | **OK** |  |
| Q51 | store | lignes Bronze = lignes du fichier source | 12 | 12 | **OK** |  |
| Q52 | store | lignes Bronze = Silver + quarantaine (aucun doublon exact : 0 constaté en exploration) | 12 | 12 | **OK** |  |
| Q53 | date_dim | lignes Bronze = lignes du fichier source | 109573 | 109573 | **OK** |  |
| Q54 | date_dim | lignes Bronze = Silver + quarantaine (aucun doublon exact : 0 constaté en exploration) | 109573 | 109573 | **OK** |  |
| Q55 | reason | lignes Bronze = lignes du fichier source | 35 | 35 | **OK** |  |
| Q56 | reason | lignes Bronze = Silver + quarantaine (aucun doublon exact : 0 constaté en exploration) | 35 | 35 | **OK** |  |
| Q57 | quarantaine | lignes mises à l'écart (toutes tables) | 0 | — | **INFO** | aucune sur les données réelles ; le fonctionnement des règles de rejet est démontré par tests/test_regles_silver.py |
| Q58 | gold.ventes_par_magasin_mois | lignes = couples (magasin, année, mois) distincts des ventes | 720 | 720 | **OK** |  |
| Q59 | gold.retours_par_motif | lignes = motifs distincts des retours (+ « non renseigné ») | 36 | 36 | **OK** |  |

## Intégrité référentielle

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q60 | store_sales | ss_sold_date_sk -> date_dim.d_date_sk : valeurs sans parent | 0 | 0 | **OK** |  |
| Q61 | store_sales | ss_store_sk -> store.s_store_sk : valeurs sans parent | 0 | 0 | **OK** |  |
| Q62 | store_sales | ss_item_sk -> item.i_item_sk : valeurs sans parent | 0 | 0 | **OK** |  |
| Q63 | store_returns | sr_returned_date_sk -> date_dim.d_date_sk : valeurs sans parent | 0 | 0 | **OK** |  |
| Q64 | store_returns | sr_store_sk -> store.s_store_sk : valeurs sans parent | 0 | 0 | **OK** |  |
| Q65 | store_returns | sr_item_sk -> item.i_item_sk : valeurs sans parent | 0 | 0 | **OK** |  |
| Q66 | store_returns | sr_reason_sk -> reason.r_reason_sk : valeurs sans parent | 0 | 0 | **OK** | clés vides ignorées (comptées en complétude) |
| Q67 | store_returns | (ticket, article) retourné -> vente d'origine : retours sans vente | 0 | 0 | **OK** |  |

## Réconciliation Gold/Silver

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q68 | gold.ventes_par_magasin_mois | SUM(chiffre_affaires) = SUM(ss_net_paid) Silver | 1150529586.37 | 1150529586.37 | **OK** |  |
| Q69 | gold.ventes_par_magasin_mois | SUM(nb_lignes) = lignes Silver | 667579 | 667579 | **OK** |  |
| Q70 | gold.ventes_par_categorie_annee | SUM(chiffre_affaires) = SUM(ss_net_paid) Silver | 1150529586.37 | 1150529586.37 | **OK** |  |
| Q71 | gold.ventes_par_categorie_annee | SUM(quantite_vendue) = SUM(ss_quantity) Silver | 33755474 | 33755474 | **OK** |  |
| Q72 | gold.retours_par_motif | SUM(nb_lignes_retour) = lignes Silver store_returns | 37902 | 37902 | **OK** |  |
| Q73 | gold.retours_par_motif | SUM(montant_rembourse) = SUM(sr_return_amt) Silver | 36688696.43 | 36688696.43 | **OK** |  |
| Q74 | gold.taux_retour_par_magasin | SUM(chiffre_affaires) = SUM(ss_net_paid) Silver | 1150529586.37 | 1150529586.37 | **OK** |  |
| Q75 | gold.taux_retour_par_magasin | SUM(quantite_retournee) = SUM(sr_return_quantity) Silver | 972092 | 972092 | **OK** |  |

## Réconciliation Gold/Jour 1

| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |
|---|---|---|---|---|---|---|
| Q76 | gold.ventes_par_magasin_mois | CA magasin = KPI J1 (SUM(ss_net_paid), DuckDB) | 1150529586.37 | 1150529586.37 | **OK** |  |
| Q77 | gold.ventes_par_magasin_mois | tickets = KPI J1 (COUNT DISTINCT ticket) | 89100 | 89100 | **OK** |  |
| Q78 | gold.ventes_par_categorie_annee | quantités vendues = KPI J1 | 33755474 | 33755474 | **OK** |  |
| Q79 | gold.retours_par_motif | montant retourné = KPI J1 | 36688696.43 | 36688696.43 | **OK** |  |
| Q80 | gold.taux_retour_par_magasin | taux de retour en quantité global (%) = KPI J1 | 2.88 | 2.88 | **OK** |  |
| Q81 | gold.ventes_par_magasin_mois | CA de chacun des 12 magasins = KPI J1 | 0 | 0 | **OK** |  |

## Bilan (sujet §4.12.3)

**Règles respectées** : tous les contrôles `OK` ci-dessus (complétude des données obligatoires, unicité des clés de dimensions, types conformes, cohérence interne des montants, volumes conservés de la source au Silver, intégrité référentielle sans orphelin, réconciliation exacte Gold ↔ Silver et Gold ↔ KPI du Jour 1).

**Anomalies restantes** (avertissements) : 

- Q14 `store_sales` : clé ss_ticket_number+ss_item_sk unique — résultat 4136. clé candidate NON unique : lignes distinctes (quantités/prix différents), conservées et signalées par qa_cle_dupliquee ; aucune clé naturelle unique sur ces tables
- Q16 `store_returns` : clé sr_ticket_number+sr_item_sk unique — résultat 158. clé candidate NON unique : lignes distinctes (quantités/prix différents), conservées et signalées par qa_cle_dupliquee ; aucune clé naturelle unique sur ces tables
- Valeurs atypiques signalées mais conservées (observations `INFO`) : ventes à prix nul, ventes sous le coût d'achat, marges négatives.
- `store.s_closed_date_sk` : incohérent, exclu de toute logique.

**Données mises à l'écart** : 0 ligne en quarantaine sur les données réelles (aucune ne viole les règles de rejet). Le mécanisme est démontré sur des anomalies injectées (`tests/test_regles_silver.py`, `preuves/06_test_regles_silver.txt`). Aucune ligne n'est supprimée : les 4 136 lignes de `store_sales` à clé répétée sont conservées et signalées (`qa_cle_dupliquee`).

**Limites des contrôles** :

- Périmètre : lot initial (`data`) uniquement, 6 tables sur 36 ; le lot `data_refresh` n'est pas contrôlé (2005 reste incomplet : ventes jusqu'au 13/12/2005).
- Les noms de colonnes sont **déduits** de TPC-DS (les `.dat` n'ont pas d'en-tête) : les jointures valident le sens des clés, pas celui des libellés.
- La cohérence métier ne peut pas dire si une valeur atypique est « vraie » : 69 % de ventes sous le coût d'achat sont cohérentes avec elles-mêmes mais pas avec la réalité commerciale (jeu synthétique).
- La réconciliation avec le Jour 1 compare deux moteurs (DuckDB et Spark) sur les **mêmes fichiers et la même interprétation** des colonnes : elle détecte une erreur de calcul, pas une erreur d'interprétation commune.
- Seuils choisis par nous (tolérance d'arrondi 0,02) faute de référentiel officiel de qualité.
- TPCx-BB est synthétique : aucun résultat n'a de valeur de performance ni de conformité à un benchmark officiel.

**Corrections éventuellement nécessaires** : (1) traiter `data_refresh` pour compléter 2005 ; (2) ajouter une clé technique de ligne sur `store_sales` et `store_returns` si une clé unique devient nécessaire ; (3) ne pas utiliser `s_closed_date_sk` sans validation du formateur.