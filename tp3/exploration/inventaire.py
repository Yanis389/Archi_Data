"""Étape 2 - Inventorier les sources : pour chaque source retenue, relève le nom réel du fichier,
son emplacement, son format, sa taille, son nombre de lignes et de colonnes, les types observés,
la clé candidate, la granularité et les anomalies repérées.

Rien n'est supposé : le nombre de champs est mesuré ligne par ligne (histogramme), l'encodage est
validé octet par octet, les types sont inférés par Spark puis comparés aux types déclarés.

Sorties : outputs/inventaire_sources.csv, outputs/inventaire_colonnes.csv,
          docs/data-dictionary/inventaire_technique.md (généré).
Lancement : python -m exploration.inventaire
"""
import os
from pathlib import Path

from pyspark.sql import functions as F

from lib import config, schemas
from lib.spark_utils import (get_spark, humain, log, nb_nuls, ecrire_csv_rapport)

DOC = config.TP3_ROOT / "docs" / "data-dictionary" / "inventaire_technique.md"


def encodage_utf8_valide(chemin: str) -> bool:
    """Décode le fichier en UTF-8 strict, ligne à ligne (pas de chargement complet en mémoire)."""
    with open(chemin, "rb") as f:
        for ligne in f:
            ligne.decode("utf-8")
    return True


def histogramme_champs(spark, chemin: str) -> dict:
    """Nombre de lignes par nombre de champs (découpage sur '|', champs vides conservés)."""
    texte = spark.read.text(chemin)
    h = texte.select(F.size(F.split("value", r"\|", -1)).alias("nb_champs")).groupBy("nb_champs").count()
    return {r["nb_champs"]: r["count"] for r in h.collect()}


def main():
    spark = get_spark("TP3-Inventaire")
    sources, colonnes_rows = [], []
    for t in config.SOURCES:
        chemin = config.chemin_source(t)
        log(f"Inventaire de {t}")
        taille = os.path.getsize(chemin)
        try:
            utf8 = encodage_utf8_valide(chemin)
        except UnicodeDecodeError:
            utf8 = False
        histo = histogramme_champs(spark, chemin)
        nb_lignes = sum(histo.values())
        attendu = len(schemas.colonnes(t))

        # types observés : inférence Spark sur le fichier complet (premier passage de lecture)
        infere = (spark.read.option("header", False).option("sep", "|").option("inferSchema", True)
                  .option("quote", "\u0000").csv(chemin))
        types_infere = [f.dataType.simpleString() for f in infere.schema.fields]
        decl = schemas.SCHEMAS[t]

        from lib.spark_utils import lire_brut
        brut = lire_brut(spark, t).cache()
        nuls = nb_nuls(brut)
        cle = schemas.CLES_CANDIDATES[t]
        nb_distinct_cle = brut.select(*cle).distinct().count()
        nb_nuls_total = {c: v for c, v in nuls.items() if v}
        esp = {c: brut.filter(F.col(c) != F.trim(F.col(c))).count() for c in brut.columns}
        esp = {c: v for c, v in esp.items() if v}

        for i, (nom, type_decl) in enumerate(decl):
            n_dist = brut.select(nom).distinct().count()
            colonnes_rows.append({
                "table": t, "position": i + 1, "colonne": nom, "type_declare": type_decl,
                "type_infere_spark": types_infere[i] if i < len(types_infere) else "?",
                "nb_nuls": nuls[nom], "pct_nuls": round(100 * nuls[nom] / nb_lignes, 3),
                "nb_distincts": n_dist})
        anomalies = []
        if nb_nuls_total:
            anomalies.append("valeurs vides : " + ", ".join(f"{c}={v}" for c, v in nb_nuls_total.items()))
        if nb_distinct_cle != nb_lignes:
            anomalies.append(f"clé candidate {'+'.join(cle)} non unique : {nb_lignes - nb_distinct_cle} lignes en excès")
        if esp:
            anomalies.append("espaces superflus : " + ", ".join(f"{c}={v}" for c, v in esp.items()))
        sources.append({
            "table": t,
            "fichier": f"{t}.dat",
            "emplacement": str(Path(chemin).relative_to(config.RETAIL_PROJECT.parent)),
            "format": "texte délimité par le caractère pipe, sans en-tête (.dat), UTF-8 valide" if utf8 else "texte pipe, encodage NON UTF-8",
            "taille_octets": taille, "taille": humain(taille),
            "nb_lignes": nb_lignes, "nb_colonnes_attendu": attendu,
            "histogramme_champs_par_ligne": "; ".join(f"{k} champs: {v} lignes" for k, v in sorted(histo.items())),
            "structure_coherente": histo.keys() == {attendu},
            "cle_candidate": "+".join(cle), "nb_cles_distinctes": nb_distinct_cle,
            "cle_unique": nb_distinct_cle == nb_lignes,
            "granularite": schemas.GRANULARITES[t],
            "anomalies": " ; ".join(anomalies) if anomalies else "aucune",
        })
        brut.unpersist()

    ecrire_csv_rapport(sources, config.OUTPUTS_DIR / "inventaire_sources.csv", list(sources[0].keys()))
    ecrire_csv_rapport(colonnes_rows, config.OUTPUTS_DIR / "inventaire_colonnes.csv", list(colonnes_rows[0].keys()))
    ecrire_markdown(sources, colonnes_rows)
    log(f"Inventaire écrit : {DOC}")
    for s in sources:
        print(f"{s['table']:14s} {s['taille']:>9s} {s['nb_lignes']:>8d} lignes  {s['nb_colonnes_attendu']:>2d} col  "
              f"structure_ok={s['structure_coherente']}  cle_unique={s['cle_unique']}")
    spark.stop()


