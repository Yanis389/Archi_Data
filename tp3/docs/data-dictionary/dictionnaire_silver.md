# Dictionnaire des données Silver (UC-06, étape 6)

Généré par `scripts/generer_dictionnaire_silver.py` : les types sont lus dans les fichiers Parquet Silver. Les sens métier sont **déduits** de TPC-DS (les `.dat` n'ont ni en-tête ni dictionnaire fourni). « — » : colonne conservée mais non utilisée dans ce TP.

Convention de nommage : un jeu Silver porte le nom de sa table source ; les colonnes d'origine gardent leur nom TPC-DS (préfixe de table) ; `qa_*` = indicateur de qualité ; `_*` = provenance ; `est_*` = colonne dérivée.
Provenance de chaque ligne : `_source_file`, `_batch`, `_ingested_at` (Bronze), `_silver_at` et `_regles_version` (Silver). Les lignes rejetées ne sont pas perdues : `data/quarantaine/<table>` (ligne brute JSON + règles en cause).

## silver.store_sales

- Chemin : `data/silver/store_sales` (Parquet) · 667 579 lignes · 32 colonnes
- Granularité : une ligne = une ligne d'article sur un ticket de caisse magasin
- Clé candidate : `ss_ticket_number+ss_item_sk`
- Colonnes obligatoires (rejet si vides) : `ss_sold_date_sk`, `ss_item_sk`, `ss_store_sk`, `ss_ticket_number`, `ss_quantity`, `ss_sales_price`, `ss_ext_sales_price`

| Colonne | Type | Description |
|---|---|---|
| `ss_sold_date_sk` | int | Date de la vente (clé vers date_dim) |
| `ss_sold_time_sk` | int | Heure de la vente (clé vers time_dim, non chargée) |
| `ss_item_sk` | int | Produit vendu (clé vers item) |
| `ss_customer_sk` | int | Client (clé vers customer, non chargée) |
| `ss_cdemo_sk` | int | — |
| `ss_hdemo_sk` | int | — |
| `ss_addr_sk` | int | — |
| `ss_store_sk` | int | Magasin (clé vers store) |
| `ss_promo_sk` | int | Promotion appliquée (facultatif) |
| `ss_ticket_number` | bigint | Numéro de ticket de caisse |
| `ss_quantity` | int | Quantité vendue sur la ligne |
| `ss_wholesale_cost` | decimal(12,2) | Coût d'achat unitaire |
| `ss_list_price` | decimal(12,2) | Prix catalogue unitaire |
| `ss_sales_price` | decimal(12,2) | Prix de vente unitaire |
| `ss_ext_discount_amt` | decimal(12,2) | Remise totale de la ligne |
| `ss_ext_sales_price` | decimal(12,2) | Montant de la ligne (quantité x prix de vente) |
| `ss_ext_wholesale_cost` | decimal(12,2) | Coût d'achat total de la ligne |
| `ss_ext_list_price` | decimal(12,2) | Montant de la ligne au prix catalogue |
| `ss_ext_tax` | decimal(12,2) | Taxe de la ligne |
| `ss_coupon_amt` | decimal(12,2) | Montant des coupons |
| `ss_net_paid` | decimal(12,2) | Montant net payé, hors taxe (base du chiffre d'affaires) |
| `ss_net_paid_inc_tax` | decimal(12,2) | Montant net payé, taxe incluse |
| `ss_net_profit` | decimal(12,2) | Marge nette de la ligne (net payé - coût d'achat) ; atypique, voir règles |
| `qa_cle_dupliquee` | boolean | Indicateur qualité : la clé (ticket, article) apparaît plusieurs fois (lignes distinctes conservées) |
| `qa_prix_nul` | boolean | Indicateur qualité : prix de vente égal à 0 |
| `qa_vente_a_perte` | boolean | Indicateur qualité : prix de vente inférieur au coût d'achat |
| `qa_marge_negative` | boolean | Indicateur qualité : marge nette négative |
| `_source_file` | string | Provenance : chemin relatif du fichier source |
| `_batch` | string | Provenance : lot d'ingestion (initial) |
| `_ingested_at` | timestamp | Provenance : horodatage de l'ingestion Bronze |
| `_silver_at` | timestamp | Provenance : horodatage du traitement Silver |
| `_regles_version` | string | Provenance : version des règles de nettoyage appliquées |

## silver.store_returns

- Chemin : `data/silver/store_returns` (Parquet) · 37 902 lignes · 28 colonnes
- Granularité : une ligne = une ligne d'article retourné rattachée à un ticket magasin
- Clé candidate : `sr_ticket_number+sr_item_sk`
- Colonnes obligatoires (rejet si vides) : `sr_returned_date_sk`, `sr_item_sk`, `sr_ticket_number`, `sr_return_quantity`, `sr_return_amt`

| Colonne | Type | Description |
|---|---|---|
| `sr_returned_date_sk` | int | Date du retour (clé vers date_dim) |
| `sr_return_time_sk` | int | — |
| `sr_item_sk` | int | Produit retourné (clé vers item) |
| `sr_customer_sk` | int | — |
| `sr_cdemo_sk` | int | — |
| `sr_hdemo_sk` | int | — |
| `sr_addr_sk` | int | — |
| `sr_store_sk` | int | Magasin du retour (clé vers store) |
| `sr_reason_sk` | int | Motif du retour (clé vers reason, facultatif) |
| `sr_ticket_number` | bigint | Ticket de la vente d'origine |
| `sr_return_quantity` | int | Quantité retournée |
| `sr_return_amt` | decimal(12,2) | Montant remboursé, hors taxe |
| `sr_return_tax` | decimal(12,2) | Taxe remboursée |
| `sr_return_amt_inc_tax` | decimal(12,2) | — |
| `sr_fee` | decimal(12,2) | Frais de retour |
| `sr_return_ship_cost` | decimal(12,2) | — |
| `sr_refunded_cash` | decimal(12,2) | Part remboursée en espèces |
| `sr_reversed_charge` | decimal(12,2) | — |
| `sr_store_credit` | decimal(12,2) | — |
| `sr_net_loss` | decimal(12,2) | Perte nette liée au retour |
| `qa_cle_dupliquee` | boolean | Indicateur qualité : la clé (ticket, article) apparaît plusieurs fois (lignes distinctes conservées) |
| `qa_remboursement_nul` | boolean | Indicateur qualité : montant remboursé égal à 0 |
| `qa_motif_manquant` | boolean | Indicateur qualité : motif de retour absent |
| `_source_file` | string | Provenance : chemin relatif du fichier source |
| `_batch` | string | Provenance : lot d'ingestion (initial) |
| `_ingested_at` | timestamp | Provenance : horodatage de l'ingestion Bronze |
| `_silver_at` | timestamp | Provenance : horodatage du traitement Silver |
| `_regles_version` | string | Provenance : version des règles de nettoyage appliquées |

## silver.item

- Chemin : `data/silver/item` (Parquet) · 17 820 lignes · 31 colonnes
- Granularité : une ligne = une version (clé de substitution) d'un produit
- Clé candidate : `i_item_sk`
- Colonnes obligatoires (rejet si vides) : `i_item_sk`, `i_item_id`, `i_category`

| Colonne | Type | Description |
|---|---|---|
| `i_item_sk` | int | Identifiant produit (clé de substitution, unique) |
| `i_item_id` | string | Identifiant produit métier (peut porter plusieurs versions) |
| `i_rec_start_date` | date | Début de validité de la version du produit |
| `i_rec_end_date` | date | Fin de validité (vide = version courante) |
| `i_item_desc` | string | Description libre du produit (texte généré) |
| `i_current_price` | decimal(12,2) | Prix courant catalogue |
| `i_wholesale_cost` | decimal(12,2) | Coût d'achat |
| `i_brand_id` | int | — |
| `i_brand` | string | Marque (« Non renseigné » si vide à la source) |
| `i_class_id` | int | — |
| `i_class` | string | Classe de produit |
| `i_category_id` | int | — |
| `i_category` | string | Catégorie de produit |
| `i_manufact_id` | int | — |
| `i_manufact` | string | — |
| `i_size` | string | — |
| `i_formulation` | string | — |
| `i_color` | string | — |
| `i_units` | string | — |
| `i_container` | string | — |
| `i_manager_id` | int | — |
| `i_product_name` | string | Nom du produit |
| `qa_prix_invalide` | boolean | Indicateur qualité : prix courant vide ou <= 0 |
| `qa_prix_sous_cout` | boolean | Indicateur qualité : prix courant inférieur au coût d'achat |
| `qa_marque_imputee` | boolean | Indicateur qualité : marque remplacée par « Non renseigné » |
| `est_version_courante` | boolean | Colonne dérivée : la version n'a pas de date de fin (version courante) |
| `_source_file` | string | Provenance : chemin relatif du fichier source |
| `_batch` | string | Provenance : lot d'ingestion (initial) |
| `_ingested_at` | timestamp | Provenance : horodatage de l'ingestion Bronze |
| `_silver_at` | timestamp | Provenance : horodatage du traitement Silver |
| `_regles_version` | string | Provenance : version des règles de nettoyage appliquées |

## silver.store

- Chemin : `data/silver/store` (Parquet) · 12 lignes · 35 colonnes
- Granularité : une ligne = une version d'un magasin
- Clé candidate : `s_store_sk`
- Colonnes obligatoires (rejet si vides) : `s_store_sk`, `s_store_id`, `s_store_name`

| Colonne | Type | Description |
|---|---|---|
| `s_store_sk` | int | Identifiant magasin (clé de substitution, unique) |
| `s_store_id` | string | Identifiant magasin métier |
| `s_rec_start_date` | date | Début de validité de la version du magasin |
| `s_rec_end_date` | date | Fin de validité (vide = version courante) |
| `s_closed_date_sk` | int | Date de fermeture (clé vers date_dim) ; INCOHÉRENTE, non exploitable |
| `s_store_name` | string | Nom du magasin |
| `s_number_employees` | int | Effectif |
| `s_floor_space` | int | — |
| `s_hours` | string | — |
| `s_manager` | string | — |
| `s_market_id` | int | — |
| `s_geography_class` | string | — |
| `s_market_desc` | string | — |
| `s_market_manager` | string | — |
| `s_division_id` | int | — |
| `s_division_name` | string | — |
| `s_company_id` | int | — |
| `s_company_name` | string | — |
| `s_street_number` | string | — |
| `s_street_name` | string | — |
| `s_street_type` | string | — |
| `s_suite_number` | string | — |
| `s_city` | string | Ville du magasin |
| `s_county` | string | — |
| `s_state` | string | État du magasin |
| `s_zip` | string | — |
| `s_country` | string | — |
| `s_gmt_offset` | decimal(5,2) | — |
| `s_tax_precentage` | decimal(5,2) | — |
| `est_version_courante` | boolean | Colonne dérivée : la version n'a pas de date de fin (version courante) |
| `_source_file` | string | Provenance : chemin relatif du fichier source |
| `_batch` | string | Provenance : lot d'ingestion (initial) |
| `_ingested_at` | timestamp | Provenance : horodatage de l'ingestion Bronze |
| `_silver_at` | timestamp | Provenance : horodatage du traitement Silver |
| `_regles_version` | string | Provenance : version des règles de nettoyage appliquées |

## silver.date_dim

- Chemin : `data/silver/date_dim` (Parquet) · 109 573 lignes · 33 colonnes
- Granularité : une ligne = un jour calendaire
- Clé candidate : `d_date_sk`
- Colonnes obligatoires (rejet si vides) : `d_date_sk`, `d_date`, `d_year`, `d_moy`

| Colonne | Type | Description |
|---|---|---|
| `d_date_sk` | int | Identifiant date (clé de substitution, unique) |
| `d_date_id` | string | — |
| `d_date` | date | Date calendaire |
| `d_month_seq` | int | — |
| `d_week_seq` | int | — |
| `d_quarter_seq` | int | — |
| `d_year` | int | Année |
| `d_dow` | int | Jour de la semaine |
| `d_moy` | int | Mois de l'année (1-12) |
| `d_dom` | int | Jour du mois |
| `d_qoy` | int | Trimestre |
| `d_fy_year` | int | — |
| `d_fy_quarter_seq` | int | — |
| `d_fy_week_seq` | int | — |
| `d_day_name` | string | Nom du jour |
| `d_quarter_name` | string | — |
| `d_holiday` | string | Jour férié (Y/N) |
| `d_weekend` | string | Week-end (Y/N) |
| `d_following_holiday` | string | — |
| `d_first_dom` | int | — |
| `d_last_dom` | int | — |
| `d_same_day_ly` | int | — |
| `d_same_day_lq` | int | — |
| `d_current_day` | string | — |
| `d_current_week` | string | — |
| `d_current_month` | string | — |
| `d_current_quarter` | string | — |
| `d_current_year` | string | — |
| `_source_file` | string | Provenance : chemin relatif du fichier source |
| `_batch` | string | Provenance : lot d'ingestion (initial) |
| `_ingested_at` | timestamp | Provenance : horodatage de l'ingestion Bronze |
| `_silver_at` | timestamp | Provenance : horodatage du traitement Silver |
| `_regles_version` | string | Provenance : version des règles de nettoyage appliquées |

## silver.reason

- Chemin : `data/silver/reason` (Parquet) · 35 lignes · 8 colonnes
- Granularité : une ligne = un motif de retour
- Clé candidate : `r_reason_sk`
- Colonnes obligatoires (rejet si vides) : `r_reason_sk`, `r_reason_desc`

| Colonne | Type | Description |
|---|---|---|
| `r_reason_sk` | int | Identifiant du motif de retour (unique) |
| `r_reason_id` | string | Identifiant métier du motif |
| `r_reason_desc` | string | Libellé du motif (texte généré, non lisible métier) |
| `_source_file` | string | Provenance : chemin relatif du fichier source |
| `_batch` | string | Provenance : lot d'ingestion (initial) |
| `_ingested_at` | timestamp | Provenance : horodatage de l'ingestion Bronze |
| `_silver_at` | timestamp | Provenance : horodatage du traitement Silver |
| `_regles_version` | string | Provenance : version des règles de nettoyage appliquées |
