"""Schémas **déduits** des fichiers TPCx-BB du kit.

IMPORTANT (statut « Déduit » au sens du TP) :
les fichiers `.dat` fournis n'ont **pas d'en-tête** et le kit ne contient aucun dictionnaire de
données. Les noms de colonnes ci-dessous proviennent de la structure publique de TPC-DS dont
TPCx-BB reprend les tables de base, plus les tables propres à BigBench (web_clickstreams,
product_reviews, item_marketprices). Ils ne sont donc PAS lus dans les fichiers.

Ils sont confrontés aux données par `profiler_tpcx_bb.py` :
  1. le nombre de champs observé par ligne doit égaler le nombre de colonnes attendu ;
  2. pour les clés, le taux de correspondance (jointure) avec la table référencée valide le sens.
Toute divergence est signalée dans les preuves.
"""

# table -> (domaine métier, [colonnes])
SCHEMAS = {
    "customer": ("Clients", [
        "c_customer_sk", "c_customer_id", "c_current_cdemo_sk", "c_current_hdemo_sk",
        "c_current_addr_sk", "c_first_shipto_date_sk", "c_first_sales_date_sk", "c_salutation",
        "c_first_name", "c_last_name", "c_preferred_cust_flag", "c_birth_day", "c_birth_month",
        "c_birth_year", "c_birth_country", "c_login", "c_email_address", "c_last_review_date"]),
    "customer_address": ("Clients", [
        "ca_address_sk", "ca_address_id", "ca_street_number", "ca_street_name", "ca_street_type",
        "ca_suite_number", "ca_city", "ca_county", "ca_state", "ca_zip", "ca_country",
        "ca_gmt_offset", "ca_location_type"]),
    "customer_demographics": ("Clients", [
        "cd_demo_sk", "cd_gender", "cd_marital_status", "cd_education_status",
        "cd_purchase_estimate", "cd_credit_rating", "cd_dep_count", "cd_dep_employed_count",
        "cd_dep_college_count"]),
    "household_demographics": ("Clients", [
        "hd_demo_sk", "hd_income_band_sk", "hd_buy_potential", "hd_dep_count",
        "hd_vehicle_count"]),
    "income_band": ("Clients", ["ib_income_band_sk", "ib_lower_bound", "ib_upper_bound"]),
    "date_dim": ("Dates et temps", [
        "d_date_sk", "d_date_id", "d_date", "d_month_seq", "d_week_seq", "d_quarter_seq", "d_year",
        "d_dow", "d_moy", "d_dom", "d_qoy", "d_fy_year", "d_fy_quarter_seq", "d_fy_week_seq",
        "d_day_name", "d_quarter_name", "d_holiday", "d_weekend", "d_following_holiday",
        "d_first_dom", "d_last_dom", "d_same_day_ly", "d_same_day_lq", "d_current_day",
        "d_current_week", "d_current_month", "d_current_quarter", "d_current_year"]),
    "time_dim": ("Dates et temps", [
        "t_time_sk", "t_time_id", "t_time", "t_hour", "t_minute", "t_second", "t_am_pm",
        "t_shift", "t_sub_shift", "t_meal_time"]),
    "item": ("Produits et prix", [
        "i_item_sk", "i_item_id", "i_rec_start_date", "i_rec_end_date", "i_item_desc",
        "i_current_price", "i_wholesale_cost", "i_brand_id", "i_brand", "i_class_id", "i_class",
        "i_category_id", "i_category", "i_manufact_id", "i_manufact", "i_size", "i_formulation",
        "i_color", "i_units", "i_container", "i_manager_id", "i_product_name"]),
    "item_marketprices": ("Produits et prix", [
        "imp_sk", "imp_item_sk", "imp_competitor", "imp_competitor_price", "imp_start_date",
        "imp_end_date"]),
    "promotion": ("Promotions", [
        "p_promo_sk", "p_promo_id", "p_start_date_sk", "p_end_date_sk", "p_item_sk", "p_cost",
        "p_response_target", "p_promo_name", "p_channel_dmail", "p_channel_email",
        "p_channel_catalog", "p_channel_tv", "p_channel_radio", "p_channel_press",
        "p_channel_event", "p_channel_demo", "p_channel_details", "p_purpose",
        "p_discount_active"]),
    "reason": ("Retours", ["r_reason_sk", "r_reason_id", "r_reason_desc"]),
    "ship_mode": ("Logistique", [
        "sm_ship_mode_sk", "sm_ship_mode_id", "sm_type", "sm_code", "sm_carrier", "sm_contract"]),
    "store": ("Magasins et entrepôts", [
        "s_store_sk", "s_store_id", "s_rec_start_date", "s_rec_end_date", "s_closed_date_sk",
        "s_store_name", "s_number_employees", "s_floor_space", "s_hours", "s_manager",
        "s_market_id", "s_geography_class", "s_market_desc", "s_market_manager", "s_division_id",
        "s_division_name", "s_company_id", "s_company_name", "s_street_number", "s_street_name",
        "s_street_type", "s_suite_number", "s_city", "s_county", "s_state", "s_zip", "s_country",
        "s_gmt_offset", "s_tax_precentage"]),
    "warehouse": ("Magasins et entrepôts", [
        "w_warehouse_sk", "w_warehouse_id", "w_warehouse_name", "w_warehouse_sq_ft",
        "w_street_number", "w_street_name", "w_street_type", "w_suite_number", "w_city",
        "w_county", "w_state", "w_zip", "w_country", "w_gmt_offset"]),
    "inventory": ("Stocks", [
        "inv_date_sk", "inv_item_sk", "inv_warehouse_sk", "inv_quantity_on_hand"]),
    "store_sales": ("Ventes magasin", [
        "ss_sold_date_sk", "ss_sold_time_sk", "ss_item_sk", "ss_customer_sk", "ss_cdemo_sk",
        "ss_hdemo_sk", "ss_addr_sk", "ss_store_sk", "ss_promo_sk", "ss_ticket_number",
        "ss_quantity", "ss_wholesale_cost", "ss_list_price", "ss_sales_price",
        "ss_ext_discount_amt", "ss_ext_sales_price", "ss_ext_wholesale_cost", "ss_ext_list_price",
        "ss_ext_tax", "ss_coupon_amt", "ss_net_paid", "ss_net_paid_inc_tax", "ss_net_profit"]),
    "store_returns": ("Retours", [
        "sr_returned_date_sk", "sr_return_time_sk", "sr_item_sk", "sr_customer_sk", "sr_cdemo_sk",
        "sr_hdemo_sk", "sr_addr_sk", "sr_store_sk", "sr_reason_sk", "sr_ticket_number",
        "sr_return_quantity", "sr_return_amt", "sr_return_tax", "sr_return_amt_inc_tax", "sr_fee",
        "sr_return_ship_cost", "sr_refunded_cash", "sr_reversed_charge", "sr_store_credit",
        "sr_net_loss"]),
    "web_sales": ("Ventes web", [
        "ws_sold_date_sk", "ws_sold_time_sk", "ws_ship_date_sk", "ws_item_sk",
        "ws_bill_customer_sk", "ws_bill_cdemo_sk", "ws_bill_hdemo_sk", "ws_bill_addr_sk",
        "ws_ship_customer_sk", "ws_ship_cdemo_sk", "ws_ship_hdemo_sk", "ws_ship_addr_sk",
        "ws_web_page_sk", "ws_web_site_sk", "ws_ship_mode_sk", "ws_warehouse_sk", "ws_promo_sk",
        "ws_order_number", "ws_quantity", "ws_wholesale_cost", "ws_list_price", "ws_sales_price",
        "ws_ext_discount_amt", "ws_ext_sales_price", "ws_ext_wholesale_cost", "ws_ext_list_price",
        "ws_ext_tax", "ws_coupon_amt", "ws_ext_ship_cost", "ws_net_paid", "ws_net_paid_inc_tax",
        "ws_net_paid_inc_ship", "ws_net_paid_inc_ship_tax", "ws_net_profit"]),
    "web_returns": ("Retours", [
        "wr_returned_date_sk", "wr_returned_time_sk", "wr_item_sk", "wr_refunded_customer_sk",
        "wr_refunded_cdemo_sk", "wr_refunded_hdemo_sk", "wr_refunded_addr_sk",
        "wr_returning_customer_sk", "wr_returning_cdemo_sk", "wr_returning_hdemo_sk",
        "wr_returning_addr_sk", "wr_web_page_sk", "wr_reason_sk", "wr_order_number",
        "wr_return_quantity", "wr_return_amt", "wr_return_tax", "wr_return_amt_inc_tax",
        "wr_fee", "wr_return_ship_cost", "wr_refunded_cash", "wr_reversed_charge",
        "wr_account_credit", "wr_net_loss"]),
    "web_page": ("Navigation web", [
        "wp_web_page_sk", "wp_web_page_id", "wp_rec_start_date", "wp_rec_end_date",
        "wp_creation_date_sk", "wp_access_date_sk", "wp_autogen_flag", "wp_customer_sk", "wp_url",
        "wp_type", "wp_char_count", "wp_link_count", "wp_image_count", "wp_max_ad_count"]),
    "web_site": ("Navigation web", [
        "web_site_sk", "web_site_id", "web_rec_start_date", "web_rec_end_date", "web_name",
        "web_open_date_sk", "web_close_date_sk", "web_class", "web_manager", "web_mkt_id",
        "web_mkt_class", "web_mkt_desc", "web_market_manager", "web_company_id",
        "web_company_name", "web_street_number", "web_street_name", "web_street_type",
        "web_suite_number", "web_city", "web_county", "web_state", "web_zip", "web_country",
        "web_gmt_offset", "web_tax_percentage"]),
    "web_clickstreams": ("Navigation web", [
        "wcs_click_date_sk", "wcs_click_time_sk", "wcs_sales_sk", "wcs_item_sk",
        "wcs_web_page_sk", "wcs_user_sk"]),
    "product_reviews": ("Avis produits", [
        "pr_review_sk", "pr_review_date", "pr_review_time", "pr_review_rating", "pr_item_sk",
        "pr_user_sk", "pr_order_sk", "pr_review_content"]),
}

