"""Zone Gold : jeux de données analytiques, chacun répondant à une question métier du Jour 1.

Jointures : aucune n'est faite « sur des noms de colonnes similaires ». Chaque jointure est vérifiée
par `jointure_verifiee` : clé du côté « un » unique ? lignes avant / après ? lignes non rapprochées ?
Une jointure N:1 qui change le nombre de lignes (multiplication ou perte) fait échouer le traitement.

Jeux Gold produits (granularité = ce que représente une ligne) :
  ventes_par_magasin_mois      magasin x mois        (Q01, Q08, Q10 : évolution du CA, comparaison des magasins)
  ventes_par_categorie_annee   catégorie x année     (Q04 : quels produits génèrent le plus de ventes)
  retours_par_motif            motif de retour       (Q05 : retours et motifs)
  taux_retour_par_magasin      magasin               (Q05, Q08 : retours rapportés aux ventes)

Mesures : chiffre d'affaires = SUM(ss_net_paid), défini ainsi au Jour 1 (dictionnaire de KPI).
Sorties : data/gold/<jeu> (versionné), outputs/jointures_verifiees.csv, outputs/gold_controle.csv
Lancement : python -m transformations.gold
"""
import sys

from pyspark.sql import Window
from pyspark.sql import functions as F

from lib import config
from lib.spark_utils import ecrire_csv_rapport, ecrire_parquet, get_spark, log

VERSION = "uc06-v1"
JOINTURES = []


def jointure_verifiee(nom, gauche, droite, cle_g, cle_d, relation, how="inner"):
    """Jointure `gauche` -> `droite` avec contrôles. `droite` est le côté « un » (clé unique attendue)."""
    n_avant = gauche.count()
    cles_droite = droite.select(cle_d)
    droite_unique = cles_droite.count() == cles_droite.distinct().count()
    res = gauche.join(F.broadcast(droite), gauche[cle_g] == droite[cle_d], how)
    n_apres = res.count()
    non_rapproches = gauche.filter(F.col(cle_g).isNotNull()).join(cles_droite, gauche[cle_g] == cles_droite[cle_d], "left_anti").count()
    sans_cle = gauche.filter(F.col(cle_g).isNull()).count()
    ok = droite_unique and n_apres == n_avant
    JOINTURES.append({
        "jointure": nom, "cle_gauche": cle_g, "cle_droite": cle_d, "relation": relation, "type": how,
        "cle_droite_unique": droite_unique, "lignes_avant": n_avant, "lignes_apres": n_apres,
        "lignes_cle_vide_cote_gauche": sans_cle, "lignes_non_rapprochees": non_rapproches,
        "verdict": "OK" if ok else "ECHEC"})
    log(f"{'OK  ' if ok else 'ECHEC'} jointure {nom}: {n_avant} -> {n_apres} lignes ; non rapprochées={non_rapproches} ; clé unique={droite_unique}")
    if not ok:
        raise SystemExit(f"Jointure {nom} invalide : multiplication ou perte de lignes")
    return res


def marquer(df, sources):
    return df.withColumn("_sources", F.lit(sources)).withColumn("_gold_at", F.current_timestamp()).withColumn("_regles_version", F.lit(VERSION))


