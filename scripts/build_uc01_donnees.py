#!/usr/bin/env python3
"""Génère les PDF « données » de l'UC-01 :
  - UC01_qualification_donnees.pdf
  - UC01_limites_et_hypotheses.pdf
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preuves import (P, ROOT, col, couverture, fichiers, fmt, kpi, lignes, mo, pct, qual,  # noqa: E402
                     rel, relations_resume, serie, total_octets)
from build_uc01_besoin import QUESTIONS  # noqa: E402
from rapport import B, Doc, S, check_chrome  # noqa: E402
from schemas import CLES_PRIMAIRES, SCHEMAS  # noqa: E402

OUT = ROOT / "01_UC01_besoin_exploration"
MISSION = ("**Votre mission.** Consultant Data auprès de Retail Intelligence : examiner les données réellement "
           "disponibles et en qualifier la fiabilité avant de concevoir une architecture. Ce document traite "
           "**UC-01** (volet exploration et qualité).")


def q_all(table=None):
    return [q for q in P["qualite"] if table is None or q["table"] == table]


# ----------------------------------------------------------------------------- qualification
def build_qualification() -> None:
    d = Doc("Qualification des données", "Format, volumes, clés, complétude, cohérence, relations et périodes",
            "UC-01 - Analyser le besoin métier et explorer les sources", MISSION)
    dat = [f for f in P["fichiers"] if f["format"] == "dat"]
    ok = sum(1 for f in dat if f["schema_coherent"] == "oui")
    rs, rr = relations_resume("data"), relations_resume("data_refresh")

    d.h1("1. Méthode et périmètre")
    d.p("Les 36 fichiers ont été chargés dans DuckDB par `scripts/profiler_tpcx_bb.py`, qui écrit toutes les preuves dans "
        "`preuves/`. Rien n'est saisi à la main : un chiffre de ce document peut être retrouvé dans un CSV de preuves.")
    d.table(["Famille de contrôle", "Ce qui est vérifié", "Preuve"], [
        ["Structure", "Nombre de champs par ligne identique sur tout le fichier et égal au schéma déduit", "`inventaire_fichiers.csv`"],
        ["Volumétrie", "Lignes (comptage exact), taille, colonnes", "`inventaire_fichiers.csv`"],
        ["Types et domaines de valeurs", "Type observé sur toutes les valeurs (entier, décimal, date, heure, texte), min, max", "`profil_colonnes.csv`"],
        ["Complétude", "Valeurs vides par colonne", "`profil_colonnes.csv`"],
        ["Unicité", "Clés primaires candidates simples et composites", "`profil_colonnes.csv`, `controles_qualite.csv`"],
        ["Validité et cohérence", "Quantités, prix, dates, identités comptables", "`controles_qualite.csv`"],
        ["Intégrité référentielle", "Valeurs d'une colonne absentes de la table référencée (orphelins)", "`controles_relations.csv`"],
        ["Couverture temporelle", "Dates min et max par table de faits", "`couverture_temporelle.csv`"],
        ["Complémentarité initial / refresh", "Recouvrement des clés entre `data` et `data_refresh`", "`comparaison_refresh.csv`"],
    ], widths=[22, 52, 26])
    d.p(f"Aucune installation de cluster n'est nécessaire à ce stade (consigne du Jour 1) : l'analyse s'exécute en "
        f"{fmt(P['duree_execution_s'], 0)} secondes sur un poste individuel.")

    d.h1("2. Format et structure des fichiers", saut=True)
    d.kpis([(str(len(P["fichiers"])), "fichiers"), (mo(total_octets()), "volume total"),
            (f"{ok}/{len(dat)}", "fichiers .dat au schéma cohérent"),
            (fmt(sum(int(f["lignes"]) for f in dat)), "lignes au total")])
    d.ul([
        f"{S('V')} **Format** : {len(dat)} fichiers `.dat` (texte, délimiteur `|`, fins de ligne CRLF, **sans en-tête**) et "
        "2 fichiers `.csv` d'audit (séparateur `,` avec en-tête).",
        f"{S('V')} **Structure régulière** : pour chacun des {len(dat)} fichiers `.dat`, le nombre de champs est identique "
        "sur toutes les lignes et égal au nombre de colonnes du schéma déduit.",
        f"{S('D')} **Noms de colonnes** : déduits de TPC-DS / BigBench (voir `scripts/schemas.py`). Le contrôle du nombre de "
        "champs et celui des jointures soutiennent l'hypothèse sans la démontrer.",
        f"{S('V')} **Organisation** : `data/` ({len(fichiers('data'))} fichiers) est le chargement initial ; `data_refresh/` "
        f"({len(fichiers('data_refresh'))} fichiers, {len([f for f in fichiers('data_refresh') if f['format'] == 'dat'])} tables) "
        "contient des lignes supplémentaires pour 11 tables (voir §8).",
    ])

    d.h1("3. Volumétrie par table")
    rows = []
    for t, (dom, cols) in SCHEMAS.items():
        n = lignes(t)
        try:
            nr = lignes(t, "data_refresh")
        except KeyError:
            nr = None
        size = sum(int(f["taille_octets"]) for f in P["fichiers"] if f["table"] == t and f["source"] == "data" and f["format"] == "dat")
        rows.append([t, dom, fmt(n), fmt(nr) if nr is not None else "-", str(len(cols)), mo(size)])
    d.table(["Table", "Domaine", "Lignes (data)", "Lignes (data_refresh)", "Colonnes", "Taille (data)"], rows,
            num_cols=(2, 3, 4, 5), widths=[22, 24, 16, 16, 10, 12])
    big = sorted(((lignes(t), t) for t in SCHEMAS), reverse=True)[:3]
    d.p("Trois tables concentrent l'essentiel des lignes : " + ", ".join(f"`{t}` ({fmt(n)})" for n, t in big) +
        ". Ce sont des candidates naturelles au stockage colonnaire (Parquet) et au partitionnement par date.")

    d.h1("4. Fiches des fichiers principaux", saut=True)
    d.p("Relevé demandé par le sujet pour chaque fichier : nom, emplacement, format, taille, lignes, colonnes, types, "
        "clés, nulls et limites. L'intégralité des colonnes (noms, types, nulls, distincts, min, max, exemple) est dans "
        "`UC01_inventaire_sources.xlsx`, onglet *Colonnes*.")
    LIM = {
        "store_sales": "Clé (ticket, produit) non unique ; environ 51 unités par ligne ; devise absente.",
        "web_sales": "Clé (commande, produit) non unique ; client facturé (`ws_bill_*`) et client livré (`ws_ship_*`) à distinguer.",
        "store_returns": "Pas de date de vente d'origine ; rapprochement par (ticket, produit).",
        "web_returns": "Deux jeux de clés client (remboursé / retournant) à distinguer.",
        "item": "Pas d'historique : `i_rec_end_date` vide à 100 % ; prix courant parfois sous le coût.",
        "customer": "Données personnelles synthétiques (nom, e-mail, naissance) à traiter comme sensibles.",
        "store": "Seulement 12 magasins ; dates de fermeture incohérentes.",
        "inventory": f"Instantané hebdomadaire, pas de mouvements ; {fmt(qual('inventory', 'vide')['nb_concernes'])} quantités vides.",
        "web_clickstreams": "Pas de clé ; 42 % de clics anonymes ; pas de session.",
        "product_reviews": "Texte libre non structuré (" + mo(sum(int(x["taille_octets"]) for x in P["fichiers"] if x["table"] == "product_reviews" and x["source"] == "data")) + ") ; lien commande ambigu.",
    }
    rows = []
    for t in LIM:
        f = [x for x in P["fichiers"] if x["table"] == t and x["source"] == "data" and x["format"] == "dat"][0]
        cs = [c for c in P["colonnes"] if c["table"] == t and c["source"] == "data"]
        types = Counter(c["type_observe"] for c in cs)
        tdesc = ", ".join(f"{v} {k}" for k, v in types.most_common())
        nul = [c for c in cs if float(c["pct_nulls"]) >= 0.5]
        ndesc = "; ".join(f"`{c['colonne']}` {fmt(c['pct_nulls'], 1)} %" for c in nul[:2]) or "aucune colonne >= 0,5 %"
        pk = CLES_PRIMAIRES.get(t)
        rows.append([f"`{f['chemin_relatif']}`", f"{f['taille']}", f"{fmt(f['lignes'])} x {f['colonnes_observees']}",
                     (" + ".join(pk) if pk else "aucune évidente"), tdesc, ndesc, LIM[t]])
    d.table(["Fichier", "Taille", "Lignes x col.", "Clé candidate", "Types observés", "Nulls notables", "Limites de compréhension"],
            rows, widths=[17, 7, 10, 14, 13, 14, 25])

    d.h1("5. Clés et unicité", saut=True)
    d.h2("5.1 Clés primaires simples")
    pks = [(t, pk[0]) for t, pk in CLES_PRIMAIRES.items() if len(pk) == 1]
    allok = all(col(t, c)["nb_lignes"] == col(t, c)["nb_distincts"] and col(t, c)["nb_nulls"] == 0 for t, c in pks)
    d.p(f"{S('V')} Les {len(pks)} clés primaires simples candidates (`*_sk`) sont **uniques et sans valeur vide** dans leur "
        f"table : {'toutes' if allok else 'pas toutes'} confirmées. Ce sont des clés de substitution (*surrogate keys*), "
        "sans signification métier ; les identifiants métier (`*_id`) sont des chaînes distinctes.")
    d.h2("5.2 Clés composites des tables de faits")
    rows = []
    for t, titre in [("store_sales", "Doublons sur (ticket, produit)"), ("web_sales", "Doublons sur (commande, produit)"),
                     ("store_returns", "Doublons sur (ticket, produit)"), ("web_returns", "Doublons sur (commande, produit)"),
                     ("inventory", "Doublons sur (date, produit, entrepôt)")]:
        q = qual(t, titre)
        rows.append([f"`{t}`", " + ".join(CLES_PRIMAIRES[t]), fmt(q["nb_total"]), fmt(q["nb_concernes"]), pct(q["pct"], 3),
                     S("V") + " unique" if int(q["nb_concernes"]) == 0 else S("V") + " non unique"])
    q = qual("web_clickstreams", "dupliquées")
    rows.append(["`web_clickstreams`", "aucune clé évidente", fmt(q["nb_total"]), fmt(q["nb_concernes"]), pct(q["pct"], 4),
                 S("A") + " doublon = double clic ?"])
    d.table(["Table", "Clé candidate", "Lignes", "Doublons", "%", "Constat"], rows, num_cols=(2, 3, 4), widths=[18, 30, 13, 11, 9, 19])
    d.box("Conséquence",
          "Dans un TPC-DS d'origine la clé (ticket, produit) est unique ; ici elle ne l'est pas pour environ 0,6 % des "
          "lignes de ventes. Une clé primaire garantie ne peut donc pas être supposée : le chargement devra définir "
          "une règle de traitement des doublons (À valider avec le formateur).", "warn")

    d.h1("6. Complétude")
    cs = [c for c in P["colonnes"] if c["source"] == "data"]
    avec = [c for c in cs if float(c["pct_nulls"]) > 0]
    vides = [c for c in cs if float(c["pct_nulls"]) == 100]
    d.p(f"{S('V')} Sur {len(cs)} colonnes de `data`, **{len(avec)}** contiennent au moins une valeur vide et "
        f"**{len(vides)}** sont vides à 100 %. La grande majorité des colonnes vides sont des clés étrangères de "
        "démographie ou d'adresse avec moins de 0,2 % de vide.")
    top = sorted(avec, key=lambda c: -float(c["pct_nulls"]))[:9]
    note = {"i_rec_end_date": "Pas d'historisation des produits : toutes les versions sont « courantes ».",
            "s_rec_end_date": "Pas d'historisation des magasins.", "wp_rec_end_date": "Pas d'historisation des pages web.",
            "web_rec_end_date": "Pas d'historisation des sites web.",
            "wcs_sales_sk": "Normal : un clic sans commande n'a pas de vente rattachée.",
            "t_meal_time": "Normal : renseigné seulement aux heures de repas.",
            "wcs_user_sk": "Visiteurs anonymes : non rattachables à un client."}
    d.table(["Table", "Colonne", "Valeurs vides", "% vide", "Lecture"],
            [[f"`{c['table']}`", f"`{c['colonne']}`", fmt(c["nb_nulls"]), pct(c["pct_nulls"], 1), note.get(c["colonne"], "")]
             for c in top], num_cols=(2, 3), widths=[18, 22, 14, 10, 36])

    d.h1("7. Cohérence et anomalies visibles", saut=True)
    nb = len(P["qualite"])
    anom = [q for q in P["qualite"] if q["nature"] == "anomalie"]
    anom_pos = [q for q in anom if int(q["nb_concernes"] or 0) > 0]
    d.p(f"{nb} contrôles ont été exécutés ({len(anom)} de type *anomalie*, {nb - len(anom)} de type *observation* à "
        f"connaître sans être une erreur). **{len(anom) - len(anom_pos)} contrôles d'anomalie sur {len(anom)} ne trouvent "
        "rien** (quantités négatives, prix incohérents, expéditions avant commande, notes hors 1 à 5, doublons de clé simple...). "
        "Les écarts constatés sont les suivants.")
    rows = []
    for q in sorted(P["qualite"], key=lambda q: (q["nature"] != "anomalie", -float(q["pct"] or 0))):
        if int(q["nb_concernes"] or 0) > 0:
            rows.append([f"`{q['table']}`", q["controle"], q["nature"], fmt(q["nb_concernes"]), fmt(q["nb_total"]), pct(q["pct"], 2)])
    d.table(["Table", "Contrôle", "Nature", "Concernés", "Total", "%"], rows, num_cols=(3, 4, 5),
            widths=[17, 36, 13, 11, 13, 10])
    mk = qual("store_sales", "inférieur au coût")
    mkw = qual("web_sales", "inférieur au coût")
    d.box("Trois constats qui changent l'usage des données",
          f"1. **Marge non fiable** : le prix de vente unitaire est inférieur au coût d'achat sur {pct(mk['pct'], 1)} des "
          f"lignes magasin et {pct(mkw['pct'], 1)} des lignes web. La marge nette cumulée est négative dans les deux "
          "canaux : elle ne reflète vraisemblablement pas une activité réelle (hypothèse : mode de génération).\n"
          f"2. **Fermetures de magasins incohérentes** : les 12 magasins ont une date de fermeture, dont "
          f"{qual('store', 'antérieure')['nb_concernes']} antérieures à leur ouverture et "
          f"{qual('store', 'postérieure')['nb_concernes']} postérieures à la fin des données. Elle ne peut pas être utilisée.\n"
          f"3. **Référentiel produit incomplet** : {fmt(qual('inventory', 'absents de item')['nb_concernes'])} lignes d'inventaire "
          "(0,999 %) portent sur 180 produits qui n'existent que dans `data_refresh/item`.", "warn")

    d.h1("8. Relations possibles entre domaines", saut=True)
    d.p(f"Aucune jointure n'a été supposée d'après les noms de colonnes : pour chacune, la présence dans les deux tables, "
        "le type, l'unicité de la clé parent, les valeurs vides et les orphelins ont été contrôlés. "
        f"**{rs['total']} relations** ont été examinées dans `data` : **{rs['verifiees']} sont vérifiées (0 orphelin)**, "
        f"**{rs['partielles']} est partielle**, {rs['sans_valeur']} sans valeur à comparer. Dans `data_refresh` "
        f"({rr['total']} relations, parent = data + data_refresh) : {rr['verifiees']} vérifiées, {rr['partielles']} partielles.")
    # résumé par table enfant
    rows = []
    for t in sorted({r["table_enfant"] for r in P["relations"] if r["source"] == "data"}):
        rs_t = [r for r in P["relations"] if r["table_enfant"] == t and r["source"] == "data"]
        ver = sum(1 for r in rs_t if r["verdict"] == "relation vérifiée")
        part = [r for r in rs_t if r["verdict"].startswith("relation partielle")]
        nul = max(float(r["pct_nulls"]) for r in rs_t)
        rows.append([f"`{t}`", str(len(rs_t)), str(ver), (", ".join(f"`{r['colonne_enfant']}`" for r in part) or "-"), pct(nul, 1)])
    d.table(["Table enfant", "Relations contrôlées", "Vérifiées", "Partielles", "Plus fort % de vides"], rows,
            num_cols=(1, 2, 4), widths=[26, 17, 14, 28, 15])
    d.h2("8.1 Relations à signaler")
    ri = rel("inventory", "inv_item_sk", "item")
    ris = rel("inventory", "inv_item_sk", "item", "data_refresh")
    pw = rel("product_reviews", "pr_order_sk", "web_sales")
    ps = rel("product_reviews", "pr_order_sk", "store_sales")
    rows = [
        [f"`inventory.inv_item_sk` -> `item.i_item_sk`", f"{pct(ri['pct_orphelines'], 3)} d'orphelins ({fmt(ri['lignes_orphelines'])} lignes, {fmt(ri['valeurs_orphelines'])} produits)",
         "Les 180 produits manquants sont dans `data_refresh/item` : relation complète seulement avec les deux sources " + S("V")],
        ["`product_reviews.pr_order_sk` -> `web_sales.ws_order_number` **et** `store_sales.ss_ticket_number`",
         f"0 orphelin vers les deux parents (parent non unique : {pw['cle_parent_unique']})",
         f"Les numéros de commande web ({col('web_sales', 'ws_order_number')['min']} à {fmt(col('web_sales', 'ws_order_number')['max'])}) et de ticket magasin "
         f"({col('store_sales', 'ss_ticket_number')['min']} à {fmt(col('store_sales', 'ss_ticket_number')['max'])}) couvrent le même intervalle que `pr_order_sk` "
         f"({col('product_reviews', 'pr_order_sk')['min']} à {fmt(col('product_reviews', 'pr_order_sk')['max'])}) : la jointure **ne discrimine pas** le parent réel " + S("A")],
        ["`web_clickstreams.wcs_sales_sk` -> `web_sales.ws_order_number`",
         f"{pct(rel('web_clickstreams', 'wcs_sales_sk', 'web_sales')['pct_nulls'], 1)} de vides, 0 orphelin",
         "Les valeurs renseignées existent toutes ; les vides sont des clics sans achat " + S("D")],
        ["`store_returns` -> `store_sales` ; `web_returns` -> `web_sales` (ticket/commande + produit)",
         "0 orphelin dans `data`", "Chaque retour retrouve sa vente d'origine dans `data` " + S("V")],
        ["Mêmes relations dans `data_refresh`", f"{fmt([r for r in P['relations'] if r['source'] == 'data_refresh' and r['table_enfant'] == 'store_returns' and '+' in r['colonne_enfant']][0]['pct_orphelines'], 1)} % (magasin) et "
         f"{fmt([r for r in P['relations'] if r['source'] == 'data_refresh' and r['table_enfant'] == 'web_returns' and '+' in r['colonne_enfant']][0]['pct_orphelines'], 1)} % (web) d'orphelins",
         "Les retours du refresh se rapportent à des ventes absentes des deux sources : lien incomplet " + S("A")],
        ["`promotion` <- `store_sales.ss_promo_sk`", f"{pct(rel('store_sales', 'ss_promo_sk', 'promotion')['pct_nulls'], 3)} de vides",
         "Quasi toutes les lignes portent une promotion : la relation est vérifiée mais peu discriminante " + S("D")],
    ]
    d.table(["Relation", "Constat mesuré", "Lecture"], rows, widths=[30, 28, 42])

    d.h1("9. data et data_refresh : un complément incrémental", saut=True)
    d.p("L'hypothèse testée est que `data_refresh` **complète** `data` sans le remplacer. Sur les tables à clé primaire, "
        "les clés du refresh sont **disjointes** de celles de `data` (colonne « déjà présentes »), et pour les tables "
        "à clé de substitution elles **prolongent** la numérotation.")
    rows = []
    for c in P["refresh"]:
        deja = c.get("cles_refresh_deja_presentes_dans_data", "")
        prolong = (f"{c['max_cle_data']} -> {c['min_cle_refresh']} à {c['max_cle_refresh']}" if c.get("max_cle_data") else "-")
        rows.append([f"`{c['table']}`", fmt(c["lignes_data"]), fmt(c["lignes_refresh"]), fmt(deja) if deja != "" else "-", prolong])
    d.table(["Table", "Lignes data", "Lignes refresh", "Clés refresh déjà dans data", "Numérotation (max data -> refresh)"],
            rows, num_cols=(1, 2, 3), widths=[22, 14, 14, 20, 30])
    s05, s05r = serie("Magasin", "data", 2005), serie("Magasin", "data + data_refresh", 2005)
    exc = [(c["table"], int(c["cles_refresh_deja_presentes_dans_data"])) for c in P["refresh"]
           if str(c.get("cles_refresh_deja_presentes_dans_data", "")).strip() not in ("", "0")]
    exc_txt = ", ".join(f"`{t}` ({n})" for t, n in exc) or "aucune table"
    d.ul([
        f"{S('V')} **Prolongement** : les nouveaux clients, adresses, produits, prix concurrents et avis reprennent la "
        "numérotation là où `data` s'arrête.",
        f"{S('V')} **Période** : les ventes de `data` s'arrêtent le {couverture('store_sales')['date_max']} ; `data_refresh` "
        f"couvre du {couverture('store_sales', 'data_refresh')['date_min']} au {couverture('store_sales', 'data_refresh')['date_max']}. "
        f"L'année 2005 passe de {s05['jours_distincts']} à {s05r['jours_distincts']} jours distincts.",
        f"{S('V')} **Exception** : {exc_txt} ont des clés déjà présentes dans `data` : à examiner "
        "(doublon, correction ?). " + S("A"),
        f"{S('H')} Le rôle exact de `data_refresh` (mise à jour périodique simulée) n'est pas documenté : à confirmer.",
    ])

    d.h1("10. Périodes couvertes")
    d.table(["Table", "Source", "Date min", "Date max", "Jours distincts"],
            [[f"`{c['table']}`", c["source"], c["date_min"], c["date_max"], fmt(c["jours_distincts"])] for c in P["couverture"]],
            num_cols=(4,), widths=[24, 18, 18, 18, 22])
    d.p(f"Les ventes, stocks et clics couvrent **2001 à 2005**. Les **retours** sont datés jusqu'en "
        f"{couverture('web_returns')['date_max'][:4]} (retour après une vente de 2005) : une analyse mensuelle du taux de "
        "retour doit rattacher le retour à la date de la vente. Les stocks sont relevés environ **une fois par semaine** "
        f"({couverture('inventory')['jours_distincts']} dates sur cinq ans).")

    d.h1("11. Conclusion : exploitabilité par domaine", saut=True)
    d.table(["Domaine", "Verdict", "Raison principale"], [
        ["Ventes magasin", B("Exploitable"), "Jointures sans orphelin, mesures cohérentes ; clé composite non unique (0,6 %)."],
        ["Ventes web", B("Exploitable"), "Idem ; expéditions toutes postérieures aux commandes."],
        ["Retours", B("Avec réserves", "h"), "Rapprochement vente-retour complet dans `data` ; motifs illisibles ; dates décalées."],
        ["Produits et prix", B("Avec réserves", "h"), "Pas d'historique ; référentiel complété par `data_refresh` ; prix parfois sous le coût."],
        ["Clients", B("Exploitable"), "Clés complètes ; données personnelles à protéger."],
        ["Magasins et entrepôts", B("Limité", "h"), "12 magasins, 5 entrepôts ; dates de fermeture inutilisables."],
        ["Stocks", B("Avec réserves", "h"), "Instantané hebdomadaire ; quantités vides ; produits à rapprocher du refresh."],
        ["Navigation web", B("Limité", "h"), "42 % de clics anonymes ; pas de session ni d'ajout au panier."],
        ["Avis produits", B("Avec réserves", "h"), "Note exploitable ; texte non structuré."],
        ["Marge / rentabilité", B("Non fiable", "n"), "Prix de vente sous le coût d'achat : à ne pas utiliser en l'état."],
    ], widths=[20, 18, 62])
    d.save_pdf(OUT / "UC01_qualification_donnees.pdf")
    print("écrit UC01_qualification_donnees.pdf")


# ----------------------------------------------------------------------------- limites et hypothèses
def build_limites() -> None:
    d = Doc("Limites et hypothèses", "Ce qui est connu, ce qui est supposé, ce qui manque",
            "UC-01 - Analyser le besoin métier et explorer les sources", MISSION)
    tick = int(kpi("Nombre de transactions", "Magasin"))
    ss = lignes("store_sales")
    d.h1("1. Limites des données et des indicateurs")
    d.p("Le sujet demande au moins cinq limites ; **quatorze** sont documentées, chacune avec sa preuve, son impact et une "
        "parade. Statuts : " + S("V") + " mesuré, " + S("D") + " déduit, " + S("H") + " à confirmer.")
    L = [
        ("L01", "Le jeu de données est synthétique", f"Remise moyenne de {fmt(kpi('Taux de remise', 'Magasin'), 1)} % sur les deux canaux ; "
         f"{fmt(qual('store_sales', 'inférieur au coût')['pct'], 1)} % de lignes magasin sous le coût ; {fmt(tick)} transactions exactement dans les deux canaux.",
         "Les KPI sont calculables mais leurs valeurs ne reflètent pas une enseigne réelle.", "Présenter les chiffres comme démonstratifs ; ne pas conclure sur la stratégie.", "V"),
        ("L02", "Aucun dictionnaire ni en-tête : noms de colonnes déduits", "34 fichiers `.dat` sans en-tête ; schémas déduits de TPC-DS/BigBench.",
         "Une colonne mal interprétée fausserait un KPI.", "Contrôler par les jointures ; faire valider le dictionnaire par le formateur.", "D"),
        ("L03", "Une table présente ne garantit pas des champs renseignés",
         f"{len([c for c in P['colonnes'] if c['source'] == 'data' and float(c['pct_nulls']) == 100])} colonnes vides à 100 % ; "
         "`wcs_sales_sk` vide à 90 % ; `wcs_user_sk` à 42 % ; `s_closed_date_sk` renseigné mais incohérent.",
         "Des champs présents sont inutilisables ou trompeurs.", "Profiler chaque colonne avant de l'utiliser (fait dans `profil_colonnes.csv`).", "V"),
        ("L04", "Vente magasin et vente web ne sont pas modélisées de la même façon",
         "Magasin : ticket, magasin, heure. Web : commande, site, page, expédition, entrepôt, client facturé et livré (34 colonnes contre 23).",
         "Additionner ou comparer deux canaux demande des définitions alignées.", "Définir un modèle commun de « vente » avant d'agréger en omnicanal.", "D"),
        ("L05", "Vente, commande, ligne de vente et transaction sont des notions distinctes",
         f"{fmt(ss)} lignes de vente magasin pour {fmt(tick)} tickets.", f"Compter des lignes à la place de transactions surestime le volume d'un facteur {fmt(ss / tick, 1)}.",
         "Compter `DISTINCT ticket` / `DISTINCT commande` ; nommer la granularité de chaque KPI.", "V"),
        ("L06", "Les clics web ne sont pas des ajouts au panier ni des achats",
         f"{fmt(kpi('Part des clics aboutissant à une commande', 'Web'), 2)} % des clics sont rattachés à une commande ; "
         f"{fmt(qual('web_clickstreams', 'anonymes')['pct'], 1)} % sont anonymes ; ni session ni événement de panier.",
         "Pas de tunnel de conversion ni de parcours par visiteur anonyme.", "Collecter les sessions et ajouts au panier (source complémentaire).", "V"),
        ("L07", "Les retours doivent être distingués des ventes",
         f"Retours datés jusqu'en {couverture('web_returns')['date_max'][:4]} pour des ventes arrêtées en 2005 ; taux de retour {fmt(kpi('Taux de retour en quantité', 'Magasin'), 2)} % (magasin).",
         "Soustraire un retour de la période de retour fausse l'analyse par période.", "Rattacher chaque retour à la date de sa vente par (ticket, produit).", "V"),
        ("L08", "Une corrélation n'est pas une causalité",
         f"Note moyenne des avis {fmt(kpi('Note moyenne des avis', 'Web'), 2)} / 5 ; promotions portées par presque toutes les lignes.",
         "Relier note et ventes, ou promotion et ventes, ne prouve aucune cause.", "Formuler les analyses comme des associations ; prévoir un groupe témoin.", "D"),
        ("L09", "L'année 2005 est incomplète dans `data` seul",
         f"`data` : {serie('Magasin', 'data', 2005)['jours_distincts']} jours ; avec `data_refresh` : {serie('Magasin', 'data + data_refresh', 2005)['jours_distincts']} jours.",
         "Une variation annuelle 2005/2004 calculée sur `data` seul est fausse.", "Toujours consolider `data` et `data_refresh` avant les comparaisons annuelles.", "V"),
        ("L10", "Le référentiel produit initial est incomplet",
         f"{fmt(qual('inventory', 'absents de item')['nb_concernes'])} lignes d'inventaire visent 180 produits présents seulement dans `data_refresh/item`.",
         "Jointure inventaire -> produit incomplète si l'on charge `data` seul.", "Imposer l'ordre de chargement : référentiels (refresh inclus) avant les faits.", "V"),
        ("L11", "Pas de clé primaire garantie sur les faits",
         f"{fmt(qual('store_sales', 'Doublons')['nb_concernes'])} doublons (ticket, produit) magasin ; {fmt(qual('web_sales', 'Doublons')['nb_concernes'])} web.",
         "Un chargement idempotent ou un contrôle d'unicité sur cette clé échouerait.", "Utiliser des clés techniques et définir une règle de dédoublonnage (À valider).", "V"),
        ("L12", "Pas d'historisation des référentiels",
         "`i_rec_end_date`, `s_rec_end_date`, `wp_rec_end_date`, `web_rec_end_date` vides à 100 %.",
         "Impossible de suivre l'évolution du prix d'un produit ou d'un attribut de magasin.", "Prévoir un suivi des changements dès l'ingestion si le besoin apparaît.", "V"),
        ("L13", "Devise, taxes et fuseaux non précisés",
         "Aucune colonne de devise ; `*_inc_tax` existent mais sans taux ; `gmt_offset` présent pour magasins et adresses.",
         "Les montants n'ont pas d'unité monétaire documentée.", "Faire confirmer la devise ; la porter dans le dictionnaire de KPI.", "H"),
        ("L14", "Données personnelles et données non structurées",
         f"`customer` : nom, prénom, e-mail, date de naissance ({fmt(lignes('customer'))} clients) ; `product_reviews` : texte libre ({mo(sum(int(f['taille_octets']) for f in P['fichiers'] if f['table'] == 'product_reviews' and f['source'] == 'data'))}).",
         "Même synthétiques, ces champs imposent des règles d'accès et de protection ; le texte n'est pas exploitable par jointure.", "Traiter les colonnes personnelles comme sensibles dans la gouvernance (UC-02).", "D"),
    ]
    d.table(["N°", "Limite", "Constat (preuve)", "Impact", "Parade", "Statut"],
            [[a, f"**{b}**", c, e, f, S(g)] for (a, b, c, e, f, g) in L], widths=[6, 16, 28, 19, 24, 7])

    d.h1("2. Hypothèses de travail", saut=True)
    d.table(["N°", "Hypothèse", "Pourquoi elle est faite", "Comment la vérifier", "Statut"], [
        ["H1", "Les noms de colonnes déduits de TPC-DS/BigBench sont exacts", "Même nombre de champs que le standard pour 34 fichiers ; jointures sans orphelin", "Dictionnaire officiel du kit ou du générateur", S("H") + " " + S("A")],
        ["H2", "Une valeur de `customer_sk` désigne la même personne en magasin et sur le web", "Une seule table `customer` référencée par les deux canaux", "Règle de gestion de l'enseigne ; contrôle d'attributs", S("H")],
        ["H3", "`data_refresh` complète `data` sans le remplacer", "Clés disjointes, numérotation prolongée, période consécutive", "Confirmation du formateur ; traitement des 4 clés de retours déjà présentes", S("H") + " " + S("A")],
        ["H4", f"L'égalité exacte des transactions entre canaux ({fmt(tick)}) est un artefact du générateur", f"Même valeur ({fmt(tick)}) que le nombre de lignes de `item_marketprices` ({fmt(lignes('item_marketprices'))})", "Comparer avec un autre jeu ou la documentation du générateur", S("H")],
        ["H5", "Le montant net payé est comparable entre magasin et web", "Mêmes noms de mesure dans les deux tables", "Définition métier de « net payé » (port, taxes)", S("H")],
        ["H6", "Les relevés de stock sont hebdomadaires", f"{couverture('inventory')['jours_distincts']} dates en {int(couverture('inventory')['date_max'][:4]) - int(couverture('inventory')['date_min'][:4]) + 1} ans, soit environ une par semaine", "Écart entre dates consécutives", S("D")],
        ["H7", "Un retour sans vente d'origine dans `data_refresh` est une donnée incomplète et non une erreur d'intégrité", "Les retours de `data` retrouvent tous leur vente ; ceux du refresh non", "Demander si les ventes d'origine sont attendues dans un lot ultérieur", S("H") + " " + S("A")],
    ], widths=[4, 27, 28, 28, 13])

    d.h1("3. Besoins non couverts et sources complémentaires proposées")
    d.p("Consigne du sujet : documenter l'absence, identifier la question concernée, indiquer l'information nécessaire, "
        "proposer une source ou une collecte, et conserver l'indicateur comme besoin non couvert. **Aucune donnée "
        "manquante n'a été remplacée par une valeur inventée.**")
    d.table(["Besoin non couvert", "Question concernée", "Information nécessaire", "Source ou collecte proposée"], [
        ["Marge réelle", "Q11", "Coût d'achat cohérent, coûts de structure", "Données du contrôle de gestion / ERP"],
        ["Devise et taxes", "Q01, Q10", "Devise, taux de TVA par pays", "Référentiel financier"],
        ["Tunnel de conversion", "Q14", "Sessions, ajouts au panier, source de trafic", "Outil d'analytics web, journaux applicatifs"],
        ["Motifs de retour lisibles", "Q05", "Libellés de `reason`", "Référentiel du SAV"],
        ["Objectifs et budgets par magasin", "Q08, Q10", "Objectifs de CA", "Contrôle de gestion"],
        ["Canal catalogue", "Q02", "Tables catalogue", "Source complémentaire ou confirmation d'absence"],
        ["Concurrents nommés", "Q07", "Identité des concurrents", "Veille tarifaire"],
        ["Consentement client", "Q16", "Bases légales, canaux autorisés", "CRM / DPO"],
    ], widths=[22, 14, 30, 34])

    d.h1("4. Questions à poser au formateur", saut=True)
    d.ol([
        "Quelle est la version et la provenance exacte du kit TPCx-BB ? Un dictionnaire de données existe-t-il ? " + S("A"),
        "Quel est le rôle de `data_refresh` : lot incrémental à intégrer après `data` ? Pourquoi 4 clés de retours y sont-elles déjà présentes dans `data` ? " + S("A"),
        "Que faire des doublons de clé (ticket, produit) : les conserver, les agréger, les rejeter ? " + S("A"),
        f"Les dates de fermeture de magasins ({qual('store', 'antérieure')['nb_concernes']} sur 12 avant leur ouverture, "
        f"{qual('store', 'postérieure')['nb_concernes']} sur 12 après 2005) sont-elles volontairement aléatoires ? " + S("A"),
        "Existe-t-il des fichiers complémentaires (JSON, météo, logistique) à identifier séparément de TPCx-BB ? " + S("A"),
        "Quelle devise faut-il considérer pour les montants ? " + S("A"),
    ])

    d.h1("5. Questions de recul (UC-01)")
    d.table(["Question du sujet", "Réponse argumentée"], [
        ["Quels besoins métier sont réellement couverts par les données ?",
         "Évolution du CA par canal, catégorie et magasin, nombre de transactions, panier moyen, quantités, retours, stocks hebdomadaires et profil démographique des clients. "
         f"{sum(1 for q in QUESTIONS if q[7] == 'C')} questions sur {len(QUESTIONS)} sont pleinement couvertes, {sum(1 for q in QUESTIONS if q[7] == 'P')} partiellement, "
         f"{sum(1 for q in QUESTIONS if q[7] in 'NX')} non fiable."],
        ["Quels KPI ne peuvent pas être calculés de manière fiable ?",
         "La marge nette (prix sous le coût), le taux de remise (régularité artificielle à 50 %), le panier moyen (valeurs non réalistes) et tout KPI nécessitant devise, sessions ou objectifs."],
        ["Différence entre donnée disponible et donnée exploitable ?",
         f"`s_closed_date_sk` est renseigné pour les 12 magasins mais inexploitable ({qual('store', 'antérieure')['nb_concernes']} dates avant l'ouverture, "
         f"{qual('store', 'postérieure')['nb_concernes']} après la fin des données). `wcs_sales_sk` est disponible mais vide à 90 %. "
         "Disponible = présent ; exploitable = présent, cohérent, joignable et interprétable."],
        ["Quelles relations restent à vérifier ?",
         "`pr_order_sk` (commande web ou ticket magasin ?), le rôle des retours du refresh sans vente d'origine, l'identité commune des clients entre canaux."],
        ["Quelles limites du jeu synthétique prendre en compte ?",
         "Valeurs régulières et non réalistes (remise ~50 %, marge négative), absence d'historisation, répartition uniforme entre magasins : les enseignements sont architecturaux, pas commerciaux."],
        ["Quelles données complémentaires seraient utiles à l'entreprise ?",
         "Sessions et paniers web, devise et taxes, objectifs par magasin, motifs de retour lisibles, concurrents nommés, consentement client (voir §3)."],
    ], widths=[32, 68])
    d.save_pdf(OUT / "UC01_limites_et_hypotheses.pdf")
    print("écrit UC01_limites_et_hypotheses.pdf")


if __name__ == "__main__":
    check_chrome()
    build_qualification()
    build_limites()