# Colonnes dont le sens métier est documenté (clés et mesures utilisées par les KPI).
DESCRIPTIONS = {
    "ss_sold_date_sk": "Date de vente (clé vers date_dim)",
    "ss_sold_time_sk": "Heure de vente (clé vers time_dim)",
    "ss_item_sk": "Produit vendu (clé vers item)",
    "ss_customer_sk": "Client (clé vers customer)",
    "ss_store_sk": "Magasin (clé vers store)",
    "ss_promo_sk": "Promotion appliquée (clé vers promotion)",
    "ss_ticket_number": "Numéro de ticket de caisse",
    "ss_quantity": "Quantité vendue sur la ligne",
    "ss_wholesale_cost": "Coût d'achat unitaire",
    "ss_list_price": "Prix catalogue unitaire",
    "ss_sales_price": "Prix de vente unitaire",
    "ss_ext_sales_price": "Montant de la ligne (quantité x prix de vente)",
    "ss_ext_discount_amt": "Remise totale de la ligne",
    "ss_ext_list_price": "Montant de la ligne au prix catalogue",
    "ss_net_paid": "Montant net payé (hors taxe)",
    "ss_net_profit": "Marge nette de la ligne (net payé - coût d'achat)",
    "ws_sold_date_sk": "Date de commande web (clé vers date_dim)",
    "ws_ship_date_sk": "Date d'expédition (clé vers date_dim)",
    "ws_item_sk": "Produit vendu (clé vers item)",
    "ws_bill_customer_sk": "Client facturé (clé vers customer)",
    "ws_web_page_sk": "Page web de la vente (clé vers web_page)",
    "ws_web_site_sk": "Site web (clé vers web_site)",
    "ws_ship_mode_sk": "Mode d'expédition (clé vers ship_mode)",
    "ws_warehouse_sk": "Entrepôt d'expédition (clé vers warehouse)",
    "ws_promo_sk": "Promotion appliquée (clé vers promotion)",
    "ws_order_number": "Numéro de commande web",
    "ws_quantity": "Quantité vendue sur la ligne",
    "ws_sales_price": "Prix de vente unitaire",
    "ws_ext_sales_price": "Montant de la ligne (quantité x prix de vente)",
    "ws_net_paid": "Montant net payé (hors taxe, hors port)",
    "ws_net_profit": "Marge nette de la ligne",
    "sr_returned_date_sk": "Date du retour (clé vers date_dim)",
    "sr_item_sk": "Produit retourné (clé vers item)",
    "sr_customer_sk": "Client (clé vers customer)",
    "sr_store_sk": "Magasin (clé vers store)",
    "sr_reason_sk": "Motif de retour (clé vers reason)",
    "sr_ticket_number": "Ticket de la vente d'origine",
    "sr_return_quantity": "Quantité retournée",
    "sr_return_amt": "Montant remboursé (hors taxe)",
    "wr_returned_date_sk": "Date du retour (clé vers date_dim)",
    "wr_item_sk": "Produit retourné (clé vers item)",
    "wr_refunded_customer_sk": "Client remboursé (clé vers customer)",
    "wr_reason_sk": "Motif de retour (clé vers reason)",
    "wr_order_number": "Commande web d'origine",
    "wr_return_quantity": "Quantité retournée",
    "wr_return_amt": "Montant remboursé (hors taxe)",
    "inv_date_sk": "Date du relevé de stock (clé vers date_dim)",
    "inv_item_sk": "Produit (clé vers item)",
    "inv_warehouse_sk": "Entrepôt (clé vers warehouse)",
    "inv_quantity_on_hand": "Quantité en stock à la date du relevé",
    "wcs_click_date_sk": "Date du clic (clé vers date_dim)",
    "wcs_click_time_sk": "Heure du clic (clé vers time_dim)",
    "wcs_sales_sk": "Commande web associée (vide si le clic n'a pas abouti à une vente)",
    "wcs_item_sk": "Produit consulté (clé vers item)",
    "wcs_web_page_sk": "Page consultée (clé vers web_page)",
    "wcs_user_sk": "Visiteur identifié (clé vers customer, vide si anonyme)",
    "pr_review_sk": "Identifiant de l'avis",
    "pr_review_rating": "Note de l'avis",
    "pr_item_sk": "Produit noté (clé vers item)",
    "pr_user_sk": "Client auteur (clé vers customer)",
    "pr_order_sk": "Commande liée à l'avis",
    "pr_review_content": "Texte libre de l'avis (donnée non structurée)",
    "i_item_sk": "Identifiant produit (clé de substitution)",
    "i_item_id": "Identifiant produit métier (plusieurs versions possibles)",
    "i_current_price": "Prix courant catalogue",
    "i_wholesale_cost": "Coût d'achat",
    "i_category": "Catégorie de produit",
    "i_class": "Classe de produit",
    "i_brand": "Marque",
    "c_customer_sk": "Identifiant client (clé de substitution)",
    "c_customer_id": "Identifiant client métier",
    "c_birth_year": "Année de naissance",
    "c_birth_country": "Pays de naissance",
    "s_store_sk": "Identifiant magasin (clé de substitution)",
    "s_store_name": "Nom du magasin",
    "s_state": "État du magasin",
    "d_date_sk": "Identifiant date (clé de substitution)",
    "d_date": "Date calendaire",
    "d_year": "Année",
    "d_moy": "Mois de l'année",
    "d_qoy": "Trimestre",
    "imp_item_sk": "Produit comparé (clé vers item)",
    "imp_competitor": "Identifiant du concurrent",
    "imp_competitor_price": "Prix constaté chez le concurrent",
}

