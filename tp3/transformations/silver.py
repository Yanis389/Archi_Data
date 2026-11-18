"""Zone Silver : données nettoyées, typées explicitement et harmonisées.

Pour chaque table : Bronze (texte) -> trim -> typage (try_cast) -> règles de rejet / signalement /
transformation (transformations/regles.py) -> dédoublonnage exact -> Parquet.
Les lignes rejetées ne sont PAS supprimées : elles vont dans data/quarantaine/<table> avec la ligne
brute (JSON) et l'identifiant de la ou des règles en cause.

Bilan de conservation vérifié pour chaque table :
    lignes Bronze == lignes Silver + lignes en quarantaine + doublons exacts retirés

Sorties : data/silver/<table>, data/quarantaine/<table>,
          outputs/silver_controle.csv, outputs/regles_nettoyage_resultats.csv,
          docs/transformations/regles_nettoyage.md (généré)
Lancement : python -m transformations.silver
"""
import sys
from functools import reduce

from pyspark.sql import Window
from pyspark.sql import functions as F

from lib import config, schemas
from lib.spark_utils import ecrire_csv_rapport, ecrire_parquet, get_spark, log
from transformations import regles

VERSION_REGLES = "uc06-v1"
PROV = ["_source_file", "_batch", "_ingested_at"]
AJOUTS = {   # colonnes dérivées simples (enrichissement sans jointure)
    "item": [("est_version_courante", "i_rec_end_date IS NULL")],
    "store": [("est_version_courante", "s_rec_end_date IS NULL")],
}
DOC = config.TP3_ROOT / "docs" / "transformations" / "regles_nettoyage.md"


def ou(conditions):
    return reduce(lambda a, b: a | b, conditions)


