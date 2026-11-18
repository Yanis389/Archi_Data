# Inventaire technique des sources (UC-06, étape 2)

Document **généré** par `python -m exploration.inventaire` à partir des fichiers réels (chiffres mesurés, preuve : `preuves/02_inventaire.txt`). Statut des noms de colonnes : **déduits** de la structure TPC-DS (les .dat n'ont pas d'en-tête), vérifiés par le nombre de champs mesuré sur chaque ligne et par les jointures (rapport qualité).

Lot traité : lot initial (`retail_project/data`). Le lot `data_refresh` n'est pas traité dans ce TP.

## Synthèse

| Information | store_sales | store_returns | item | store | date_dim | reason |
|---|---|---|---|---|---|---|
| Nom réel du fichier | store_sales.dat | store_returns.dat | item.dat | store.dat | date_dim.dat | reason.dat |
| Emplacement (relatif à `Annexes/`) | `retail_project/data/store_sales/store_sales.dat` | `retail_project/data/store_returns/store_returns.dat` | `retail_project/data/item/item.dat` | `retail_project/data/store/store.dat` | `retail_project/data/date_dim/date_dim.dat` | `retail_project/data/reason/reason.dat` |
| Format | texte délimité par le caractère pipe, sans en-tête (.dat), UTF-8 valide | texte délimité par le caractère pipe, sans en-tête (.dat), UTF-8 valide | texte délimité par le caractère pipe, sans en-tête (.dat), UTF-8 valide | texte délimité par le caractère pipe, sans en-tête (.dat), UTF-8 valide | texte délimité par le caractère pipe, sans en-tête (.dat), UTF-8 valide | texte délimité par le caractère pipe, sans en-tête (.dat), UTF-8 valide |
| Taille | 88.5 Mo | 4.1 Mo | 6.5 Mo | 3.3 Ko | 14.7 Mo | 3.0 Ko |
| Nombre de lignes | 667 579 | 37 902 | 17 820 | 12 | 109 573 | 35 |
| Nombre de colonnes | 23 | 20 | 22 | 29 | 28 | 3 |
| Champs par ligne (mesuré) | 23 champs: 667579 lignes | 20 champs: 37902 lignes | 22 champs: 17820 lignes | 29 champs: 12 lignes | 28 champs: 109573 lignes | 3 champs: 35 lignes |
| Clé candidate | `ss_ticket_number+ss_item_sk` | `sr_ticket_number+sr_item_sk` | `i_item_sk` | `s_store_sk` | `d_date_sk` | `r_reason_sk` |
| Clé unique ? | **non** | **non** | oui | oui | oui | oui |
| Granularité (1 ligne =) | une ligne d'article sur un ticket de caisse magasin | une ligne d'article retourné rattachée à un ticket magasin | une version (clé de substitution) d'un produit | une version d'un magasin | un jour calendaire | un motif de retour |
| Anomalies identifiées | valeurs vides : ss_cdemo_sk=238, ss_hdemo_sk=295, ss_addr_sk=448, ss_promo_sk=158 ; clé candidate ss_ticket_number+ss_item_sk non unique : 4136 lignes en excès | valeurs vides : sr_cdemo_sk=21, sr_hdemo_sk=15, sr_addr_sk=42, sr_reason_sk=11 ; clé candidate sr_ticket_number+sr_item_sk non unique : 158 lignes en excès | valeurs vides : i_rec_end_date=17820, i_item_desc=4, i_brand_id=8, i_brand=6 ; espaces superflus : i_item_desc=2575 | valeurs vides : s_rec_end_date=12 ; espaces superflus : s_market_desc=1 | aucune | espaces superflus : r_reason_desc=4 |

## Types observés et colonnes