# (table_enfant, colonne_enfant) -> (table_parent, colonne_parent)  [relations à vérifier]
RELATIONS = [
    # Ventes magasin
    ("store_sales", "ss_sold_date_sk", "date_dim", "d_date_sk"),
    ("store_sales", "ss_sold_time_sk", "time_dim", "t_time_sk"),
    ("store_sales", "ss_item_sk", "item", "i_item_sk"),
    ("store_sales", "ss_customer_sk", "customer", "c_customer_sk"),
    ("store_sales", "ss_cdemo_sk", "customer_demographics", "cd_demo_sk"),
    ("store_sales", "ss_hdemo_sk", "household_demographics", "hd_demo_sk"),
    ("store_sales", "ss_addr_sk", "customer_address", "ca_address_sk"),
    ("store_sales", "ss_store_sk", "store", "s_store_sk"),
    ("store_sales", "ss_promo_sk", "promotion", "p_promo_sk"),
    # Ventes web
    ("web_sales", "ws_sold_date_sk", "date_dim", "d_date_sk"),
    ("web_sales", "ws_sold_time_sk", "time_dim", "t_time_sk"),
    ("web_sales", "ws_ship_date_sk", "date_dim", "d_date_sk"),
    ("web_sales", "ws_item_sk", "item", "i_item_sk"),
    ("web_sales", "ws_bill_customer_sk", "customer", "c_customer_sk"),
    ("web_sales", "ws_ship_customer_sk", "customer", "c_customer_sk"),
    ("web_sales", "ws_bill_addr_sk", "customer_address", "ca_address_sk"),
    ("web_sales", "ws_web_page_sk", "web_page", "wp_web_page_sk"),
    ("web_sales", "ws_web_site_sk", "web_site", "web_site_sk"),
    ("web_sales", "ws_ship_mode_sk", "ship_mode", "sm_ship_mode_sk"),
    ("web_sales", "ws_warehouse_sk", "warehouse", "w_warehouse_sk"),
    ("web_sales", "ws_promo_sk", "promotion", "p_promo_sk"),
    # Retours
    ("store_returns", "sr_returned_date_sk", "date_dim", "d_date_sk"),
    ("store_returns", "sr_item_sk", "item", "i_item_sk"),
    ("store_returns", "sr_customer_sk", "customer", "c_customer_sk"),
    ("store_returns", "sr_store_sk", "store", "s_store_sk"),
    ("store_returns", "sr_reason_sk", "reason", "r_reason_sk"),
    ("web_returns", "wr_returned_date_sk", "date_dim", "d_date_sk"),
    ("web_returns", "wr_item_sk", "item", "i_item_sk"),
    ("web_returns", "wr_refunded_customer_sk", "customer", "c_customer_sk"),
    ("web_returns", "wr_returning_customer_sk", "customer", "c_customer_sk"),
    ("web_returns", "wr_web_page_sk", "web_page", "wp_web_page_sk"),
    ("web_returns", "wr_reason_sk", "reason", "r_reason_sk"),
    # Stocks
    ("inventory", "inv_date_sk", "date_dim", "d_date_sk"),
    ("inventory", "inv_item_sk", "item", "i_item_sk"),
    ("inventory", "inv_warehouse_sk", "warehouse", "w_warehouse_sk"),
    # Navigation et avis
    ("web_clickstreams", "wcs_click_date_sk", "date_dim", "d_date_sk"),
    ("web_clickstreams", "wcs_click_time_sk", "time_dim", "t_time_sk"),
    ("web_clickstreams", "wcs_item_sk", "item", "i_item_sk"),
    ("web_clickstreams", "wcs_web_page_sk", "web_page", "wp_web_page_sk"),
    ("web_clickstreams", "wcs_user_sk", "customer", "c_customer_sk"),
    ("web_clickstreams", "wcs_sales_sk", "web_sales", "ws_order_number"),
    ("product_reviews", "pr_item_sk", "item", "i_item_sk"),
    ("product_reviews", "pr_user_sk", "customer", "c_customer_sk"),
    ("product_reviews", "pr_order_sk", "web_sales", "ws_order_number"),
    ("product_reviews", "pr_order_sk", "store_sales", "ss_ticket_number"),
    # Prix concurrents, référentiels
    ("item_marketprices", "imp_item_sk", "item", "i_item_sk"),
    ("customer", "c_current_cdemo_sk", "customer_demographics", "cd_demo_sk"),
    ("customer", "c_current_hdemo_sk", "household_demographics", "hd_demo_sk"),
    ("customer", "c_current_addr_sk", "customer_address", "ca_address_sk"),
    ("customer", "c_first_sales_date_sk", "date_dim", "d_date_sk"),
    ("customer", "c_first_shipto_date_sk", "date_dim", "d_date_sk"),
    ("household_demographics", "hd_income_band_sk", "income_band", "ib_income_band_sk"),
    ("promotion", "p_item_sk", "item", "i_item_sk"),
    ("promotion", "p_start_date_sk", "date_dim", "d_date_sk"),
    ("promotion", "p_end_date_sk", "date_dim", "d_date_sk"),
    ("web_page", "wp_customer_sk", "customer", "c_customer_sk"),
    ("web_page", "wp_creation_date_sk", "date_dim", "d_date_sk"),
    ("web_site", "web_open_date_sk", "date_dim", "d_date_sk"),
    ("store", "s_closed_date_sk", "date_dim", "d_date_sk"),
]