def traiter(spark, table):
    cols = schemas.colonnes(table)
    types = dict(schemas.SCHEMAS[table])
    spec = regles.SPECIFIQUES[table]
    bronze = spark.read.parquet(config.chemin("bronze", table))
    n_bronze = bronze.count()

    # R01 : combien de valeurs le trim / la mise à NULL modifient-elles ?
    modif = bronze.agg(*[
        F.sum(F.when(F.col(c).isNotNull() & ((F.col(c) != F.trim(F.col(c))) | (F.trim(F.col(c)) == "")), 1).otherwise(0)).alias(c)
        for c in cols]).first()
    nb_trim = sum(int(modif[c] or 0) for c in cols)
    trimmed = bronze.select(*[F.nullif(F.trim(F.col(c)), F.lit("")).alias(c) for c in cols], *PROV)

    # R02 : typage explicite ; on garde la trace des conversions impossibles
    conv_fail = ou([F.col(c).isNotNull() & F.col(c).try_cast(types[c]).isNull() for c in cols])
    typed = trimmed.select(
        *[F.col(c).try_cast(types[c]).alias(c) for c in cols],
        conv_fail.alias("_conv_fail"),
        F.to_json(F.struct(*[F.col(c) for c in cols])).alias("_ligne_brute"),   # ligne brute pour la quarantaine
        *PROV)
    cle = schemas.CLES_CANDIDATES[table]
    typed = typed.withColumn("qa_cle_dupliquee", F.count(F.lit(1)).over(Window.partitionBy(*cle)) > 1)

    # Règles de rejet (id -> condition booléenne)
    rejets = [("R02", F.col("_conv_fail")),
              ("R03", ou([F.col(c).isNull() for c in schemas.OBLIGATOIRES[table]]))]
    if table in regles.DIMENSIONS:
        rejets.append(("R05", F.col("qa_cle_dupliquee")))
    for rid, _cat, _desc, cond, _just in spec["rejets"]:
        rejets.append((rid, F.coalesce(F.expr(cond), F.lit(False))))
    typed = typed.withColumn("_motifs", F.array_compact(F.array(*[F.when(c, F.lit(r)) for r, c in rejets])))
    typed = typed.withColumn("_rejet", F.size("_motifs") > 0)

    # Règles de signalement (colonnes qa_*)
    for col, _rid, _cat, _desc, cond, _just in spec["drapeaux"]:
        if col not in typed.columns:
            typed = typed.withColumn(col, F.coalesce(F.expr(cond), F.lit(False)))
    flags = [d[0] for d in spec["drapeaux"]]

    # Comptage des effets de chaque règle : un seul passage
    agg = [F.count(F.lit(1)).alias("n"), F.sum(F.col("_rejet").cast("int")).alias("nb_rejetees")]
    agg += [F.sum(F.when(c, 1).otherwise(0)).alias(f"rej_{r}") for r, c in rejets]
    cnt = typed.drop("_ligne_brute").agg(*agg).first()
    assert cnt["n"] == n_bronze, "le typage ne doit ni ajouter ni perdre de ligne"

    valides = typed.filter(~F.col("_rejet"))
    n_valides = n_bronze - int(cnt["nb_rejetees"] or 0)

    # Transformation explicite (item : marque vide -> libellé), tracée par qa_marque_imputee
    if table == "item":
        valides = valides.withColumn("i_brand", F.coalesce(F.col("i_brand"), F.lit("Non renseigné")))

    # R04 : doublons exacts (toutes colonnes métier identiques)
    dedup = valides.dropDuplicates(cols)
    selection = (cols + flags + [n for n, _ in AJOUTS.get(table, [])] + PROV)
    silver = dedup
    if "qa_cle_dupliquee" in flags:
        # recalculé après le dédoublonnage exact : une ligne dont le doublon a été retiré n'est plus « dupliquée »
        silver = silver.withColumn("qa_cle_dupliquee", F.count(F.lit(1)).over(Window.partitionBy(*cle)) > 1)
    for nom, expr in AJOUTS.get(table, []):
        silver = silver.withColumn(nom, F.expr(expr))
    silver = (silver.select(*selection)
              .withColumn("_silver_at", F.current_timestamp())
              .withColumn("_regles_version", F.lit(VERSION_REGLES)))
    duree = ecrire_parquet(silver, config.chemin("silver", table))

    quarantaine = (typed.filter(F.col("_rejet"))
                   .select("_ligne_brute", F.concat_ws(",", "_motifs").alias("_motifs_rejet"), *PROV)
                   .withColumn("_silver_at", F.current_timestamp()))
    ecrire_parquet(quarantaine, config.chemin("quarantaine", table))

    # Relecture et bilan de conservation
    relu = spark.read.parquet(config.chemin("silver", table))
    n_silver = relu.count()
    cnt_flags = relu.agg(*[F.sum(F.col(f).cast("int")).alias(f) for f in flags]).first().asDict() if flags else {}
    nb_transfo = {"IT-T01": int(cnt_flags.get("qa_marque_imputee") or 0)} if table == "item" else {}
    n_quar = spark.read.parquet(config.chemin("quarantaine", table)).count()
    n_dup = n_valides - n_silver
    bilan_ok = (n_bronze == n_silver + n_quar + n_dup) and n_quar == int(cnt["nb_rejetees"] or 0)

    # Résultats par règle
    res = [dict(table=table, regle=regles.COMMUNES[0][0], action="TRANSFO", categorie=regles.COMMUNES[0][2],
                nb=nb_trim, unite="valeurs", total=n_bronze * len(cols)),
           dict(table=table, regle="R02", action="REJET", categorie="Type incorrect", nb=int(cnt["rej_R02"] or 0), unite="lignes", total=n_bronze),
           dict(table=table, regle="R03", action="REJET", categorie="Identifiant invalide", nb=int(cnt["rej_R03"] or 0), unite="lignes", total=n_bronze),
           dict(table=table, regle="R04", action="DEDOUBLON", categorie="Doublon", nb=n_dup, unite="lignes", total=n_valides)]
    if table in regles.DIMENSIONS:
        res.append(dict(table=table, regle="R05", action="REJET", categorie="Identifiant invalide", nb=int(cnt["rej_R05"] or 0), unite="lignes", total=n_bronze))
    for rid, cat, _d, _c, _j in spec["rejets"]:
        res.append(dict(table=table, regle=rid, action="REJET", categorie=cat, nb=int(cnt[f"rej_{rid}"] or 0), unite="lignes", total=n_bronze))
    for col, rid, cat, *_ in spec["drapeaux"]:
        res.append(dict(table=table, regle=rid, action="SIGNALEMENT", categorie=cat, nb=int(cnt_flags[col] or 0), unite="lignes", total=n_silver))
    for rid, cat, *_ in spec.get("transfos", []):
        res.append(dict(table=table, regle=rid, action="TRANSFO", categorie=cat, nb=nb_transfo[rid], unite="valeurs", total=n_silver))
    for rid, cat, *_ in spec.get("notes", []):
        res.append(dict(table=table, regle=rid, action="DECISION", categorie=cat, nb="", unite="", total=""))

    log(f"{'OK  ' if bilan_ok else 'ECART'} silver.{table:14s} bronze={n_bronze:>8d} = silver {n_silver:>8d} + quarantaine {n_quar:>3d} + doublons {n_dup:>3d}  ({duree:.1f}s)")
    controle = dict(table=table, lignes_bronze=n_bronze, lignes_silver=n_silver, lignes_quarantaine=n_quar,
                    doublons_exacts_retires=n_dup, colonnes_silver=len(silver.columns), bilan_conservation="OK" if bilan_ok else "ECHEC",
                    chemin_silver=f"data/silver/{table}", chemin_quarantaine=f"data/quarantaine/{table}")
    return controle, res


