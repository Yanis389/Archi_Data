"""Schémas explicites des 6 sources retenues pour le TP3 (UC-06).

Statut : **déduit**. Les fichiers .dat n'ont pas d'en-tête et le kit ne fournit pas de dictionnaire.
Les noms de colonnes suivent la structure publique de TPC-DS dont TPCx-BB reprend les tables de base
(même démarche que `tp1/scripts/schemas.py`). Ils ne sont pas lus dans les fichiers : chaque script
vérifie que le nombre de champs lus est bien égal au nombre de colonnes attendu (voir
`spark_utils.lire_brut`), et les clés sont validées par jointure (`quality/controles_qualite.py`).

Chaque table est décrite par une liste (nom, type Spark DDL). Les montants sont en DECIMAL(12,2)
et non en DOUBLE pour éviter les erreurs d'arrondi lors des sommes.
"""

MONEY = "DECIMAL(12,2)"

SCHEMAS = {
    "store_sales": [
        ("ss_sold_date_sk", "INT"), ("ss_sold_time_sk", "INT"), ("ss_item_sk", "INT"),
        ("ss_customer_sk", "INT"), ("ss_cdemo_sk", "INT"), ("ss_hdemo_sk", "INT"),
        ("ss_addr_sk", "INT"), ("ss_store_sk", "INT"), ("ss_promo_sk", "INT"),
        ("ss_ticket_number", "BIGINT"), ("ss_quantity", "INT"), ("ss_wholesale_cost", MONEY),
        ("ss_list_price", MONEY), ("ss_sales_price", MONEY), ("ss_ext_discount_amt", MONEY),
        ("ss_ext_sales_price", MONEY), ("ss_ext_wholesale_cost", MONEY),
        ("ss_ext_list_price", MONEY), ("ss_ext_tax", MONEY), ("ss_coupon_amt", MONEY),
        ("ss_net_paid", MONEY), ("ss_net_paid_inc_tax", MONEY), ("ss_net_profit", MONEY),
    ],
    "store_returns": [
        ("sr_returned_date_sk", "INT"), ("sr_return_time_sk", "INT"), ("sr_item_sk", "INT"),
        ("sr_customer_sk", "INT"), ("sr_cdemo_sk", "INT"), ("sr_hdemo_sk", "INT"),
        ("sr_addr_sk", "INT"), ("sr_store_sk", "INT"), ("sr_reason_sk", "INT"),
        ("sr_ticket_number", "BIGINT"), ("sr_return_quantity", "INT"), ("sr_return_amt", MONEY),
        ("sr_return_tax", MONEY), ("sr_return_amt_inc_tax", MONEY), ("sr_fee", MONEY),
        ("sr_return_ship_cost", MONEY), ("sr_refunded_cash", MONEY),
        ("sr_reversed_charge", MONEY), ("sr_store_credit", MONEY), ("sr_net_loss", MONEY),
    ],
    "item": [
        ("i_item_sk", "INT"), ("i_item_id", "STRING"), ("i_rec_start_date", "DATE"),
        ("i_rec_end_date", "DATE"), ("i_item_desc", "STRING"), ("i_current_price", MONEY),
        ("i_wholesale_cost", MONEY), ("i_brand_id", "INT"), ("i_brand", "STRING"),
        ("i_class_id", "INT"), ("i_class", "STRING"), ("i_category_id", "INT"),
        ("i_category", "STRING"), ("i_manufact_id", "INT"), ("i_manufact", "STRING"),
        ("i_size", "STRING"), ("i_formulation", "STRING"), ("i_color", "STRING"),
        ("i_units", "STRING"), ("i_container", "STRING"), ("i_manager_id", "INT"),
        ("i_product_name", "STRING"),
    ],
    "store": [
        ("s_store_sk", "INT"), ("s_store_id", "STRING"), ("s_rec_start_date", "DATE"),
        ("s_rec_end_date", "DATE"), ("s_closed_date_sk", "INT"), ("s_store_name", "STRING"),
        ("s_number_employees", "INT"), ("s_floor_space", "INT"), ("s_hours", "STRING"),
        ("s_manager", "STRING"), ("s_market_id", "INT"), ("s_geography_class", "STRING"),
        ("s_market_desc", "STRING"), ("s_market_manager", "STRING"), ("s_division_id", "INT"),
        ("s_division_name", "STRING"), ("s_company_id", "INT"), ("s_company_name", "STRING"),
        ("s_street_number", "STRING"), ("s_street_name", "STRING"), ("s_street_type", "STRING"),
        ("s_suite_number", "STRING"), ("s_city", "STRING"), ("s_county", "STRING"),
        ("s_state", "STRING"), ("s_zip", "STRING"), ("s_country", "STRING"),
        ("s_gmt_offset", "DECIMAL(5,2)"), ("s_tax_precentage", "DECIMAL(5,2)"),
    ],
    "date_dim": [
        ("d_date_sk", "INT"), ("d_date_id", "STRING"), ("d_date", "DATE"), ("d_month_seq", "INT"),
        ("d_week_seq", "INT"), ("d_quarter_seq", "INT"), ("d_year", "INT"), ("d_dow", "INT"),
        ("d_moy", "INT"), ("d_dom", "INT"), ("d_qoy", "INT"), ("d_fy_year", "INT"),
        ("d_fy_quarter_seq", "INT"), ("d_fy_week_seq", "INT"), ("d_day_name", "STRING"),
        ("d_quarter_name", "STRING"), ("d_holiday", "STRING"), ("d_weekend", "STRING"),
        ("d_following_holiday", "STRING"), ("d_first_dom", "INT"), ("d_last_dom", "INT"),
        ("d_same_day_ly", "INT"), ("d_same_day_lq", "INT"), ("d_current_day", "STRING"),
        ("d_current_week", "STRING"), ("d_current_month", "STRING"),
        ("d_current_quarter", "STRING"), ("d_current_year", "STRING"),
    ],
    "reason": [
        ("r_reason_sk", "INT"), ("r_reason_id", "STRING"), ("r_reason_desc", "STRING"),
    ],
}