def ecrire_markdown(sources, cols):
    L = ["# Inventaire technique des sources (UC-06, étape 2)", "",
         "Document **généré** par `python -m exploration.inventaire` à partir des fichiers réels "
         "(chiffres mesurés, preuve : `preuves/02_inventaire.txt`). Statut des noms de colonnes : "
         "**déduits** de la structure TPC-DS (les .dat n'ont pas d'en-tête), vérifiés par le nombre de champs "
         "mesuré sur chaque ligne et par les jointures (rapport qualité).", "",
         "Lot traité : lot initial (`retail_project/data`). Le lot `data_refresh` n'est pas traité dans ce TP.", "",
         "## Synthèse", "",
         "| Information | " + " | ".join(s["table"] for s in sources) + " |",
         "|---|" + "---|" * len(sources)]
    def ligne(label, cle, fmt=lambda x: x):
        L.append(f"| {label} | " + " | ".join(str(fmt(s[cle])) for s in sources) + " |")
    ligne("Nom réel du fichier", "fichier")
    ligne("Emplacement (relatif à `Annexes/`)", "emplacement", lambda x: f"`{x}`")
    ligne("Format", "format")
    ligne("Taille", "taille")
    ligne("Nombre de lignes", "nb_lignes", lambda x: f"{x:,}".replace(",", " "))
    ligne("Nombre de colonnes", "nb_colonnes_attendu")
    ligne("Champs par ligne (mesuré)", "histogramme_champs_par_ligne")
    ligne("Clé candidate", "cle_candidate", lambda x: f"`{x}`")
    ligne("Clé unique ?", "cle_unique", lambda x: "oui" if x else "**non**")
    ligne("Granularité (1 ligne =)", "granularite")
    ligne("Anomalies identifiées", "anomalies")
    L += ["", "## Types observés et colonnes", "",
          "`type_infere_spark` = inférence automatique de Spark sur le fichier complet (simple exploration, "
          "pas une validation de schéma). `type_declare` = type retenu dans `lib/schemas.py`. "
          "Les écarts attendus : Spark infère `double` pour les montants (déclarés `DECIMAL(12,2)` pour "
          "éviter les erreurs d'arrondi) et `timestamp` ou `date` pour les dates selon les valeurs.", ""]
    for s in sources:
        t = s["table"]
        L += [f"### {t}", "", "| # | Colonne | Type déclaré | Type inféré Spark | Nuls | % nuls | Distincts |",
              "|---|---|---|---|---|---|---|"]
        for c in [c for c in cols if c["table"] == t]:
            L.append(f"| {c['position']} | `{c['colonne']}` | {c['type_declare']} | {c['type_infere_spark']} | "
                     f"{c['nb_nuls']} | {c['pct_nuls']} | {c['nb_distincts']} |")
        L.append("")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
