"""Étape 8 - Utiliser le format Parquet : écriture, relecture vérifiée, comparaison de formats, limites.

1. Relecture vérifiée : un jeu Silver et les jeux Gold sont copiés en Parquet dans le répertoire de test
   dédié (jamais sur les sources ni sur les zones), relus, puis comparés à l'original : schéma, nombre de
   lignes, valeurs (exceptAll dans les deux sens), répertoire de sortie.
2. Comparaison CSV / JSON / Parquet sur le même jeu (silver.store_sales) : taille, durée d'écriture, durée
   de lecture d'une agrégation sur une colonne, types conservés après relecture.
3. Preuves de l'organisation en colonnes : lecture d'une colonne vs de toutes, pushdown de filtre (plan Spark).
4. Limites de Parquet seul : un dossier Parquet n'est pas une table transactionnelle (démonstration minimale).

Sorties : data/parquet_test/ (non versionné), outputs/parquet_relecture.csv, outputs/comparaison_formats.csv
Lancement : python -m transformations.parquet_formats
"""
import shutil
import statistics
import sys
import time

from pyspark.sql import functions as F

from lib import config, schemas
from lib.spark_utils import ecrire_csv_rapport, get_spark, humain, log, taille_octets

T = config.PARQUET_TEST_DIR
REPETITIONS = 3


def chrono(fonction, n=REPETITIONS):
    """Durées (s) de n exécutions ; retourne (min, médiane)."""
    durees = []
    for _ in range(n):
        debut = time.perf_counter()
        fonction()
        durees.append(time.perf_counter() - debut)
    return min(durees), statistics.median(durees)


def types_df(df):
    return {f.name: f.dataType.simpleString() for f in df.schema.fields}


