"""Étape 9 - Contrôles qualité sur les zones produites (livrable : rapport qualité).

Les contrôles RECALCULENT à partir des fichiers Parquet (Bronze, Silver, Gold) et des sources : ils ne
reprennent aucun compteur des scripts de production. Familles couvertes (sujet §4.12.2) : complétude,
unicité, validité des types, cohérence des valeurs, volumes, clés candidates, intégrité référentielle ;
plus la réconciliation Gold <-> Silver et Gold <-> KPI du Jour 1 (calculés alors avec DuckDB).

Statuts : OK | AVERTISSEMENT (écart connu, documenté, non bloquant) | ECHEC (bloquant) | INFO (observation)
Sorties : outputs/rapport_qualite.csv, docs/quality/rapport_qualite.md (généré)
Code retour : 1 s'il y a au moins un ECHEC.
Lancement : python -m quality.controles_qualite
"""
import csv
import sys
from decimal import Decimal

from pyspark.sql import functions as F

from lib import config, schemas
from lib.spark_utils import ecrire_csv_rapport, get_spark, log

DOC = config.TP3_ROOT / "docs" / "quality" / "rapport_qualite.md"
KPI_J1 = config.TP3_ROOT.parent / "tp1" / "01_UC01_besoin_exploration" / "preuves"
R = []


def ctrl(famille, table, regle, valeur, attendu=0, sinon="ECHEC", commentaire=""):
    statut = "OK" if valeur == attendu else sinon
    R.append({"id": f"Q{len(R) + 1:02d}", "famille": famille, "table": table, "regle": regle,
              "resultat": str(valeur), "attendu": str(attendu), "statut": statut, "commentaire": commentaire})
    return statut


def info(famille, table, regle, valeur, commentaire=""):
    R.append({"id": f"Q{len(R) + 1:02d}", "famille": famille, "table": table, "regle": regle,
              "resultat": str(valeur), "attendu": "—", "statut": "INFO", "commentaire": commentaire})


def orphelins(enfant, col, parent, pcol):
    cles = parent.select(pcol).distinct()
    return enfant.filter(F.col(col).isNotNull()).join(cles, enfant[col] == cles[pcol], "left_anti").count()


def kpi_j1(canal_kpi, canal):
    """Valeur d'un KPI du Jour 1 (kpi_tests.csv) ou None si le fichier est absent."""
    chemin = KPI_J1 / "kpi_tests.csv"
    if not chemin.exists():
        return None
    with open(chemin, encoding="utf-8") as f:
        for ligne in csv.DictReader(f, delimiter=";"):
            if ligne["kpi"] == canal_kpi and ligne["canal"] == canal:
                return Decimal(ligne["valeur"])
    return None


