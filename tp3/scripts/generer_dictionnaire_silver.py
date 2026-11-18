"""Génère docs/data-dictionary/dictionnaire_silver.md : colonnes, types, sens métier, provenance.

Lancement : python scripts/generer_dictionnaire_silver.py   (depuis tp3/)
Les types sont lus dans les Parquet Silver réels (pas recopiés). Statut des noms et des sens : déduit
de TPC-DS (les .dat n'ont pas d'en-tête et le kit ne fournit pas de dictionnaire).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import config, schemas                      # noqa: E402
from lib.spark_utils import get_spark                # noqa: E402

DESC = {
    "ss_sold_date_sk": "Date de la vente (clé vers date_dim)", "ss_sold_time_sk": "Heure de la vente (clé vers time_dim, non chargée)",
    "ss_item_sk": "Produit vendu (clé vers item)", "ss_customer_sk": "Client (clé vers customer, non chargée)",
    "ss_store_sk": "Magasin (clé vers store)", "ss_promo_sk": "Promotion appliquée (facultatif)",
    "ss_ticket_number": "Numéro de ticket de caisse", "ss_quantity": "Quantité vendue sur la ligne",
    "ss_wholesale_cost": "Coût d'achat unitaire", "ss_list_price": "Prix catalogue unitaire", "ss_sales_price": "Prix de vente unitaire",
    "ss_ext_discount_amt": "Remise totale de la ligne", "ss_ext_sales_price": "Montant de la ligne (quantité x prix de vente)",
    "ss_ext_wholesale_cost": "Coût d'achat total de la ligne", "ss_ext_list_price": "Montant de la ligne au prix catalogue",
    "ss_ext_tax": "Taxe de la ligne", "ss_coupon_amt": "Montant des coupons", "ss_net_paid": "Montant net payé, hors taxe (base du chiffre d'affaires)",
    "ss_net_paid_inc_tax": "Montant net payé, taxe incluse", "ss_net_profit": "Marge nette de la ligne (net payé - coût d'achat) ; atypique, voir règles",
    "sr_returned_date_sk": "Date du retour (clé vers date_dim)", "sr_item_sk": "Produit retourné (clé vers item)", "sr_store_sk": "Magasin du retour (clé vers store)",
    "sr_reason_sk": "Motif du retour (clé vers reason, facultatif)", "sr_ticket_number": "Ticket de la vente d'origine",
    "sr_return_quantity": "Quantité retournée", "sr_return_amt": "Montant remboursé, hors taxe", "sr_return_tax": "Taxe remboursée",
    "sr_net_loss": "Perte nette liée au retour", "sr_fee": "Frais de retour", "sr_refunded_cash": "Part remboursée en espèces",
    "i_item_sk": "Identifiant produit (clé de substitution, unique)", "i_item_id": "Identifiant produit métier (peut porter plusieurs versions)",
    "i_rec_start_date": "Début de validité de la version du produit", "i_rec_end_date": "Fin de validité (vide = version courante)",
    "i_item_desc": "Description libre du produit (texte généré)", "i_current_price": "Prix courant catalogue", "i_wholesale_cost": "Coût d'achat",
    "i_brand": "Marque (« Non renseigné » si vide à la source)", "i_class": "Classe de produit", "i_category": "Catégorie de produit",
    "i_product_name": "Nom du produit",
    "s_store_sk": "Identifiant magasin (clé de substitution, unique)", "s_store_id": "Identifiant magasin métier", "s_store_name": "Nom du magasin",
    "s_state": "État du magasin", "s_city": "Ville du magasin", "s_number_employees": "Effectif",
    "s_closed_date_sk": "Date de fermeture (clé vers date_dim) ; INCOHÉRENTE, non exploitable", "s_rec_start_date": "Début de validité de la version du magasin",
    "s_rec_end_date": "Fin de validité (vide = version courante)",
    "d_date_sk": "Identifiant date (clé de substitution, unique)", "d_date": "Date calendaire", "d_year": "Année", "d_moy": "Mois de l'année (1-12)",
    "d_dom": "Jour du mois", "d_dow": "Jour de la semaine", "d_qoy": "Trimestre", "d_day_name": "Nom du jour", "d_weekend": "Week-end (Y/N)", "d_holiday": "Jour férié (Y/N)",
    "r_reason_sk": "Identifiant du motif de retour (unique)", "r_reason_id": "Identifiant métier du motif", "r_reason_desc": "Libellé du motif (texte généré, non lisible métier)",
    "qa_cle_dupliquee": "Indicateur qualité : la clé (ticket, article) apparaît plusieurs fois (lignes distinctes conservées)",
    "qa_prix_nul": "Indicateur qualité : prix de vente égal à 0", "qa_vente_a_perte": "Indicateur qualité : prix de vente inférieur au coût d'achat",
    "qa_marge_negative": "Indicateur qualité : marge nette négative", "qa_remboursement_nul": "Indicateur qualité : montant remboursé égal à 0",
    "qa_motif_manquant": "Indicateur qualité : motif de retour absent", "qa_prix_invalide": "Indicateur qualité : prix courant vide ou <= 0",
    "qa_prix_sous_cout": "Indicateur qualité : prix courant inférieur au coût d'achat", "qa_marque_imputee": "Indicateur qualité : marque remplacée par « Non renseigné »",
    "est_version_courante": "Colonne dérivée : la version n'a pas de date de fin (version courante)",
    "_source_file": "Provenance : chemin relatif du fichier source", "_batch": "Provenance : lot d'ingestion (initial)",
    "_ingested_at": "Provenance : horodatage de l'ingestion Bronze", "_silver_at": "Provenance : horodatage du traitement Silver",
    "_regles_version": "Provenance : version des règles de nettoyage appliquées",
}


def main():
    spark = get_spark("TP3-Dictionnaire")
    L = ["# Dictionnaire des données Silver (UC-06, étape 6)", "",
         "Généré par `scripts/generer_dictionnaire_silver.py` : les types sont lus dans les fichiers Parquet Silver. "
         "Les sens métier sont **déduits** de TPC-DS (les `.dat` n'ont ni en-tête ni dictionnaire fourni). "
         "« — » : colonne conservée mais non utilisée dans ce TP.", "",
         "Convention de nommage : un jeu Silver porte le nom de sa table source ; les colonnes d'origine gardent leur nom TPC-DS "
         "(préfixe de table) ; `qa_*` = indicateur de qualité ; `_*` = provenance ; `est_*` = colonne dérivée.",
         "Provenance de chaque ligne : `_source_file`, `_batch`, `_ingested_at` (Bronze), `_silver_at` et `_regles_version` (Silver). "
         "Les lignes rejetées ne sont pas perdues : `data/quarantaine/<table>` (ligne brute JSON + règles en cause).", ""]
    for t in config.SOURCES:
        df = spark.read.parquet(config.chemin("silver", t))
        n = df.count()
        L += [f"## silver.{t}", "", f"- Chemin : `data/silver/{t}` (Parquet) · {n:,} lignes · {len(df.columns)} colonnes".replace(",", " "),
              f"- Granularité : une ligne = {schemas.GRANULARITES[t]}", f"- Clé candidate : `{'+'.join(schemas.CLES_CANDIDATES[t])}`",
              f"- Colonnes obligatoires (rejet si vides) : {', '.join(f'`{c}`' for c in schemas.OBLIGATOIRES[t])}", "",
              "| Colonne | Type | Description |", "|---|---|---|"]
        for f in df.schema.fields:
            L.append(f"| `{f.name}` | {f.dataType.simpleString()} | {DESC.get(f.name, '—')} |")
        L.append("")
    out = config.TP3_ROOT / "docs" / "data-dictionary" / "dictionnaire_silver.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"Dictionnaire écrit : {out}")
    spark.stop()


if __name__ == "__main__":
    main()