def main():
    spark = get_spark("TP3-Parquet")
    T.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- 1. relecture vérifiée -------------
    log("1. Écriture en Parquet, relecture et vérification")
    relectures = []
    jeux = [("silver", "store_sales")] + [("gold", g) for g in
            ["ventes_par_magasin_mois", "ventes_par_categorie_annee", "retours_par_motif", "taux_retour_par_magasin"]]
    for zone, nom in jeux:
        original = spark.read.parquet(config.chemin(zone, nom))
        cible = str(T / f"{zone}_{nom}_copie")
        original.write.mode("overwrite").parquet(cible)          # overwrite : uniquement dans le répertoire de test
        relu = spark.read.parquet(cible)
        n0, n1 = original.count(), relu.count()
        schema_ok = types_df(original) == types_df(relu)
        diff = original.exceptAll(relu).count() + relu.exceptAll(original).count()
        ok = n0 == n1 and schema_ok and diff == 0
        log(f"{'OK  ' if ok else 'ECHEC'} {zone}.{nom}: {n0} -> {n1} lignes, schéma identique={schema_ok}, lignes différentes={diff}")
        if nom == "ventes_par_magasin_mois":
            relu.printSchema()
            relu.drop("_sources", "_gold_at", "_regles_version").show(5, truncate=False)
        relectures.append({"jeu": f"{zone}.{nom}", "repertoire_sortie": f"data/parquet_test/{zone}_{nom}_copie",
                           "lignes_original": n0, "lignes_relues": n1, "schema_identique": schema_ok,
                           "lignes_differentes_exceptAll": diff, "taille": humain(taille_octets(cible)),
                           "statut": "OK" if ok else "ECHEC"})
    ecrire_csv_rapport(relectures, config.OUTPUTS_DIR / "parquet_relecture.csv", list(relectures[0].keys()))

    # ---------------------------------------------------------------- 2. comparaison de formats -----------
    log("2. Comparaison CSV / JSON / Parquet sur silver.store_sales")
    base = spark.read.parquet(config.chemin("silver", "store_sales")).drop("_ingested_at", "_silver_at").cache()
    n = base.count()
    ddl = ", ".join(f"{f.name} {f.dataType.simpleString()}" for f in base.schema.fields)
    mesures = []

    def tester(nom_format, ecrire, lire, taille_ref=None):
        chemin = str(T / f"store_sales_{nom_format}")
        shutil.rmtree(chemin, ignore_errors=True)
        debut = time.perf_counter()
        ecrire(base.coalesce(4), chemin)
        duree_ecriture = time.perf_counter() - debut
        taille = taille_octets(chemin)
        agg = lambda: lire(chemin).agg(F.sum("ss_net_paid")).collect()
        agg()                                                           # échauffement (listing, JIT)
        mn, med = chrono(agg)
        relu_infere = {  # types SANS schéma imposé : ce que contient réellement le fichier
            "csv": lambda: spark.read.option("header", True).option("inferSchema", True).csv(chemin),
            "json": lambda: spark.read.json(chemin),
            "parquet": lambda: spark.read.parquet(chemin)}[nom_format.split("_")[0]]()
        t_orig, t_relu = types_df(base), types_df(relu_infere)
        altere = [c for c in t_orig if c in t_relu and t_orig[c] != t_relu[c]]
        mesures.append({"format": nom_format, "lignes": n, "taille_octets": taille, "taille": humain(taille),
                        "ecriture_s": round(duree_ecriture, 2), "lecture_agregat_1_colonne_min_s": round(mn, 2),
                        "lecture_agregat_1_colonne_mediane_s": round(med, 2),
                        "colonnes_au_type_altere_sans_schema_impose": len(altere), "colonnes_total": len(t_orig),
                        "exemples_types_alteres": "; ".join(f"{c}: {t_orig[c]} -> {t_relu[c]}" for c in altere[:3])})
        log(f"   {nom_format:12s} {humain(taille):>10s}  écriture {duree_ecriture:5.1f}s  agrégat 1 colonne {med:5.2f}s  types altérés {len(altere)}/{len(t_orig)}")
        return chemin

    tester("csv", lambda d, p: d.write.mode("overwrite").option("header", True).csv(p),
           lambda p: spark.read.option("header", True).schema(ddl).csv(p))
    tester("json", lambda d, p: d.write.mode("overwrite").json(p), lambda p: spark.read.schema(ddl).json(p))
    chemin_parquet = tester("parquet", lambda d, p: d.write.mode("overwrite").parquet(p), lambda p: spark.read.parquet(p))
    tester("parquet_gzip", lambda d, p: d.write.mode("overwrite").option("compression", "gzip").parquet(p),
           lambda p: spark.read.parquet(p))
    # ces entrées sont des variantes de compression Parquet : types_df relit via parquet
    source = config.chemin_source("store_sales")
    mesures.insert(0, {"format": "source .dat (texte pipe)", "lignes": n, "taille_octets": taille_octets(source),
                       "taille": humain(taille_octets(source)), "ecriture_s": "", "lecture_agregat_1_colonne_min_s": "",
                       "lecture_agregat_1_colonne_mediane_s": "", "colonnes_au_type_altere_sans_schema_impose": "",
                       "colonnes_total": len(base.columns), "exemples_types_alteres": "sans en-tête ni types"})
    ecrire_csv_rapport(mesures, config.OUTPUTS_DIR / "comparaison_formats.csv", list(mesures[0].keys()))

    # ---------------------------------------------------------------- 3. organisation en colonnes ----------
    log("3. Parquet : lecture d'une colonne vs toutes les colonnes ; pushdown de filtre")
    pq = lambda: spark.read.parquet(chemin_parquet)
    une = lambda: pq().agg(F.sum("ss_net_paid")).collect()
    colonnes_num = [f.name for f in base.schema.fields if f.dataType.simpleString().startswith(("decimal", "int", "bigint"))]
    toutes = lambda: pq().agg(*[F.sum(c) for c in colonnes_num]).collect()
    une(); toutes()
    m1, md1 = chrono(une)
    mt, mdt = chrono(toutes)
    print(f"Lecture Parquet : 1 colonne = {md1:.2f}s (médiane) ; {len(colonnes_num)} colonnes numériques = {mdt:.2f}s (médiane)")
    print("\nPlan d'exécution d'un filtre sur ss_store_sk (cherchez PushedFilters / ReadSchema) :")
    plan = pq().filter("ss_store_sk = 2").select("ss_ticket_number", "ss_net_paid")._jdf.queryExecution().executedPlan().toString()
    for ligne in plan.splitlines():
        if "FileScan" in ligne or "PushedFilters" in ligne or "ReadSchema" in ligne:
            print("  " + ligne.strip()[:260])

    # ---------------------------------------------------------------- 4. limites de Parquet seul -----------
    log("4. Limites de Parquet seul (pas de transaction, pas de contrôle de schéma)")
    demo = str(T / "demo_limites")
    shutil.rmtree(demo, ignore_errors=True)
    lot1 = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "valeur"])
    lot1.write.mode("append").parquet(demo)
    lot2 = spark.createDataFrame([(3, "c", "extra")], ["id", "valeur", "colonne_en_plus"])
    lot2.write.mode("append").parquet(demo)                         # schéma différent : accepté sans erreur
    lot1.write.mode("append").parquet(demo)                         # même lot rejoué : doublons, aucune protection
    relu = spark.read.parquet(demo)
    print(f"Après 3 ajouts : {relu.count()} lignes (2 + 1 + 2 rejouées), colonnes vues par défaut = {relu.columns}")
    fusion = spark.read.option("mergeSchema", True).parquet(demo)
    print(f"Avec mergeSchema : colonnes = {fusion.columns} ; lignes id=1 en double = {fusion.filter('id = 1').count()}")
    print("-> aucun refus d'un schéma différent, aucune protection contre le rejeu, pas d'historique ni de retour arrière.")
    print("   Un format de table Lakehouse (Delta, Iceberg, Hudi) ajoute un journal de transactions pour cela.")

    spark.stop()
    sys.exit(0 if all(r["statut"] == "OK" for r in relectures) else 1)


if __name__ == "__main__":
    main()