# Clé candidate de chaque table (colonne ou combinaison), à valider par le contrôle d'unicité.
CLES_CANDIDATES = {
    "store_sales": ["ss_ticket_number", "ss_item_sk"],
    "store_returns": ["sr_ticket_number", "sr_item_sk"],
    "item": ["i_item_sk"],
    "store": ["s_store_sk"],
    "date_dim": ["d_date_sk"],
    "reason": ["r_reason_sk"],
}

# Granularité : ce que représente exactement une ligne.
GRANULARITES = {
    "store_sales": "une ligne d'article sur un ticket de caisse magasin",
    "store_returns": "une ligne d'article retourné rattachée à un ticket magasin",
    "item": "une version (clé de substitution) d'un produit",
    "store": "une version d'un magasin",
    "date_dim": "un jour calendaire",
    "reason": "un motif de retour",
}

# Colonnes dont une valeur manquante rend la ligne inexploitable (donnée obligatoire).
OBLIGATOIRES = {
    "store_sales": ["ss_sold_date_sk", "ss_item_sk", "ss_store_sk", "ss_ticket_number",
                    "ss_quantity", "ss_sales_price", "ss_ext_sales_price"],
    "store_returns": ["sr_returned_date_sk", "sr_item_sk", "sr_ticket_number",
                      "sr_return_quantity", "sr_return_amt"],
    "item": ["i_item_sk", "i_item_id", "i_category"],
    "store": ["s_store_sk", "s_store_id", "s_store_name"],
    "date_dim": ["d_date_sk", "d_date", "d_year", "d_moy"],
    "reason": ["r_reason_sk", "r_reason_desc"],
}


def colonnes(table):
    return [c for c, _ in SCHEMAS[table]]


def ddl(table):
    return ", ".join(f"{c} {t}" for c, t in SCHEMAS[table])