# Relations composites (retour -> vente d'origine)
RELATIONS_COMPOSITES = [
    ("store_returns", ["sr_ticket_number", "sr_item_sk"], "store_sales", ["ss_ticket_number", "ss_item_sk"]),
    ("web_returns", ["wr_order_number", "wr_item_sk"], "web_sales", ["ws_order_number", "ws_item_sk"]),
]

# Clé primaire supposée (à vérifier par unicité) : simple ou composite.
CLES_PRIMAIRES = {
    "customer": ["c_customer_sk"], "customer_address": ["ca_address_sk"],
    "customer_demographics": ["cd_demo_sk"], "household_demographics": ["hd_demo_sk"],
    "income_band": ["ib_income_band_sk"], "date_dim": ["d_date_sk"], "time_dim": ["t_time_sk"],
    "item": ["i_item_sk"], "item_marketprices": ["imp_sk"], "promotion": ["p_promo_sk"],
    "reason": ["r_reason_sk"], "ship_mode": ["sm_ship_mode_sk"], "store": ["s_store_sk"],
    "warehouse": ["w_warehouse_sk"], "web_page": ["wp_web_page_sk"], "web_site": ["web_site_sk"],
    "product_reviews": ["pr_review_sk"],
    "inventory": ["inv_date_sk", "inv_item_sk", "inv_warehouse_sk"],
    "store_sales": ["ss_ticket_number", "ss_item_sk"],
    "store_returns": ["sr_ticket_number", "sr_item_sk"],
    "web_sales": ["ws_order_number", "ws_item_sk"],
    "web_returns": ["wr_order_number", "wr_item_sk"],
    # web_clickstreams : pas de clé évidente (journal d'événements)
}
