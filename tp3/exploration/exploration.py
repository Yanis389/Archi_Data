"""Étape 3 - Explorer les données avec PySpark (livrable : script d'exploration + résultats).

Pour chaque source : schéma, échantillon, volume, profil de colonnes (nuls, distincts, min, max),
doublons (clé candidate et lignes exactes), puis contrôles de valeurs atypiques et de cohérence
entre tables. Aucune donnée n'est modifiée ni supprimée à cette étape : on constate, on décide à
l'étape 4 (règles de nettoyage).

Sorties : outputs/profil_colonnes.csv, outputs/valeurs_atypiques.csv
Lancement : python -m exploration.exploration
"""
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, DecimalType, IntegerType, LongType

from lib import config, schemas
from lib.spark_utils import ecrire_csv_rapport, get_spark, lire_type, log, nb_nuls

NUMERIQUES = (IntegerType, LongType, DecimalType, DateType)


def profil(df, table, n):
    nuls = nb_nuls(df)
    distincts = df.agg(*[F.countDistinct(c).alias(c) for c in df.columns]).first()
    stats_cols = [f.name for f in df.schema.fields if isinstance(f.dataType, NUMERIQUES)]
    stats = df.agg(*[x for c in stats_cols for x in (F.min(c).alias(f"min_{c}"), F.max(c).alias(f"max_{c}"))]).first()
    lignes = []
    for f in df.schema.fields:
        c = f.name
        lignes.append({
            "table": table, "colonne": c, "type": f.dataType.simpleString(),
            "nb_nuls": nuls[c], "pct_nuls": round(100 * nuls[c] / n, 3), "nb_distincts": distincts[c],
            "min": stats[f"min_{c}"] if c in stats_cols else "", "max": stats[f"max_{c}"] if c in stats_cols else ""})
    return lignes