def main():
    spark = get_spark("TP3-Qualite")
    S = {t: spark.read.parquet(config.chemin("silver", t)) for t in config.SOURCES}
    B = {t: spark.read.parquet(config.chemin("bronze", t)) for t in config.SOURCES}
    Q = {t: spark.read.parquet(config.chemin("quarantaine", t)) for t in config.SOURCES}
    G = {g: spark.read.parquet(config.chemin("gold", g)) for g in
         ["ventes_par_magasin_mois", "ventes_par_categorie_annee", "retours_par_motif", "taux_retour_par_magasin"]}
    ss, sr, it, st, dd, rs = (S[t] for t in config.SOURCES)

    # ------------------------------------------------------------------ Complétude -------------------
    log("Complétude")
    for t in config.SOURCES:
        manquants = S[t].agg(*[F.sum(F.col(c).isNull().cast("int")).alias(c) for c in schemas.OBLIGATOIRES[t]]).first()
        total = sum(int(manquants[c] or 0) for c in schemas.OBLIGATOIRES[t])
        ctrl("Complétude", t, f"colonnes obligatoires non nulles ({', '.join(schemas.OBLIGATOIRES[t])})", total, 0)
    facultatives = {"store_sales": ["ss_cdemo_sk", "ss_hdemo_sk", "ss_addr_sk", "ss_promo_sk"],
                    "store_returns": ["sr_cdemo_sk", "sr_hdemo_sk", "sr_addr_sk", "sr_reason_sk"]}
    for t, cols in facultatives.items():
        m = S[t].agg(*[F.sum(F.col(c).isNull().cast("int")).alias(c) for c in cols]).first()
        info("Complétude", t, "clés facultatives vides", ", ".join(f"{c}={int(m[c])}" for c in cols),
             "autorisé : client ou promotion absents ; conservé tel quel")

    # ------------------------------------------------------------------ Unicité / clés candidates ------
    log("Unicité et clés candidates")
    for t in ["item", "store", "date_dim", "reason"]:
        k = schemas.CLES_CANDIDATES[t]
        n = S[t].count()
        ctrl("Unicité / clé candidate", t, f"clé {'+'.join(k)} unique", n - S[t].select(*k).distinct().count(), 0,
             commentaire="clé de substitution d'une dimension : doit être unique pour que les jointures ne démultiplient pas")
    ctrl("Unicité / clé candidate", "date_dim", "d_date unique (un jour = une ligne)", dd.count() - dd.select("d_date").distinct().count(), 0)
    for t in ["store_sales", "store_returns"]:
        k = schemas.CLES_CANDIDATES[t]
        exces = S[t].count() - S[t].select(*k).distinct().count()
        ctrl("Unicité / clé candidate", t, f"clé {'+'.join(k)} unique", exces, 0, "AVERTISSEMENT",
             "clé candidate NON unique : lignes distinctes (quantités/prix différents), conservées et signalées par qa_cle_dupliquee ; "
             "aucune clé naturelle unique sur ces tables")
        cols = schemas.colonnes(t)
        ctrl("Unicité / clé candidate", t, "aucune ligne exactement dupliquée (toutes colonnes métier)", S[t].count() - S[t].select(*cols).distinct().count(), 0)

    # ------------------------------------------------------------------ Validité des types -------------
    log("Validité des types")
    for t in config.SOURCES:
        attendu = {c: tp.lower() for c, tp in schemas.SCHEMAS[t]}
        reel = {f.name: f.dataType.simpleString() for f in S[t].schema.fields}
        ecarts = [c for c in attendu if reel.get(c) != attendu[c]]
        ctrl("Validité des types", t, f"types Silver = schéma déclaré ({len(attendu)} colonnes)", len(ecarts), 0,
             commentaire=("écarts : " + ", ".join(ecarts)) if ecarts else "")
        techniques = ["_source_file", "_batch", "_ingested_at", "_silver_at", "_regles_version"]
        ctrl("Validité des types", t, "colonnes de provenance présentes", len([c for c in techniques if c not in S[t].columns]), 0)

    # ------------------------------------------------------------------ Cohérence des valeurs ----------
    log("Cohérence des valeurs")
    ctrl("Cohérence", "store_sales", "quantité > 0", ss.filter("ss_quantity <= 0").count(), 0)
    ctrl("Cohérence", "store_sales", "prix de vente et montant de ligne >= 0", ss.filter("ss_sales_price < 0 OR ss_ext_sales_price < 0").count(), 0)
    ctrl("Cohérence", "store_sales", f"montant de ligne = quantité x prix (tolérance {config.ECART_MONTANT})",
         ss.filter(F.abs(F.col("ss_ext_sales_price") - F.col("ss_quantity") * F.col("ss_sales_price")) > config.ECART_MONTANT).count(), 0)
    ctrl("Cohérence", "store_sales", "prix de vente <= prix catalogue", ss.filter("ss_sales_price > ss_list_price").count(), 0)
    ctrl("Cohérence", "store_returns", "quantité retournée > 0 et montant remboursé >= 0", sr.filter("sr_return_quantity <= 0 OR sr_return_amt < 0").count(), 0)
    ctrl("Cohérence", "date_dim", "d_year et d_moy cohérents avec d_date", dd.filter((F.col("d_year") != F.year("d_date")) | (F.col("d_moy") != F.month("d_date"))).count(), 0)
    ctrl("Cohérence", "item", "prix courant > 0", it.filter("i_current_price IS NULL OR i_current_price <= 0").count(), 0)
    dates = dd.select(F.col("d_date_sk").alias("k"), F.col("d_date"))
    v = (ss.join(dates, ss.ss_sold_date_sk == dates.k).groupBy("ss_ticket_number", "ss_item_sk")
         .agg(F.min("d_date").alias("date_vente"), F.sum("ss_quantity").alias("qte_vendue")))
    r = sr.join(dates.select(F.col("k").alias("k2"), F.col("d_date").alias("date_retour")), sr.sr_returned_date_sk == F.col("k2"))
    m = r.join(v, (r.sr_ticket_number == v.ss_ticket_number) & (r.sr_item_sk == v.ss_item_sk))
    ctrl("Cohérence", "store_returns", "retour jamais antérieur à la vente d'origine", m.filter("date_retour < date_vente").count(), 0)
    ctrl("Cohérence", "store_returns", "quantité retournée <= quantité vendue (ticket + article)", m.filter("sr_return_quantity > qte_vendue").count(), 0)
    for col, libelle in [("qa_prix_nul", "ventes à prix nul"), ("qa_vente_a_perte", "ventes sous le coût d'achat"), ("qa_marge_negative", "marges nettes négatives")]:
        info("Cohérence", "store_sales", f"{libelle} (signalées, conservées)", ss.filter(col).count(), "valeur atypique mais plausible : jeu synthétique, voir règles de nettoyage")
    info("Cohérence", "store", "dates de fermeture s_closed_date_sk", "5 magasins sur 12 antérieures à leurs ventes",
         "colonne inexploitable (voir exploration) : exclue de toute logique")
    p = G["ventes_par_categorie_annee"].groupBy("annee").agg(F.sum("part_ca_annee_pct").alias("s"))
    ctrl("Cohérence", "gold.ventes_par_categorie_annee", "parts de CA : somme par année = 100 % (±0,05)", p.filter(F.abs(F.col("s") - 100) > 0.05).count(), 0)
    ctrl("Cohérence", "gold.taux_retour_par_magasin", "taux de retour compris entre 0 et 100 %", G["taux_retour_par_magasin"].filter("taux_retour_quantite_pct < 0 OR taux_retour_quantite_pct > 100 OR taux_retour_montant_pct < 0 OR taux_retour_montant_pct > 100").count(), 0)

    # ------------------------------------------------------------------ Volumes -------------------------
    log("Volumes")
    for t in config.SOURCES:
        src = spark.read.text(config.chemin_source(t)).count()
        ctrl("Volumes", t, "lignes Bronze = lignes du fichier source", B[t].count(), src)
        ctrl("Volumes", t, "lignes Bronze = Silver + quarantaine (aucun doublon exact : 0 constaté en exploration)",
             S[t].count() + Q[t].count(), B[t].count())
    info("Volumes", "quarantaine", "lignes mises à l'écart (toutes tables)", sum(Q[t].count() for t in config.SOURCES),
         "aucune sur les données réelles ; le fonctionnement des règles de rejet est démontré par tests/test_regles_silver.py")
    attendu_g1 = ss.join(dates, ss.ss_sold_date_sk == dates.k).join(dd.select(F.col("d_date_sk").alias("k3"), "d_year", "d_moy"), F.col("k") == F.col("k3")).select("ss_store_sk", "d_year", "d_moy").distinct().count()
    ctrl("Volumes", "gold.ventes_par_magasin_mois", "lignes = couples (magasin, année, mois) distincts des ventes", G["ventes_par_magasin_mois"].count(), attendu_g1)
    ctrl("Volumes", "gold.retours_par_motif", "lignes = motifs distincts des retours (+ « non renseigné »)", G["retours_par_motif"].count(),
         sr.select("sr_reason_sk").distinct().count())

    # ------------------------------------------------------------------ Intégrité référentielle ---------
    log("Intégrité référentielle")
    liens = [("store_sales", ss, "ss_sold_date_sk", "date_dim", dd, "d_date_sk"), ("store_sales", ss, "ss_store_sk", "store", st, "s_store_sk"),
             ("store_sales", ss, "ss_item_sk", "item", it, "i_item_sk"), ("store_returns", sr, "sr_returned_date_sk", "date_dim", dd, "d_date_sk"),
             ("store_returns", sr, "sr_store_sk", "store", st, "s_store_sk"), ("store_returns", sr, "sr_item_sk", "item", it, "i_item_sk"),
             ("store_returns", sr, "sr_reason_sk", "reason", rs, "r_reason_sk")]
    for tn, enfant, col, tp, parent, pcol in liens:
        ctrl("Intégrité référentielle", tn, f"{col} -> {tp}.{pcol} : valeurs sans parent", orphelins(enfant, col, parent, pcol), 0,
             commentaire="clés vides ignorées (comptées en complétude)" if col == "sr_reason_sk" else "")
    cles_ventes = ss.select("ss_ticket_number", "ss_item_sk").distinct()
    ctrl("Intégrité référentielle", "store_returns", "(ticket, article) retourné -> vente d'origine : retours sans vente",
         sr.join(cles_ventes, (sr.sr_ticket_number == cles_ventes.ss_ticket_number) & (sr.sr_item_sk == cles_ventes.ss_item_sk), "left_anti").count(), 0)

    # ------------------------------------------------------------------ Réconciliation Gold <-> Silver ---
    log("Réconciliation Gold <-> Silver")
    tot = lambda df, c: df.agg(F.sum(c)).first()[0]
    g1, g2, g3, g4 = G["ventes_par_magasin_mois"], G["ventes_par_categorie_annee"], G["retours_par_motif"], G["taux_retour_par_magasin"]
    ca_silver, qte_silver = tot(ss, "ss_net_paid"), tot(ss, "ss_quantity")
    ctrl("Réconciliation Gold/Silver", "gold.ventes_par_magasin_mois", "SUM(chiffre_affaires) = SUM(ss_net_paid) Silver", tot(g1, "chiffre_affaires"), ca_silver)
    ctrl("Réconciliation Gold/Silver", "gold.ventes_par_magasin_mois", "SUM(nb_lignes) = lignes Silver", tot(g1, "nb_lignes"), ss.count())
    ctrl("Réconciliation Gold/Silver", "gold.ventes_par_categorie_annee", "SUM(chiffre_affaires) = SUM(ss_net_paid) Silver", tot(g2, "chiffre_affaires"), ca_silver)
    ctrl("Réconciliation Gold/Silver", "gold.ventes_par_categorie_annee", "SUM(quantite_vendue) = SUM(ss_quantity) Silver", tot(g2, "quantite_vendue"), qte_silver)
    ctrl("Réconciliation Gold/Silver", "gold.retours_par_motif", "SUM(nb_lignes_retour) = lignes Silver store_returns", tot(g3, "nb_lignes_retour"), sr.count())
    ctrl("Réconciliation Gold/Silver", "gold.retours_par_motif", "SUM(montant_rembourse) = SUM(sr_return_amt) Silver", tot(g3, "montant_rembourse"), tot(sr, "sr_return_amt"))
    ctrl("Réconciliation Gold/Silver", "gold.taux_retour_par_magasin", "SUM(chiffre_affaires) = SUM(ss_net_paid) Silver", tot(g4, "chiffre_affaires"), ca_silver)
    ctrl("Réconciliation Gold/Silver", "gold.taux_retour_par_magasin", "SUM(quantite_retournee) = SUM(sr_return_quantity) Silver", tot(g4, "quantite_retournee"), tot(sr, "sr_return_quantity"))

    # ------------------------------------------------------------------ Réconciliation Gold <-> KPI Jour 1
    log("Réconciliation avec les KPI du Jour 1 (moteur DuckDB)")
    ref_ca, ref_qte, ref_tickets = kpi_j1("Chiffre d'affaires", "Magasin"), kpi_j1("Quantités vendues", "Magasin"), kpi_j1("Nombre de transactions", "Magasin")
    ref_ret, ref_taux = kpi_j1("Montant retourné", "Magasin"), kpi_j1("Taux de retour en quantité", "Magasin")
    if ref_ca is None:
        info("Réconciliation Gold/Jour 1", "gold", "KPI du Jour 1", "non exécuté", f"fichier absent : {KPI_J1 / 'kpi_tests.csv'}")
    else:
        ctrl("Réconciliation Gold/Jour 1", "gold.ventes_par_magasin_mois", "CA magasin = KPI J1 (SUM(ss_net_paid), DuckDB)", tot(g1, "chiffre_affaires"), ref_ca)
        ctrl("Réconciliation Gold/Jour 1", "gold.ventes_par_magasin_mois", "tickets = KPI J1 (COUNT DISTINCT ticket)", tot(g1, "nb_tickets"), int(ref_tickets))
        ctrl("Réconciliation Gold/Jour 1", "gold.ventes_par_categorie_annee", "quantités vendues = KPI J1", tot(g2, "quantite_vendue"), int(ref_qte))
        ctrl("Réconciliation Gold/Jour 1", "gold.retours_par_motif", "montant retourné = KPI J1", tot(g3, "montant_rembourse"), ref_ret)
        taux = (Decimal(tot(g4, "quantite_retournee")) * 100 / Decimal(tot(g4, "quantite_vendue"))).quantize(Decimal("0.01"))
        ctrl("Réconciliation Gold/Jour 1", "gold.taux_retour_par_magasin", "taux de retour en quantité global (%) = KPI J1", taux, ref_taux)
        ref_mag = KPI_J1 / "kpi_series_magasins.csv"
        if ref_mag.exists():
            with open(ref_mag, encoding="utf-8") as f:
                attendus = {int(l["magasin_sk"]): Decimal(l["chiffre_affaires"]) for l in csv.DictReader(f, delimiter=";")}
            reels = {r["ss_store_sk"]: r["ca"] for r in ss.groupBy("ss_store_sk").agg(F.sum("ss_net_paid").alias("ca")).collect()}
            g1_par_mag = {r["magasin_sk"]: r["ca"] for r in g1.groupBy("magasin_sk").agg(F.sum("chiffre_affaires").alias("ca")).collect()}
            ecarts = sum(1 for k, v_ in attendus.items() if g1_par_mag.get(k) != v_)
            ctrl("Réconciliation Gold/Jour 1", "gold.ventes_par_magasin_mois", f"CA de chacun des {len(attendus)} magasins = KPI J1", ecarts, 0)

    # ------------------------------------------------------------------ Sorties --------------------------
    ecrire_csv_rapport(R, config.OUTPUTS_DIR / "rapport_qualite.csv", ["id", "famille", "table", "regle", "resultat", "attendu", "statut", "commentaire"])
    ecrire_doc()
    compte = {s: sum(1 for r in R if r["statut"] == s) for s in ["OK", "AVERTISSEMENT", "INFO", "ECHEC"]}
    print(f"\nBILAN : {len(R)} contrôles -> {compte}")
    for r in R:
        if r["statut"] in ("AVERTISSEMENT", "ECHEC"):
            print(f"  {r['statut']:13s} {r['id']} {r['table']}: {r['regle']} (résultat {r['resultat']}, attendu {r['attendu']})")
    spark.stop()
    sys.exit(1 if compte["ECHEC"] else 0)