def main():
    spark = get_spark("TP3-Gold")
    lire = lambda t: spark.read.parquet(config.chemin("silver", t))
    ss, sr, it, st, dd, rs = (lire(t) for t in ["store_sales", "store_returns", "item", "store", "date_dim", "reason"])
    controles = []

    def ecrire(nom, df, grain, sources):
        df = marquer(df, sources).coalesce(1)
        ecrire_parquet(df, config.chemin("gold", nom))
        relu = spark.read.parquet(config.chemin("gold", nom))
        n = relu.count()
        n_grain = relu.select(*grain).distinct().count()
        ok = n == n_grain
        log(f"{'OK  ' if ok else 'ECHEC'} gold.{nom}: {n} lignes, granularité {grain} unique={ok}")
        controles.append({"jeu": nom, "lignes": n, "colonnes": len(relu.columns), "granularite": " x ".join(grain),
                          "granularite_unique": ok, "sources_silver": sources, "chemin": f"data/gold/{nom}"})
        print(f"\n--- gold.{nom} ---")
        relu.printSchema()
        relu.drop("_sources", "_gold_at", "_regles_version").show(12, truncate=False)

    # ---- Ventes enrichies de la date (N:1 sur d_date_sk) -------------------------------------------------
    dates = dd.select("d_date_sk", "d_date", "d_year", "d_moy")
    ss_d = jointure_verifiee("store_sales -> date_dim", ss, dates, "ss_sold_date_sk", "d_date_sk", "N:1 (plusieurs lignes de vente par jour)").cache()

    # ---- Gold 1 : ventes par magasin et par mois --------------------------------------------------------
    magasins = st.select("s_store_sk", "s_store_name", "s_state")
    ss_dm = jointure_verifiee("store_sales -> store", ss_d, magasins, "ss_store_sk", "s_store_sk", "N:1 (plusieurs ventes par magasin)")
    g1 = (ss_dm.groupBy(F.col("s_store_sk").alias("magasin_sk"), F.col("s_store_name").alias("magasin_nom"),
                        F.col("s_state").alias("magasin_etat"), F.col("d_year").alias("annee"), F.col("d_moy").alias("mois"))
          .agg(F.count(F.lit(1)).alias("nb_lignes"),
               F.countDistinct("ss_ticket_number").alias("nb_tickets"),
               F.countDistinct("d_date").alias("nb_jours_avec_ventes"),
               F.sum("ss_quantity").alias("quantite_vendue"),
               F.sum("ss_ext_sales_price").alias("montant_lignes_brut"),
               F.sum("ss_net_paid").alias("chiffre_affaires"))
          .withColumn("periode", F.format_string("%d-%02d", F.col("annee"), F.col("mois")))
          .withColumn("panier_moyen", F.round(F.col("chiffre_affaires") / F.col("nb_tickets"), 2))
          .select("magasin_sk", "magasin_nom", "magasin_etat", "annee", "mois", "periode", "nb_lignes", "nb_tickets",
                  "nb_jours_avec_ventes", "quantite_vendue", "montant_lignes_brut", "chiffre_affaires", "panier_moyen")
          .orderBy("magasin_sk", "annee", "mois"))
    ecrire("ventes_par_magasin_mois", g1, ["magasin_sk", "annee", "mois"], "silver.store_sales, silver.date_dim, silver.store")

    # ---- Gold 2 : ventes par catégorie et par année -------------------------------------------------------
    produits = it.select("i_item_sk", "i_category")
    ss_di = jointure_verifiee("store_sales -> item", ss_d, produits, "ss_item_sk", "i_item_sk", "N:1 (plusieurs lignes par produit)")
    par_annee = Window.partitionBy("annee")
    g2 = (ss_di.groupBy(F.col("i_category").alias("categorie"), F.col("d_year").alias("annee"))
          .agg(F.count(F.lit(1)).alias("nb_lignes"),
               F.countDistinct("d_date").alias("nb_jours_avec_ventes"),
               F.sum("ss_quantity").alias("quantite_vendue"),
               F.sum("ss_net_paid").alias("chiffre_affaires"))
          .withColumn("part_ca_annee_pct", F.round(100 * F.col("chiffre_affaires") / F.sum("chiffre_affaires").over(par_annee), 2))
          .orderBy("annee", F.desc("chiffre_affaires")))
    ecrire("ventes_par_categorie_annee", g2, ["categorie", "annee"], "silver.store_sales, silver.date_dim, silver.item")

    # ---- Gold 3 : retours par motif -------------------------------------------------------------------------
    motifs = rs.select("r_reason_sk", "r_reason_desc")
    sr_m = jointure_verifiee("store_returns -> reason", sr, motifs, "sr_reason_sk", "r_reason_sk",
                             "N:1 (plusieurs retours par motif), motif vide conservé (left)", how="left")
    total_lignes = sr_m.count()
    g3 = (sr_m.groupBy(F.col("r_reason_sk").alias("motif_sk"),
                       F.coalesce(F.col("r_reason_desc"), F.lit("Motif non renseigné")).alias("motif_libelle"))
          .agg(F.count(F.lit(1)).alias("nb_lignes_retour"),
               F.sum("sr_return_quantity").alias("quantite_retournee"),
               F.sum("sr_return_amt").alias("montant_rembourse"),
               F.sum("sr_net_loss").alias("perte_nette"))
          .withColumn("part_lignes_pct", F.round(100 * F.col("nb_lignes_retour") / F.lit(total_lignes), 2))
          .orderBy(F.desc("nb_lignes_retour")))
    ecrire("retours_par_motif", g3, ["motif_libelle"], "silver.store_returns, silver.reason")

    # ---- Gold 4 : taux de retour par magasin (deux agrégats de même granularité, jointure 1:1) ----------------
    ventes_mag = ss.groupBy(F.col("ss_store_sk").alias("magasin_sk")).agg(
        F.sum("ss_quantity").alias("quantite_vendue"), F.sum("ss_ext_sales_price").alias("montant_lignes_brut"),
        F.sum("ss_net_paid").alias("chiffre_affaires"))
    retours_mag = sr.groupBy(F.col("sr_store_sk").alias("retour_magasin_sk")).agg(
        F.sum("sr_return_quantity").alias("quantite_retournee"), F.sum("sr_return_amt").alias("montant_rembourse"))
    v_r = jointure_verifiee("ventes_par_magasin -> retours_par_magasin", ventes_mag, retours_mag, "magasin_sk", "retour_magasin_sk",
                            "1:1 (un agrégat par magasin de chaque côté)")
    g4 = (jointure_verifiee("ventes+retours -> store", v_r, magasins, "magasin_sk", "s_store_sk", "N:1 (agrégat par magasin vers sa fiche)")
          .select(F.col("magasin_sk"), F.col("s_store_name").alias("magasin_nom"), "quantite_vendue", "quantite_retournee",
                  F.round(100 * F.col("quantite_retournee") / F.col("quantite_vendue"), 3).alias("taux_retour_quantite_pct"),
                  "montant_lignes_brut", "montant_rembourse",
                  F.round(100 * F.col("montant_rembourse") / F.col("montant_lignes_brut"), 3).alias("taux_retour_montant_pct"),
                  "chiffre_affaires")
          .orderBy("magasin_sk"))
    ecrire("taux_retour_par_magasin", g4, ["magasin_sk"], "silver.store_sales, silver.store_returns, silver.store")

    ecrire_csv_rapport(JOINTURES, config.OUTPUTS_DIR / "jointures_verifiees.csv", list(JOINTURES[0].keys()))
    ecrire_csv_rapport(controles, config.OUTPUTS_DIR / "gold_controle.csv", list(controles[0].keys()))
    spark.stop()
    sys.exit(0 if all(c["granularite_unique"] for c in controles) else 1)


if __name__ == "__main__":
    main()