def description_regle(table, regle_id):
    """(décision, justification, description) d'une règle, depuis regles.py."""
    for rid, _act, _cat, desc, decision, just in regles.COMMUNES:
        if rid == regle_id:
            return desc, decision, just
    if regle_id == regles.REGLE_CLE_DIMENSION[0]:
        _, _, _, desc, decision, just = regles.REGLE_CLE_DIMENSION
        return desc, decision, just
    s = regles.SPECIFIQUES[table]
    for rid, _cat, desc, _cond, just in s["rejets"]:
        if rid == regle_id:
            return desc, "mise en quarantaine de la ligne", just
    for _col, rid, _cat, desc, _cond, just in s["drapeaux"]:
        if rid == regle_id:
            return desc, "ligne conservée, colonne booléenne qa_* ajoutée", just
    for rid, _cat, desc, decision, just, _col in s.get("transfos", []):
        if rid == regle_id:
            return desc, decision, just
    for rid, _cat, desc, decision, just in s.get("notes", []):
        if rid == regle_id:
            return desc, decision, just
    raise KeyError(regle_id)


def ecrire_doc(res_all, controles):
    L = ["# Règles de nettoyage (UC-06, étapes 4 et 6)", "",
         "Document **généré** par `python -m transformations.silver` à partir de `transformations/regles.py` "
         "et des comptages réels (preuve : `preuves/05_silver.txt`, détail : `outputs/regles_nettoyage_resultats.csv`).", "",
         "Principes (sujet §3.2) : aucune ligne n'est supprimée arbitrairement ; une ligne rejetée est mise en "
         "**quarantaine** avec sa ligne brute et l'identifiant de règle ; une valeur atypique mais plausible est "
         "**conservée et signalée** par une colonne `qa_*` ; toute valeur remplacée l'est par une règle explicite et tracée.", "",
         "Actions : `REJET` (quarantaine) · `SIGNALEMENT` (conservée + colonne `qa_*`) · `TRANSFO` (valeur modifiée) · "
         "`DEDOUBLON` (une occurrence conservée) · `DECISION` (décision documentée sans traitement).", "",
         "## Bilan de conservation", "",
         "| Table | Bronze | Silver | Quarantaine | Doublons exacts retirés | Bronze = Silver + quarantaine + doublons |",
         "|---|---|---|---|---|---|"]
    for c in controles:
        L.append(f"| {c['table']} | {c['lignes_bronze']:,} | {c['lignes_silver']:,} | {c['lignes_quarantaine']:,} | "
                 f"{c['doublons_exacts_retires']:,} | {c['bilan_conservation']} |".replace(",", " "))
    L += ["", "## Règles par table", ""]
    for t in config.SOURCES:
        L += [f"### {t}", "", "| Règle | Anomalie (catégorie) | Constat | Action appliquée | Justification | Concerné |", "|---|---|---|---|---|---|"]
        for r in [x for x in res_all if x["table"] == t]:
            desc, decision, just = description_regle(t, r["regle"])
            concerne = f"{r['nb']:,} {r['unite']}".replace(",", " ") if r["nb"] != "" else "—"
            L.append(f"| {r['regle']} | {r['categorie']} | {desc} | {r['action']} : {decision} | {just} | {concerne} |")
        L.append("")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(L), encoding="utf-8")


def main():
    spark = get_spark("TP3-Silver")
    controles, res_all = [], []
    for t in config.SOURCES:
        c, r = traiter(spark, t)
        controles.append(c)
        res_all += r
    ecrire_csv_rapport(controles, config.OUTPUTS_DIR / "silver_controle.csv", list(controles[0].keys()))
    ecrire_csv_rapport(res_all, config.OUTPUTS_DIR / "regles_nettoyage_resultats.csv", ["table", "regle", "action", "categorie", "nb", "unite", "total"])
    ecrire_doc(res_all, controles)
    log(f"Document des règles généré : {DOC}")
    spark.stop()
    sys.exit(0 if all(c["bilan_conservation"] == "OK" for c in controles) else 1)


if __name__ == "__main__":
    main()