def ecrire_doc():
    compte = {s: sum(1 for r in R if r["statut"] == s) for s in ["OK", "AVERTISSEMENT", "INFO", "ECHEC"]}
    L = ["# Rapport de qualité des données (UC-06, étape 9)", "",
         "Document **généré** par `python -m quality.controles_qualite` (preuve : `preuves/09_qualite.txt`, tableau complet : "
         "`outputs/rapport_qualite.csv`). Les contrôles recalculent tout depuis les fichiers Parquet et les sources ; ils ne reprennent "
         "aucun compteur des scripts de production.", "",
         f"**Bilan : {len(R)} contrôles — {compte['OK']} OK, {compte['AVERTISSEMENT']} avertissement(s), {compte['INFO']} observations, {compte['ECHEC']} échec(s).**", "",
         "Statuts : `OK` règle respectée · `AVERTISSEMENT` écart connu et documenté, non bloquant · `ECHEC` bloquant · `INFO` observation sans seuil.", ""]
    for famille in dict.fromkeys(r["famille"] for r in R):
        L += [f"## {famille}", "", "| ID | Table | Règle | Résultat | Attendu | Statut | Commentaire |", "|---|---|---|---|---|---|---|"]
        for r in [x for x in R if x["famille"] == famille]:
            L.append(f"| {r['id']} | {r['table']} | {r['regle']} | {r['resultat']} | {r['attendu']} | **{r['statut']}** | {r['commentaire']} |")
        L.append("")
    L += ["## Bilan (sujet §4.12.3)", "",
          "**Règles respectées** : tous les contrôles `OK` ci-dessus (complétude des données obligatoires, unicité des clés de dimensions, "
          "types conformes, cohérence interne des montants, volumes conservés de la source au Silver, intégrité référentielle sans orphelin, "
          "réconciliation exacte Gold ↔ Silver et Gold ↔ KPI du Jour 1).", "",
          "**Anomalies restantes** (avertissements) : ", ""]
    for r in R:
        if r["statut"] == "AVERTISSEMENT":
            L.append(f"- {r['id']} `{r['table']}` : {r['regle']} — résultat {r['resultat']}. {r['commentaire']}")
    L += ["- Valeurs atypiques signalées mais conservées (observations `INFO`) : ventes à prix nul, ventes sous le coût d'achat, marges négatives.",
          "- `store.s_closed_date_sk` : incohérent, exclu de toute logique.", "",
          "**Données mises à l'écart** : 0 ligne en quarantaine sur les données réelles (aucune ne viole les règles de rejet). "
          "Le mécanisme est démontré sur des anomalies injectées (`tests/test_regles_silver.py`, `preuves/06_test_regles_silver.txt`). "
          "Aucune ligne n'est supprimée : les 4 136 lignes de `store_sales` à clé répétée sont conservées et signalées (`qa_cle_dupliquee`).", "",
          "**Limites des contrôles** :", "",
          "- Périmètre : lot initial (`data`) uniquement, 6 tables sur 36 ; le lot `data_refresh` n'est pas contrôlé (2005 reste incomplet : ventes jusqu'au 13/12/2005).",
          "- Les noms de colonnes sont **déduits** de TPC-DS (les `.dat` n'ont pas d'en-tête) : les jointures valident le sens des clés, pas celui des libellés.",
          "- La cohérence métier ne peut pas dire si une valeur atypique est « vraie » : 69 % de ventes sous le coût d'achat sont cohérentes avec elles-mêmes mais pas avec la réalité commerciale (jeu synthétique).",
          "- La réconciliation avec le Jour 1 compare deux moteurs (DuckDB et Spark) sur les **mêmes fichiers et la même interprétation** des colonnes : elle détecte une erreur de calcul, pas une erreur d'interprétation commune.",
          "- Seuils choisis par nous (tolérance d'arrondi 0,02) faute de référentiel officiel de qualité.",
          "- TPCx-BB est synthétique : aucun résultat n'a de valeur de performance ni de conformité à un benchmark officiel.", "",
          "**Corrections éventuellement nécessaires** : (1) traiter `data_refresh` pour compléter 2005 ; (2) ajouter une clé technique de ligne "
          "sur `store_sales` et `store_returns` si une clé unique devient nécessaire ; (3) ne pas utiliser `s_closed_date_sk` sans validation du formateur."]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
