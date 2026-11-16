#!/usr/bin/env python3
"""Profilage des fichiers TPCx-BB fournis (UC-01 : exploration et qualification des sources).

Lit les `.dat` (délimiteur `|`, sans en-tête) des dossiers `data/` et `data_refresh/`, les charge
dans DuckDB, puis écrit dans `--out` des preuves reproductibles :

  inventaire_fichiers.csv   un fichier = une ligne (chemin, format, taille, lignes, colonnes)
  profil_colonnes.csv       une colonne = une ligne (type observé, nulls, distincts, min/max...)
  controles_relations.csv   taux de correspondance des jointures candidates (clés étrangères)
  controles_qualite.csv     anomalies visibles (doublons, valeurs aberrantes, incohérences)
  comparaison_refresh.csv   data_refresh est-il un complément de data ? (recouvrement des clés)
  kpi_tests.csv             calculs de KPI de test (preuve de calculabilité)
  kpi_series_annuelles.csv  évolution annuelle du CA par canal
  apercu_donnees.txt        premières lignes de chaque table
  arborescence.txt          arborescence des données et tailles
  audit_item_marketprices.txt  contenu des fichiers .csv d'audit
  profil.json               synthèse complète (alimente la génération des livrables)

Les noms de colonnes viennent de `schemas.py` (statut « Déduit », voir ce fichier).

Usage :
    python scripts/profiler_tpcx_bb.py --data ../retail_project --out 01_UC01_besoin_exploration/preuves
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schemas import (CLES_PRIMAIRES, DESCRIPTIONS, RELATIONS, RELATIONS_COMPOSITES,  # noqa: E402
                     SCHEMAS)

SOURCES = ("data", "data_refresh")


# --------------------------------------------------------------------------- utilitaires
def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def tname(table: str, source: str) -> str:
    """Nom de la table DuckDB (suffixe __refresh pour data_refresh)."""
    return table if source == "data" else f"{table}__refresh"


def num(col: str) -> str:
    return f"try_cast(nullif({col}, '') as double)"


def sk(col: str) -> str:
    return f"try_cast(nullif({col}, '') as bigint)"


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(rows)


def human(n: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


# --------------------------------------------------------------------------- découverte
def discover(data_root: Path) -> list[dict]:
    """Inventaire brut des fichiers présents sur disque."""
    files = []
    for source in SOURCES:
        base = data_root / source
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.name != ".DS_Store":
                files.append({"source": source, "table": p.parent.name, "path": p,
                              "rel": str(p.relative_to(data_root)), "taille_octets": p.stat().st_size,
                              "format": p.suffix.lstrip(".")})
    return files


# --------------------------------------------------------------------------- chargement
def count_fields(con, path: Path) -> tuple[int, int, int]:
    """(min, max, nb_lignes) du nombre de champs par ligne, en lisant chaque ligne brute."""
    r = con.execute(
        "select min(length(l) - length(replace(l, '|', '')) + 1), "
        "max(length(l) - length(replace(l, '|', '')) + 1), count(*) "
        f"from read_csv('{path}', delim='\\x01', header=false, columns={{'l':'VARCHAR'}}, "
        "quote='', escape='', strict_mode=false)").fetchone()
    return r[0], r[1], r[2]


def load_tables(con, files: list[dict]) -> None:
    for f in files:
        if f["format"] != "dat":
            continue
        table, source = f["table"], f["source"]
        if table not in SCHEMAS:
            f["note"] = "table absente du dictionnaire déduit"
            continue
        cols = SCHEMAS[table][1]
        f["colonnes_attendues"] = len(cols)
        fmin, fmax, nlines = count_fields(con, f["path"])
        f["champs_min"], f["champs_max"], f["lignes"] = fmin, fmax, nlines
        f["correspond"] = (fmin == fmax == len(cols))
        if not f["correspond"]:
            log(f"  ATTENTION {f['rel']}: {fmin}-{fmax} champs observés, {len(cols)} attendus")
            continue
        spec = ", ".join(f"'{c}': 'VARCHAR'" for c in cols)
        con.execute(
            f"create or replace table {tname(table, source)} as select * from "
            f"read_csv('{f['path']}', delim='|', header=false, columns={{{spec}}}, quote='', "
            "escape='', strict_mode=false)")
        n = con.execute(f"select count(*) from {tname(table, source)}").fetchone()[0]
        assert n == nlines, f"{table}: {n} lignes chargées != {nlines} lignes du fichier"
        log(f"  chargé {tname(table, source):<34} {n:>12,} lignes".replace(",", " "))


# --------------------------------------------------------------------------- profil colonnes
def profile_columns(con, table: str, source: str) -> list[dict]:
    name = tname(table, source)
    domaine, cols = SCHEMAS[table]
    aggs = ["count(*)"]
    for c in cols:
        aggs += [
            f"count(nullif({c}, ''))",
            f"count(distinct nullif({c}, ''))",
            f"count(try_cast(nullif({c}, '') as bigint))",
            f"count({num(c)})",
            f"count(*) filter (where regexp_matches({c}, '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'))",
            f"count(*) filter (where regexp_matches({c}, '^[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}$'))",
            f"min({num(c)})", f"max({num(c)})",
            f"min(nullif({c}, ''))", f"max(nullif({c}, ''))",
            f"max(length({c}))",
            f"any_value(nullif({c}, ''))",
        ]
    row = con.execute(f"select {', '.join(aggs)} from {name}").fetchone()
    total = row[0]
    pk = set(CLES_PRIMAIRES.get(table, []))
    fk = {c for (t, c, _, _) in RELATIONS if t == table}
    out = []
    for i, c in enumerate(cols):
        (nn, nd, ni, nf, nd8, nt, nmin, nmax, smin, smax, ml, ex) = row[1 + 12 * i: 13 + 12 * i]
        if nn == 0:
            typ = "vide"
        elif ni == nn:
            typ = "entier"
        elif nf == nn:
            typ = "décimal"
        elif nd8 == nn:
            typ = "date"
        elif nt == nn:
            typ = "heure"
        else:
            typ = "texte"
        if typ in ("entier", "décimal"):
            vmin, vmax = nmin, nmax
        else:
            vmin, vmax = smin, smax
        if isinstance(ex, str) and len(ex) > 60:
            ex = ex[:57] + "..."
        if isinstance(vmin, str) and len(vmin) > 40:
            vmin = vmin[:37] + "..."
        if isinstance(vmax, str) and len(vmax) > 40:
            vmax = vmax[:37] + "..."
        role = "clé primaire (candidate)" if c in pk and len(pk) == 1 else (
            "clé primaire composite (candidate)" if c in pk else (
                "clé étrangère (candidate)" if c in fk else
                ("mesure" if typ == "décimal" else "attribut")))
        out.append({
            "source": source, "domaine": domaine, "table": table, "position": i + 1,
            "colonne": c, "description": DESCRIPTIONS.get(c, ""), "type_observe": typ,
            "nb_lignes": total, "nb_nulls": total - nn,
            "pct_nulls": round(100 * (total - nn) / total, 3) if total else 0,
            "nb_distincts": nd, "min": vmin, "max": vmax, "longueur_max": ml,
            "exemple": ex, "role": role})
    return out


# --------------------------------------------------------------------------- relations
def parent_keys_sql(parent: str, pcol: str, with_refresh: bool) -> str:
    q = f"select {sk(pcol)} as k from {parent}"
    if with_refresh and parent + "__refresh" in TABLES_PRESENTES:
        q += f" union all select {sk(pcol)} from {parent}__refresh"
    return q


def check_relations(con) -> list[dict]:
    out = []
    for (child, col, parent, pcol) in RELATIONS:
        for source in SOURCES:
            cname = tname(child, source)
            if cname not in TABLES_PRESENTES or parent not in TABLES_PRESENTES:
                continue
            with_refresh = source == "data_refresh"
            sql = f"""
            with p as ({parent_keys_sql(parent, pcol, with_refresh)}),
            pk as (select distinct k from p where k is not null),
            c as (select nullif({col}, '') as raw, {sk(col)} as k from {cname})
            select count(*), count(c.raw), count(c.k),
                   count(*) filter (where c.k is not null and pk.k is null),
                   count(distinct c.k) filter (where c.k is not null and pk.k is null),
                   count(distinct c.k),
                   (select count(k) = count(distinct k) from p)
            from c left join pk on c.k = pk.k"""
            total, nonnull, castable, orph_rows, orph_dist, c_dist, p_unique = con.execute(sql).fetchone()
            out.append({
                "source": source, "table_enfant": child, "colonne_enfant": col,
                "table_parent": parent, "colonne_parent": pcol,
                "portee_parent": "data + data_refresh" if with_refresh else "data",
                "nb_lignes": total, "nb_renseignees": nonnull,
                "pct_nulls": round(100 * (total - nonnull) / total, 3) if total else 0,
                "non_numeriques": nonnull - castable,
                "valeurs_distinctes_enfant": c_dist,
                "lignes_orphelines": orph_rows, "valeurs_orphelines": orph_dist,
                "pct_orphelines": round(100 * orph_rows / castable, 4) if castable else 0,
                "cle_parent_unique": "oui" if p_unique else "non",
                "verdict": ("à confirmer (aucune valeur)" if castable == 0 else
                            "relation vérifiée" if orph_rows == 0 else
                            "relation partielle (orphelins)"),
            })
    for (child, ccols, parent, pcols) in RELATIONS_COMPOSITES:
        for source in SOURCES:
            cname = tname(child, source)
            if cname not in TABLES_PRESENTES:
                continue
            with_refresh = source == "data_refresh"
            psrc = f"select {', '.join(sk(c) + f' as k{i}' for i, c in enumerate(pcols))} from {parent}"
            if with_refresh and parent + "__refresh" in TABLES_PRESENTES:
                psrc += " union all select " + ", ".join(sk(c) for c in pcols) + f" from {parent}__refresh"
            csel = ", ".join(sk(c) + f" as k{i}" for i, c in enumerate(ccols))
            cond = " and ".join(f"c.k{i} = pk.k{i}" for i in range(len(ccols)))
            sql = f"""
            with p as ({psrc}), pk as (select distinct * from p),
            c as (select {csel} from {cname})
            select count(*), count(*) filter (where pk.k0 is null) from c left join pk on {cond}"""
            total, orph = con.execute(sql).fetchone()
            out.append({
                "source": source, "table_enfant": child, "colonne_enfant": " + ".join(ccols),
                "table_parent": parent, "colonne_parent": " + ".join(pcols),
                "portee_parent": "data + data_refresh" if with_refresh else "data",
                "nb_lignes": total, "nb_renseignees": total, "pct_nulls": 0, "non_numeriques": 0,
                "valeurs_distinctes_enfant": "", "lignes_orphelines": orph, "valeurs_orphelines": "",
                "pct_orphelines": round(100 * orph / total, 4) if total else 0,
                "cle_parent_unique": "oui (composite)",
                "verdict": "relation vérifiée" if orph == 0 else "relation partielle (orphelins)"})
    return out


# --------------------------------------------------------------------------- qualité
def quality_checks(con) -> list[dict]:
    """Chaque contrôle renvoie (nb_anomalies, nb_total). 'nature' : anomalie ou observation."""
    C = []

    def add(table, titre, nature, sql, interpretation=""):
        C.append((table, titre, nature, sql, interpretation))

    # -- ventes magasin
    ss = "store_sales"
    add(ss, "Lignes sans client (ss_customer_sk vide)", "observation",
        f"select count(*) filter (where nullif(ss_customer_sk,'') is null), count(*) from {ss}",
        "Ventes anonymes : analyses par client impossibles sur ces lignes.")
    add(ss, "Quantité vendue nulle, vide ou négative", "anomalie",
        f"select count(*) filter (where {num('ss_quantity')} is null or {num('ss_quantity')} <= 0), count(*) from {ss}")
    add(ss, "Prix de vente supérieur au prix catalogue", "anomalie",
        f"select count(*) filter (where {num('ss_sales_price')} > {num('ss_list_price')}), count(*) from {ss}")
    add(ss, "Montant de ligne != quantité x prix de vente (écart > 0,02)", "anomalie",
        f"select count(*) filter (where abs({num('ss_ext_sales_price')} - {num('ss_quantity')}*{num('ss_sales_price')}) > 0.02), count(*) from {ss}",
        "Teste la cohérence interne des mesures avant d'agréger un chiffre d'affaires.")
    add(ss, "Lignes en perte (marge nette négative)", "observation",
        f"select count(*) filter (where {num('ss_net_profit')} < 0), count(*) from {ss}")
    add(ss, "Doublons sur (ticket, produit)", "anomalie",
        f"select count(*) - count(distinct (ss_ticket_number, ss_item_sk)), count(*) from {ss}",
        "Clé primaire composite candidate.")
    # -- ventes web
    ws = "web_sales"
    add(ws, "Lignes sans client facturé (ws_bill_customer_sk vide)", "observation",
        f"select count(*) filter (where nullif(ws_bill_customer_sk,'') is null), count(*) from {ws}")
    add(ws, "Quantité vendue nulle, vide ou négative", "anomalie",
        f"select count(*) filter (where {num('ws_quantity')} is null or {num('ws_quantity')} <= 0), count(*) from {ws}")
    add(ws, "Prix de vente supérieur au prix catalogue", "anomalie",
        f"select count(*) filter (where {num('ws_sales_price')} > {num('ws_list_price')}), count(*) from {ws}")
    add(ws, "Montant de ligne != quantité x prix de vente (écart > 0,02)", "anomalie",
        f"select count(*) filter (where abs({num('ws_ext_sales_price')} - {num('ws_quantity')}*{num('ws_sales_price')}) > 0.02), count(*) from {ws}")
    add(ws, "Expédition avant la commande (ship_date < sold_date)", "anomalie",
        f"select count(*) filter (where {sk('ws_ship_date_sk')} < {sk('ws_sold_date_sk')}), count(*) from {ws}")
    add(ws, "Lignes en perte (marge nette négative)", "observation",
        f"select count(*) filter (where {num('ws_net_profit')} < 0), count(*) from {ws}")
    add(ws, "Doublons sur (commande, produit)", "anomalie",
        f"select count(*) - count(distinct (ws_order_number, ws_item_sk)), count(*) from {ws}")
    # -- retours
    sr, wr = "store_returns", "web_returns"
    add(sr, "Quantité retournée nulle, vide ou négative", "anomalie",
        f"select count(*) filter (where {num('sr_return_quantity')} is null or {num('sr_return_quantity')} <= 0), count(*) from {sr}")
    add(sr, "Doublons sur (ticket, produit)", "anomalie",
        f"select count(*) - count(distinct (sr_ticket_number, sr_item_sk)), count(*) from {sr}")
    add(wr, "Quantité retournée nulle, vide ou négative", "anomalie",
        f"select count(*) filter (where {num('wr_return_quantity')} is null or {num('wr_return_quantity')} <= 0), count(*) from {wr}")
    add(wr, "Doublons sur (commande, produit)", "anomalie",
        f"select count(*) - count(distinct (wr_order_number, wr_item_sk)), count(*) from {wr}")
    # -- stocks
    inv = "inventory"
    add(inv, "Quantité en stock vide", "anomalie",
        f"select count(*) filter (where nullif(inv_quantity_on_hand,'') is null), count(*) from {inv}",
        "Dans TPC-DS d'origine ce champ peut être vide ; à ne pas confondre avec une rupture (zéro).")
    add(inv, "Quantité en stock négative", "anomalie",
        f"select count(*) filter (where {num('inv_quantity_on_hand')} < 0), count(*) from {inv}")
    add(inv, "Doublons sur (date, produit, entrepôt)", "anomalie",
        f"select count(*) - count(distinct (inv_date_sk, inv_item_sk, inv_warehouse_sk)), count(*) from {inv}")
    # -- navigation
    wc = "web_clickstreams"
    add(wc, "Clics anonymes (wcs_user_sk vide)", "observation",
        f"select count(*) filter (where nullif(wcs_user_sk,'') is null), count(*) from {wc}",
        "Un visiteur non identifié ne peut pas être relié à un client.")
    add(wc, "Clics sans commande associée (wcs_sales_sk vide)", "observation",
        f"select count(*) filter (where nullif(wcs_sales_sk,'') is null), count(*) from {wc}",
        "Un clic n'est pas un achat : seule une minorité aboutit à une vente.")
    add(wc, "Lignes entièrement dupliquées", "anomalie",
        f"select count(*) - count(distinct (wcs_click_date_sk, wcs_click_time_sk, wcs_sales_sk, wcs_item_sk, wcs_web_page_sk, wcs_user_sk)), count(*) from {wc}",
        "Pas de clé primaire : un doublon peut être un double clic légitime (À valider).")
    # -- avis
    pr = "product_reviews"
    add(pr, "Note hors de l'intervalle 1 à 5", "anomalie",
        f"select count(*) filter (where {num('pr_review_rating')} is null or {num('pr_review_rating')} not between 1 and 5), count(*) from {pr}")
    add(pr, "Avis sans texte", "anomalie",
        f"select count(*) filter (where nullif(pr_review_content,'') is null), count(*) from {pr}")
    add(pr, "Doublons sur pr_review_sk", "anomalie",
        f"select count(*) - count(distinct pr_review_sk), count(*) from {pr}")
    # -- produits
    it = "item"
    add(it, "Prix courant vide ou <= 0", "anomalie",
        f"select count(*) filter (where {num('i_current_price')} is null or {num('i_current_price')} <= 0), count(*) from {it}")
    add(it, "Prix courant inférieur au coût d'achat", "observation",
        f"select count(*) filter (where {num('i_current_price')} < {num('i_wholesale_cost')}), count(*) from {it}")
    add(it, "Catégorie vide", "anomalie",
        f"select count(*) filter (where nullif(i_category,'') is null), count(*) from {it}")
    add(it, "Lignes en trop par rapport aux produits distincts (i_item_id)", "observation",
        f"select count(*) - count(distinct i_item_id), count(*) from {it}",
        "Historisation de type 2 : un même produit métier peut avoir plusieurs versions (sk).")
    add(it, "Versions de produit encore courantes (i_rec_end_date vide)", "observation",
        f"select count(*) filter (where nullif(i_rec_end_date,'') is null), count(*) from {it}")
    # -- clients
    cu = "customer"
    add(cu, "Année de naissance hors 1900-2010", "anomalie",
        f"select count(*) filter (where {num('c_birth_year')} not between 1900 and 2010), count(*) from {cu}")
    add(cu, "Adresse e-mail vide", "observation",
        f"select count(*) filter (where nullif(c_email_address,'') is null), count(*) from {cu}")
    add(cu, "Doublons sur c_customer_id", "anomalie",
        f"select count(*) - count(distinct c_customer_id), count(*) from {cu}")
    add(cu, "Client sans adresse (c_current_addr_sk vide)", "observation",
        f"select count(*) filter (where nullif(c_current_addr_sk,'') is null), count(*) from {cu}")
    # -- prix concurrents
    mp = "item_marketprices"
    add(mp, "Prix concurrent vide ou <= 0", "anomalie",
        f"select count(*) filter (where {num('imp_competitor_price')} is null or {num('imp_competitor_price')} <= 0), count(*) from {mp}")
    add(mp, "Fin de validité avant début", "anomalie",
        f"select count(*) filter (where {sk('imp_end_date')} < {sk('imp_start_date')}), count(*) from {mp}")
    # -- magasins / dates
    add("store", "Magasins fermés (s_closed_date_sk renseigné)", "observation",
        "select count(*) filter (where nullif(s_closed_date_sk,'') is not null), count(*) from store")
    add("date_dim", "Doublons sur d_date", "anomalie",
        "select count(*) - count(distinct d_date), count(*) from date_dim")

    out = []
    for (table, titre, nature, sql, interp) in C:
        try:
            a, t = con.execute(sql).fetchone()
            out.append({"table": table, "controle": titre, "nature": nature, "nb_concernes": a,
                        "nb_total": t, "pct": round(100 * a / t, 4) if t else 0,
                        "interpretation": interp, "erreur": ""})
        except Exception as e:  # noqa: BLE001 - on garde la preuve de l'échec
            out.append({"table": table, "controle": titre, "nature": nature, "nb_concernes": "",
                        "nb_total": "", "pct": "", "interpretation": interp, "erreur": str(e)[:200]})
            log(f"  contrôle en erreur: {titre}: {e}")
    return out


# --------------------------------------------------------------------------- périodes & refresh
def coverage(con) -> list[dict]:
    """Période couverte par chaque table de faits (jointure avec date_dim)."""
    specs = [("store_sales", "ss_sold_date_sk"), ("web_sales", "ws_sold_date_sk"),
             ("store_returns", "sr_returned_date_sk"), ("web_returns", "wr_returned_date_sk"),
             ("inventory", "inv_date_sk"), ("web_clickstreams", "wcs_click_date_sk"),
             ("product_reviews", "pr_review_date")]
    out = []
    for table, col in specs:
        for source in SOURCES:
            name = tname(table, source)
            if name not in TABLES_PRESENTES:
                continue
            if col == "pr_review_date":
                q = f"select min({col}), max({col}), count(distinct {col}) from {name}"
            else:
                q = (f"select min(d.d_date), max(d.d_date), count(distinct d.d_date) from {name} f "
                     f"join date_dim d on d.d_date_sk = {sk('f.' + col)}")
            dmin, dmax, ndist = con.execute(q).fetchone()
            out.append({"source": source, "table": table, "colonne_date": col,
                        "date_min": str(dmin), "date_max": str(dmax), "jours_distincts": ndist})
    return out


def refresh_comparison(con) -> list[dict]:
    out = []
    for table in SCHEMAS:
        r, i = tname(table, "data_refresh"), table
        if r not in TABLES_PRESENTES or i not in TABLES_PRESENTES:
            continue
        pk = CLES_PRIMAIRES.get(table)
        row = {"table": table,
               "lignes_data": con.execute(f"select count(*) from {i}").fetchone()[0],
               "lignes_refresh": con.execute(f"select count(*) from {r}").fetchone()[0]}
        if pk:
            key = ", ".join(pk)
            tup = f"({key})" if len(pk) > 1 else key
            row["cle"] = " + ".join(pk)
            row["cles_refresh_deja_presentes_dans_data"] = con.execute(
                f"select count(*) from {r} where {tup} in (select {tup} from {i})").fetchone()[0]
            if len(pk) == 1:
                row["min_cle_data"], row["max_cle_data"] = con.execute(
                    f"select min({sk(pk[0])}), max({sk(pk[0])}) from {i}").fetchone()
                row["min_cle_refresh"], row["max_cle_refresh"] = con.execute(
                    f"select min({sk(pk[0])}), max({sk(pk[0])}) from {r}").fetchone()
        out.append(row)
    return out


# --------------------------------------------------------------------------- KPI de test
def kpi_tests(con) -> tuple[list[dict], list[dict]]:
    K = []

    def add(kpi, canal, formule, sql, unite):
        try:
            v = con.execute(sql).fetchone()[0]
            err = ""
        except Exception as e:  # noqa: BLE001
            v, err = None, str(e)[:200]
        K.append({"kpi": kpi, "canal": canal, "formule": formule, "valeur": v, "unite": unite,
                  "erreur": err})

    add("Chiffre d'affaires", "Magasin", "SUM(ss_net_paid)",
        f"select round(sum({num('ss_net_paid')}), 2) from store_sales", "devise non précisée")
    add("Chiffre d'affaires", "Web", "SUM(ws_net_paid)",
        f"select round(sum({num('ws_net_paid')}), 2) from web_sales", "devise non précisée")
    add("Nombre de transactions", "Magasin", "COUNT(DISTINCT ss_ticket_number)",
        "select count(distinct ss_ticket_number) from store_sales", "tickets")
    add("Nombre de transactions", "Web", "COUNT(DISTINCT ws_order_number)",
        "select count(distinct ws_order_number) from web_sales", "commandes")
    add("Panier moyen", "Magasin", "SUM(ss_net_paid) / COUNT(DISTINCT ss_ticket_number)",
        f"select round(sum({num('ss_net_paid')}) / count(distinct ss_ticket_number), 2) from store_sales",
        "devise / ticket")
    add("Panier moyen", "Web", "SUM(ws_net_paid) / COUNT(DISTINCT ws_order_number)",
        f"select round(sum({num('ws_net_paid')}) / count(distinct ws_order_number), 2) from web_sales",
        "devise / commande")
    add("Quantités vendues", "Magasin", "SUM(ss_quantity)",
        f"select sum({num('ss_quantity')}) from store_sales", "unités")
    add("Quantités vendues", "Web", "SUM(ws_quantity)",
        f"select sum({num('ws_quantity')}) from web_sales", "unités")
    add("Taux de remise", "Magasin", "SUM(ss_ext_discount_amt) / SUM(ss_ext_list_price)",
        f"select round(100 * sum({num('ss_ext_discount_amt')}) / sum({num('ss_ext_list_price')}), 2) from store_sales", "%")
    add("Taux de remise", "Web", "SUM(ws_ext_discount_amt) / SUM(ws_ext_list_price)",
        f"select round(100 * sum({num('ws_ext_discount_amt')}) / sum({num('ws_ext_list_price')}), 2) from web_sales", "%")
    add("Marge nette", "Magasin", "SUM(ss_net_profit)",
        f"select round(sum({num('ss_net_profit')}), 2) from store_sales", "devise non précisée")
    add("Marge nette", "Web", "SUM(ws_net_profit)",
        f"select round(sum({num('ws_net_profit')}), 2) from web_sales", "devise non précisée")
    add("Taux de retour en quantité", "Magasin", "SUM(sr_return_quantity) / SUM(ss_quantity)",
        f"select round(100 * (select sum({num('sr_return_quantity')}) from store_returns) / "
        f"(select sum({num('ss_quantity')}) from store_sales), 2)", "%")
    add("Taux de retour en quantité", "Web", "SUM(wr_return_quantity) / SUM(ws_quantity)",
        f"select round(100 * (select sum({num('wr_return_quantity')}) from web_returns) / "
        f"(select sum({num('ws_quantity')}) from web_sales), 2)", "%")
    add("Montant retourné", "Magasin", "SUM(sr_return_amt)",
        f"select round(sum({num('sr_return_amt')}), 2) from store_returns", "devise non précisée")
    add("Montant retourné", "Web", "SUM(wr_return_amt)",
        f"select round(sum({num('wr_return_amt')}), 2) from web_returns", "devise non précisée")
    add("Stock moyen par relevé", "Entrepôts", "AVG(inv_quantity_on_hand)",
        f"select round(avg({num('inv_quantity_on_hand')}), 2) from inventory", "unités")
    add("Part des clics aboutissant à une commande", "Web", "COUNT(wcs_sales_sk) / COUNT(*)",
        "select round(100 * count(nullif(wcs_sales_sk,'')) / count(*), 3) from web_clickstreams", "%")
    add("Note moyenne des avis", "Web", "AVG(pr_review_rating)",
        f"select round(avg({num('pr_review_rating')}), 3) from product_reviews", "note sur 5")
    add("Nombre de produits distincts vendus", "Magasin", "COUNT(DISTINCT ss_item_sk)",
        "select count(distinct ss_item_sk) from store_sales", "produits")

    series = []
    for canal, tbl, dcol, mcol in (("Magasin", "store_sales", "ss_sold_date_sk", "ss_net_paid"),
                                   ("Web", "web_sales", "ws_sold_date_sk", "ws_net_paid")):
        rows = con.execute(
            f"select d.d_year, round(sum({num('f.' + mcol)}), 2), count(*) from {tbl} f "
            f"join date_dim d on d.d_date_sk = {sk('f.' + dcol)} group by 1 order by 1").fetchall()
        for y, ca, n in rows:
            series.append({"canal": canal, "annee": y, "chiffre_affaires": ca, "lignes": n})
    return K, series


# --------------------------------------------------------------------------- fichiers de preuve
def write_apercu(con, out: Path, files: list[dict]) -> None:
    lines = ["APERCU DES DONNEES : 3 premières lignes par table (champs tronqués à 40 caractères)",
             f"Généré le {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    for source in SOURCES:
        for table in SCHEMAS:
            name = tname(table, source)
            if name not in TABLES_PRESENTES:
                continue
            lines.append(f"=== {source}/{table}  ({SCHEMAS[table][0]})")
            cols = SCHEMAS[table][1]
            for r in con.execute(f"select * from {name} limit 3").fetchall():
                lines.append("  " + " | ".join(f"{c}={('' if v is None else str(v))[:40]}"
                                                 for c, v in zip(cols, r)))
            lines.append("")
    (out / "apercu_donnees.txt").write_text("\n".join(lines), encoding="utf-8")


def write_tree(data_root: Path, out: Path, files: list[dict]) -> None:
    lines = [f"ARBORESCENCE de {data_root.name}/ (hors .DS_Store)", ""]
    total = 0
    for source in SOURCES:
        sub = [f for f in files if f["source"] == source]
        lines.append(f"{source}/  ({len(sub)} fichiers, {human(sum(f['taille_octets'] for f in sub))})")
        for f in sub:
            lines.append(f"  {f['table']}/{Path(f['rel']).name:<42} {human(f['taille_octets']):>10}")
            total += f["taille_octets"]
    lines += ["", f"TOTAL : {len(files)} fichiers, {human(total)} ({total} octets)"]
    (out / "arborescence.txt").write_text("\n".join(lines), encoding="utf-8")


def write_csv_audit(files: list[dict], out: Path) -> None:
    lines = []
    for f in files:
        if f["format"] == "csv":
            raw = f["path"].read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
            rows = raw.split("\n")
            lines.append(f"=== {f['rel']} ({human(f['taille_octets'])}, {len(rows)} lignes brutes)")
            lines += rows[:12]
            if len(rows) > 12:
                lines.append(f"... ({len(rows) - 12} lignes supplémentaires)")
            lines.append("")
    (out / "audit_item_marketprices.txt").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- main
TABLES_PRESENTES: set[str] = set()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="dossier contenant data/ et data_refresh/")
    ap.add_argument("--out", required=True, help="dossier de sortie des preuves")
    ap.add_argument("--db", default="build/tpcxbb.duckdb", help="base DuckDB intermédiaire (non versionnée)")
    ap.add_argument("--only", choices=["inventaire", "colonnes", "relations", "qualite", "kpi", "tout"],
                    default="tout", help="limiter les étapes exécutées")
    args = ap.parse_args()

    data_root, out = Path(args.data).resolve(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    con = duckdb.connect(args.db)

    log(f"Découverte des fichiers dans {data_root}")
    files = discover(data_root)
    log(f"{len(files)} fichiers trouvés")
    write_tree(data_root, out, files)

    log("Chargement dans DuckDB (contrôle du nombre de champs par ligne)")
    load_tables(con, files)
    TABLES_PRESENTES.update(r[0] for r in con.execute("select table_name from information_schema.tables").fetchall())

    # --- inventaire
    inv_rows = []
    for f in files:
        sch = SCHEMAS.get(f["table"])
        inv_rows.append({
            "source": f["source"], "table": f["table"], "domaine": sch[0] if sch and f["format"] == "dat" else "",
            "fichier": Path(f["rel"]).name, "chemin_relatif": f["rel"], "format": f["format"],
            "delimiteur": "|" if f["format"] == "dat" else ",",
            "taille_octets": f["taille_octets"], "taille": human(f["taille_octets"]),
            "lignes": f.get("lignes", ""), "colonnes_observees": (
                f"{f['champs_min']}" if f.get("champs_min") == f.get("champs_max") else
                f"{f.get('champs_min', '')}-{f.get('champs_max', '')}") if "champs_min" in f else "",
            "colonnes_attendues_deduites": f.get("colonnes_attendues", ""),
            "schema_coherent": ("oui" if f.get("correspond") else "NON") if "correspond" in f else "",
            "en_tete_present": "non" if f["format"] == "dat" else "oui (1 ligne d'en-tête)",
        })
    write_csv(out / "inventaire_fichiers.csv", inv_rows, list(inv_rows[0].keys()))
    write_csv_audit(files, out)
    log(f"inventaire écrit ({len(inv_rows)} lignes)")

    result = {"genere_le": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "duckdb": duckdb.__version__,
              "python": platform.python_version(), "systeme": platform.platform(),
              "data_root": str(data_root), "fichiers": inv_rows}

    if args.only in ("colonnes", "tout"):
        log("Profil des colonnes")
        prof = []
        for source in SOURCES:
            for table in SCHEMAS:
                if tname(table, source) in TABLES_PRESENTES:
                    prof += profile_columns(con, table, source)
                    log(f"  {source}/{table}")
        write_csv(out / "profil_colonnes.csv", prof, list(prof[0].keys()))
        result["colonnes"] = prof
        write_apercu(con, out, files)

    if args.only in ("relations", "tout"):
        log("Contrôle des relations candidates")
        rel = check_relations(con)
        write_csv(out / "controles_relations.csv", rel, list(rel[0].keys()))
        result["relations"] = rel
        log(f"  {len(rel)} relations contrôlées")

    if args.only in ("qualite", "tout"):
        log("Contrôles de qualité")
        q = quality_checks(con)
        write_csv(out / "controles_qualite.csv", q, list(q[0].keys()))
        result["qualite"] = q
        cov = coverage(con)
        write_csv(out / "couverture_temporelle.csv", cov, list(cov[0].keys()))
        result["couverture"] = cov
        comp = refresh_comparison(con)
        fields = sorted({k for r in comp for k in r}, key=lambda k: (k != "table", k))
        write_csv(out / "comparaison_refresh.csv", comp, fields)
        result["refresh"] = comp

    if args.only in ("kpi", "tout"):
        log("KPI de test")
        k, series = kpi_tests(con)
        write_csv(out / "kpi_tests.csv", k, list(k[0].keys()))
        write_csv(out / "kpi_series_annuelles.csv", series, list(series[0].keys()))
        result["kpi"], result["kpi_series"] = k, series

    result["duree_execution_s"] = round(time.time() - t0, 1)
    (out / "profil.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str),
                                     encoding="utf-8")
    log(f"Terminé en {result['duree_execution_s']} s -> {out}")


if __name__ == "__main__":
    main()