`type_infere_spark` = inférence automatique de Spark sur le fichier complet (simple exploration, pas une validation de schéma). `type_declare` = type retenu dans `lib/schemas.py`. Les écarts attendus : Spark infère `double` pour les montants (déclarés `DECIMAL(12,2)` pour éviter les erreurs d'arrondi) et `timestamp` ou `date` pour les dates selon les valeurs.

### store_sales

| # | Colonne | Type déclaré | Type inféré Spark | Nuls | % nuls | Distincts |
|---|---|---|---|---|---|---|
| 1 | `ss_sold_date_sk` | INT | int | 0 | 0.0 | 1808 |
| 2 | `ss_sold_time_sk` | INT | int | 0 | 0.0 | 55645 |
| 3 | `ss_item_sk` | INT | int | 0 | 0.0 | 17820 |
| 4 | `ss_customer_sk` | INT | int | 0 | 0.0 | 37336 |
| 5 | `ss_cdemo_sk` | INT | int | 238 | 0.036 | 36954 |
| 6 | `ss_hdemo_sk` | INT | int | 295 | 0.044 | 7162 |
| 7 | `ss_addr_sk` | INT | int | 448 | 0.067 | 26287 |
| 8 | `ss_store_sk` | INT | int | 0 | 0.0 | 12 |
| 9 | `ss_promo_sk` | INT | int | 158 | 0.024 | 301 |
| 10 | `ss_ticket_number` | BIGINT | int | 0 | 0.0 | 89100 |
| 11 | `ss_quantity` | INT | int | 0 | 0.0 | 100 |
| 12 | `ss_wholesale_cost` | DECIMAL(12,2) | double | 0 | 0.0 | 9901 |
| 13 | `ss_list_price` | DECIMAL(12,2) | double | 0 | 0.0 | 19524 |
| 14 | `ss_sales_price` | DECIMAL(12,2) | double | 0 | 0.0 | 17199 |
| 15 | `ss_ext_discount_amt` | DECIMAL(12,2) | double | 0 | 0.0 | 238093 |
| 16 | `ss_ext_sales_price` | DECIMAL(12,2) | double | 0 | 0.0 | 237770 |
| 17 | `ss_ext_wholesale_cost` | DECIMAL(12,2) | double | 0 | 0.0 | 264513 |
| 18 | `ss_ext_list_price` | DECIMAL(12,2) | double | 0 | 0.0 | 328908 |
| 19 | `ss_ext_tax` | DECIMAL(12,2) | double | 0 | 0.0 | 53387 |
| 20 | `ss_coupon_amt` | DECIMAL(12,2) | double | 0 | 0.0 | 87123 |
| 21 | `ss_net_paid` | DECIMAL(12,2) | double | 0 | 0.0 | 255026 |
| 22 | `ss_net_paid_inc_tax` | DECIMAL(12,2) | double | 0 | 0.0 | 315642 |
| 23 | `ss_net_profit` | DECIMAL(12,2) | double | 0 | 0.0 | 288874 |

### store_returns

| # | Colonne | Type déclaré | Type inféré Spark | Nuls | % nuls | Distincts |
|---|---|---|---|---|---|---|
| 1 | `sr_returned_date_sk` | INT | int | 0 | 0.0 | 2221 |
| 2 | `sr_return_time_sk` | INT | int | 0 | 0.0 | 30697 |
| 3 | `sr_item_sk` | INT | int | 0 | 0.0 | 12551 |
| 4 | `sr_customer_sk` | INT | int | 0 | 0.0 | 6226 |
| 5 | `sr_cdemo_sk` | INT | int | 21 | 0.055 | 6278 |
| 6 | `sr_hdemo_sk` | INT | int | 15 | 0.04 | 4216 |
| 7 | `sr_addr_sk` | INT | int | 42 | 0.111 | 5914 |
| 8 | `sr_store_sk` | INT | int | 0 | 0.0 | 12 |
| 9 | `sr_reason_sk` | INT | int | 11 | 0.029 | 36 |
| 10 | `sr_ticket_number` | BIGINT | int | 0 | 0.0 | 8910 |
| 11 | `sr_return_quantity` | INT | int | 0 | 0.0 | 100 |
| 12 | `sr_return_amt` | DECIMAL(12,2) | double | 0 | 0.0 | 29163 |
| 13 | `sr_return_tax` | DECIMAL(12,2) | double | 0 | 0.0 | 11617 |
| 14 | `sr_return_amt_inc_tax` | DECIMAL(12,2) | double | 0 | 0.0 | 32024 |
| 15 | `sr_fee` | DECIMAL(12,2) | double | 0 | 0.0 | 9712 |
| 16 | `sr_return_ship_cost` | DECIMAL(12,2) | double | 0 | 0.0 | 32264 |
| 17 | `sr_refunded_cash` | DECIMAL(12,2) | double | 0 | 0.0 | 26912 |
| 18 | `sr_reversed_charge` | DECIMAL(12,2) | double | 0 | 0.0 | 21080 |
| 19 | `sr_store_credit` | DECIMAL(12,2) | double | 0 | 0.0 | 20717 |
| 20 | `sr_net_loss` | DECIMAL(12,2) | double | 0 | 0.0 | 32952 |

### item

| # | Colonne | Type déclaré | Type inféré Spark | Nuls | % nuls | Distincts |
|---|---|---|---|---|---|---|
| 1 | `i_item_sk` | INT | int | 0 | 0.0 | 17820 |
| 2 | `i_item_id` | STRING | string | 0 | 0.0 | 17820 |
| 3 | `i_rec_start_date` | DATE | date | 0 | 0.0 | 364 |
| 4 | `i_rec_end_date` | DATE | string | 17820 | 100.0 | 1 |
| 5 | `i_item_desc` | STRING | string | 4 | 0.022 | 17817 |
| 6 | `i_current_price` | DECIMAL(12,2) | double | 0 | 0.0 | 8343 |
| 7 | `i_wholesale_cost` | DECIMAL(12,2) | double | 0 | 0.0 | 7598 |
| 8 | `i_brand_id` | INT | int | 8 | 0.045 | 17798 |
| 9 | `i_brand` | STRING | string | 6 | 0.034 | 17555 |
| 10 | `i_class_id` | INT | int | 0 | 0.0 | 16 |
| 11 | `i_class` | STRING | string | 0 | 0.0 | 74 |
| 12 | `i_category_id` | INT | int | 0 | 0.0 | 9 |
| 13 | `i_category` | STRING | string | 0 | 0.0 | 9 |
| 14 | `i_manufact_id` | INT | int | 0 | 0.0 | 1000 |
| 15 | `i_manufact` | STRING | string | 0 | 0.0 | 17481 |
| 16 | `i_size` | STRING | string | 0 | 0.0 | 7 |
| 17 | `i_formulation` | STRING | string | 0 | 0.0 | 16916 |
| 18 | `i_color` | STRING | string | 0 | 0.0 | 92 |
| 19 | `i_units` | STRING | string | 0 | 0.0 | 21 |
| 20 | `i_container` | STRING | string | 0 | 0.0 | 1 |
| 21 | `i_manager_id` | INT | int | 0 | 0.0 | 100 |
| 22 | `i_product_name` | STRING | string | 0 | 0.0 | 17820 |

### store

| # | Colonne | Type déclaré | Type inféré Spark | Nuls | % nuls | Distincts |
|---|---|---|---|---|---|---|
| 1 | `s_store_sk` | INT | int | 0 | 0.0 | 12 |
| 2 | `s_store_id` | STRING | string | 0 | 0.0 | 12 |
| 3 | `s_rec_start_date` | DATE | date | 0 | 0.0 | 7 |
| 4 | `s_rec_end_date` | DATE | string | 12 | 100.0 | 1 |
| 5 | `s_closed_date_sk` | INT | int | 0 | 0.0 | 12 |
| 6 | `s_store_name` | STRING | string | 0 | 0.0 | 12 |
| 7 | `s_number_employees` | INT | int | 0 | 0.0 | 9 |
| 8 | `s_floor_space` | INT | int | 0 | 0.0 | 12 |
| 9 | `s_hours` | STRING | string | 0 | 0.0 | 3 |
| 10 | `s_manager` | STRING | string | 0 | 0.0 | 12 |
| 11 | `s_market_id` | INT | int | 0 | 0.0 | 6 |
| 12 | `s_geography_class` | STRING | string | 0 | 0.0 | 1 |
| 13 | `s_market_desc` | STRING | string | 0 | 0.0 | 12 |
| 14 | `s_market_manager` | STRING | string | 0 | 0.0 | 12 |
| 15 | `s_division_id` | INT | int | 0 | 0.0 | 1 |
| 16 | `s_division_name` | STRING | string | 0 | 0.0 | 1 |
| 17 | `s_company_id` | INT | int | 0 | 0.0 | 1 |
| 18 | `s_company_name` | STRING | string | 0 | 0.0 | 1 |
| 19 | `s_street_number` | STRING | int | 0 | 0.0 | 12 |
| 20 | `s_street_name` | STRING | string | 0 | 0.0 | 12 |
| 21 | `s_street_type` | STRING | string | 0 | 0.0 | 12 |
| 22 | `s_suite_number` | STRING | string | 0 | 0.0 | 12 |
| 23 | `s_city` | STRING | string | 0 | 0.0 | 12 |
| 24 | `s_county` | STRING | string | 0 | 0.0 | 12 |
| 25 | `s_state` | STRING | string | 0 | 0.0 | 8 |
| 26 | `s_zip` | STRING | int | 0 | 0.0 | 12 |
| 27 | `s_country` | STRING | string | 0 | 0.0 | 1 |
| 28 | `s_gmt_offset` | DECIMAL(5,2) | int | 0 | 0.0 | 4 |
| 29 | `s_tax_precentage` | DECIMAL(5,2) | double | 0 | 0.0 | 7 |

### date_dim

| # | Colonne | Type déclaré | Type inféré Spark | Nuls | % nuls | Distincts |
|---|---|---|---|---|---|---|
| 1 | `d_date_sk` | INT | int | 0 | 0.0 | 109573 |
| 2 | `d_date_id` | STRING | string | 0 | 0.0 | 109573 |
| 3 | `d_date` | DATE | date | 0 | 0.0 | 109573 |
| 4 | `d_month_seq` | INT | int | 0 | 0.0 | 3600 |
| 5 | `d_week_seq` | INT | int | 0 | 0.0 | 15654 |
| 6 | `d_quarter_seq` | INT | int | 0 | 0.0 | 1200 |
| 7 | `d_year` | INT | int | 0 | 0.0 | 300 |
| 8 | `d_dow` | INT | int | 0 | 0.0 | 7 |
| 9 | `d_moy` | INT | int | 0 | 0.0 | 12 |
| 10 | `d_dom` | INT | int | 0 | 0.0 | 31 |
| 11 | `d_qoy` | INT | int | 0 | 0.0 | 4 |
| 12 | `d_fy_year` | INT | int | 0 | 0.0 | 300 |
| 13 | `d_fy_quarter_seq` | INT | int | 0 | 0.0 | 1200 |
| 14 | `d_fy_week_seq` | INT | int | 0 | 0.0 | 15654 |
| 15 | `d_day_name` | STRING | string | 0 | 0.0 | 7 |
| 16 | `d_quarter_name` | STRING | string | 0 | 0.0 | 1200 |
| 17 | `d_holiday` | STRING | string | 0 | 0.0 | 1 |
| 18 | `d_weekend` | STRING | string | 0 | 0.0 | 2 |
| 19 | `d_following_holiday` | STRING | string | 0 | 0.0 | 2 |
| 20 | `d_first_dom` | INT | int | 0 | 0.0 | 56753 |
| 21 | `d_last_dom` | INT | int | 0 | 0.0 | 56970 |
| 22 | `d_same_day_ly` | INT | int | 0 | 0.0 | 56725 |
| 23 | `d_same_day_lq` | INT | int | 0 | 0.0 | 56778 |
| 24 | `d_current_day` | STRING | string | 0 | 0.0 | 2 |
| 25 | `d_current_week` | STRING | string | 0 | 0.0 | 2 |
| 26 | `d_current_month` | STRING | string | 0 | 0.0 | 2 |
| 27 | `d_current_quarter` | STRING | string | 0 | 0.0 | 2 |
| 28 | `d_current_year` | STRING | string | 0 | 0.0 | 2 |

### reason

| # | Colonne | Type déclaré | Type inféré Spark | Nuls | % nuls | Distincts |
|---|---|---|---|---|---|---|
| 1 | `r_reason_sk` | INT | int | 0 | 0.0 | 35 |
| 2 | `r_reason_id` | STRING | string | 0 | 0.0 | 35 |
| 3 | `r_reason_desc` | STRING | string | 0 | 0.0 | 35 |