def main():
    spark = get_spark("TP3-Exploration")
    profils, atypiques = [], []
    t = {nom: lire_type(spark, nom).cache() for nom in config.SOURCES}

    for nom in config.SOURCES:
        df = t[nom]
        n = df.count()
        print(f"\n{'=' * 100}\nSOURCE {nom}  ({n} lignes, {len(df.columns)} colonnes)\n{'=' * 100}")
        df.printSchema()
        if len(df.columns) > 12:
            df.show(3, truncate=40, vertical=True)
        else:
            df.show(10, truncate=40)
        profils += profil(df, nom, n)
        sans_nul = [r for r in profils if r["table"] == nom and r["nb_nuls"] > 0]
        print("Colonnes avec valeurs manquantes :", {r["colonne"]: r["nb_nuls"] for r in sans_nul} or "aucune")
        cle = schemas.CLES_CANDIDATES[nom]
        dup_cle = df.groupBy(*cle).count().filter("count > 1")
        exces = dup_cle.agg(F.sum(F.col("count") - 1)).first()[0] or 0
        exacts = n - df.dropDuplicates().count()
        print(f"Doublons sur la clé candidate {cle} : {dup_cle.count()} clés répétées, {exces} lignes en excès")
        print(f"Lignes exactement dupliquées (toutes colonnes identiques) : {exacts}")

    ss, sr, it, st, dd, rs = (t[x] for x in config.SOURCES)

    def ctrl(table, controle, nb, total, interpretation):
        atypiques.append({"table": table, "controle": controle, "nb_lignes": nb, "total": total,
                          "pct": round(100 * nb / total, 4) if total else 0, "interpretation": interpretation})

    n_ss, n_sr, n_it = ss.count(), sr.count(), it.count()
    print(f"\n{'=' * 100}\nVALEURS ATYPIQUES ET COHÉRENCE\n{'=' * 100}")
    ctrl("store_sales", "Quantité <= 0", ss.filter("ss_quantity <= 0").count(), n_ss, "aucune : pas de retour mélangé aux ventes")
    ctrl("store_sales", "Prix de vente < 0", ss.filter("ss_sales_price < 0").count(), n_ss, "aucune valeur négative : les retours sont dans store_returns")
    ctrl("store_sales", "Prix de vente = 0", ss.filter("ss_sales_price = 0").count(), n_ss, "articles à 0 : atypique mais possible (offert, promotion) -> conservé et signalé")
    ctrl("store_sales", "Montant ligne != quantité x prix (écart > 0,02)",
         ss.filter(F.abs(F.col("ss_ext_sales_price") - F.col("ss_quantity") * F.col("ss_sales_price")) > config.ECART_MONTANT).count(),
         n_ss, "cohérence interne des mesures : avant d'agréger un chiffre d'affaires")
    ctrl("store_sales", "Prix de vente > prix catalogue", ss.filter("ss_sales_price > ss_list_price").count(), n_ss, "aucune : seules des remises")
    ctrl("store_sales", "Prix de vente < coût d'achat", ss.filter("ss_sales_price < ss_wholesale_cost").count(), n_ss,
         "majorité des lignes : particularité du jeu synthétique, marge non fiable -> conservé et signalé")
    ctrl("store_sales", "Marge nette négative", ss.filter("ss_net_profit < 0").count(), n_ss, "idem : à interpréter avec prudence")
    ctrl("store_returns", "Quantité retournée <= 0", sr.filter("sr_return_quantity <= 0").count(), n_sr, "aucune")
    ctrl("store_returns", "Montant remboursé < 0", sr.filter("sr_return_amt < 0").count(), n_sr, "aucune")
    ctrl("store_returns", "Montant remboursé = 0", sr.filter("sr_return_amt = 0").count(), n_sr, "retour sans remboursement : conservé")
    ctrl("item", "Prix courant <= 0 ou vide", it.filter("i_current_price is null or i_current_price <= 0").count(), n_it, "aucune")
    ctrl("item", "Prix courant < coût d'achat", it.filter("i_current_price < i_wholesale_cost").count(), n_it, "observation métier, conservé")
    ctrl("item", "Marque vide", it.filter("i_brand is null").count(), n_it, "libellé à harmoniser (Non renseigné) en Silver")
    n_dd = dd.count()
    ctrl("date_dim", "d_year != année de d_date", dd.filter(F.col("d_year") != F.year("d_date")).count(), n_dd, "cohérence interne du calendrier")
    ctrl("date_dim", "d_moy != mois de d_date", dd.filter(F.col("d_moy") != F.month("d_date")).count(), n_dd, "cohérence interne du calendrier")

    # s_closed_date_sk : valeurs aberrantes ?
    fer = st.join(dd, st.s_closed_date_sk == dd.d_date_sk, "left").select("s_store_sk", F.col("d_date").alias("date_fermeture"))
    print("\nDates de fermeture déclarées des magasins (jointure date_dim) :")
    fer.orderBy("s_store_sk").show(12, truncate=False)
    plage = ss.join(dd, ss.ss_sold_date_sk == dd.d_date_sk).agg(F.min("d_date").alias("premiere_vente"), F.max("d_date").alias("derniere_vente")).first()
    print(f"Période des ventes : {plage['premiere_vente']} -> {plage['derniere_vente']}")
    apres = ss.join(dd, ss.ss_sold_date_sk == dd.d_date_sk).join(fer, ss.ss_store_sk == fer.s_store_sk).filter(F.col("d_date") > F.col("date_fermeture")).count()
    par_magasin = (ss.join(dd, ss.ss_sold_date_sk == dd.d_date_sk).groupBy("ss_store_sk")
                   .agg(F.min("d_date").alias("premiere_vente")).join(fer, F.col("ss_store_sk") == fer.s_store_sk))
    nb_mag = par_magasin.filter(F.col("date_fermeture") < F.col("premiere_vente")).count()
    n_mag = st.count()
    print(f"Magasins dont la fermeture déclarée précède leur première vente : {nb_mag} sur {n_mag}")
    ctrl("store", "Ventes postérieures à la date de fermeture du magasin", apres, n_ss,
         f"s_closed_date_sk incohérent : {nb_mag} magasins sur {n_mag} ont une fermeture antérieure à leur première vente "
         "(les autres ont des dates futures, 2019 à 2141) -> colonne NON exploitable, on ne filtre pas les ventes dessus")

    # retours vs ventes (clé ticket + article, une même clé peut avoir plusieurs lignes de vente)
    v = (ss.join(dd.select(F.col("d_date_sk").alias("k"), F.col("d_date").alias("date_vente")), ss.ss_sold_date_sk == F.col("k"))
         .groupBy("ss_ticket_number", "ss_item_sk").agg(F.min("date_vente").alias("date_vente"), F.sum("ss_quantity").alias("qte_vendue")))
    r = sr.join(dd.select(F.col("d_date_sk").alias("k2"), F.col("d_date").alias("date_retour")), sr.sr_returned_date_sk == F.col("k2"))
    cond = (r.sr_ticket_number == v.ss_ticket_number) & (r.sr_item_sk == v.ss_item_sk)
    ctrl("store_returns", "Retour sans vente d'origine (ticket + article)", r.join(v, cond, "left_anti").count(), n_sr, "aucun : intégrité retour -> vente")
    m = r.join(v, cond)
    ctrl("store_returns", "Retour daté avant la vente", m.filter("date_retour < date_vente").count(), n_sr, "aucun")
    ctrl("store_returns", "Quantité retournée > quantité vendue", m.filter("sr_return_quantity > qte_vendue").count(), n_sr, "aucun")

    ecrire_csv_rapport(profils, config.OUTPUTS_DIR / "profil_colonnes.csv", list(profils[0].keys()))
    ecrire_csv_rapport(atypiques, config.OUTPUTS_DIR / "valeurs_atypiques.csv", list(atypiques[0].keys()))
    print("\nRésumé des contrôles :")
    for a in atypiques:
        print(f"  {a['table']:14s} {a['controle']:58s} {a['nb_lignes']:>8d} / {a['total']:<8d} ({a['pct']}%)")
    log("Rapports écrits dans outputs/ (profil_colonnes.csv, valeurs_atypiques.csv)")
    spark.stop()


if __name__ == "__main__":
    main()
