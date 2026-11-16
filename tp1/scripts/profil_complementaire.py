#!/usr/bin/env python3
"""Preuves chiffrées de l'UC-C1 (processus décisionnel sur les retours, question Q05).

Lit build/tpcxbb.duckdb (créée par profiler_tpcx_bb.py) et écrit dans 03_complementaire/preuves/ :
  retours_par_categorie.csv  retours_par_motif.csv  retours_synthese.json  controles_retours.csv

Périmètre : data + data_refresh (même numérotation, clés disjointes, voir UC-01).
Un taux de retour = quantité retournée / quantité vendue, par catégorie de produit.
Usage : python scripts/profil_complementaire.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT.parent / "build" / "tpcxbb.duckdb"
OUT = ROOT / "03_complementaire" / "preuves"

con = duckdb.connect(str(DB), read_only=True)
q = lambda s: con.execute(s).fetchall()  # noqa: E731

# vues : tables data + refresh, colonnes typées
con.execute("""
create temp view item_all as
  select try_cast(i_item_sk as bigint) sk, coalesce(nullif(i_category,''),'(vide)') categorie from item
  union all select try_cast(i_item_sk as bigint), coalesce(nullif(i_category,''),'(vide)') from item__refresh;
create temp view ventes as
  select 'magasin' canal, try_cast(ss_item_sk as bigint) item, try_cast(ss_quantity as bigint) qte from store_sales
  union all select 'magasin', try_cast(ss_item_sk as bigint), try_cast(ss_quantity as bigint) from store_sales__refresh
  union all select 'web', try_cast(ws_item_sk as bigint), try_cast(ws_quantity as bigint) from web_sales
  union all select 'web', try_cast(ws_item_sk as bigint), try_cast(ws_quantity as bigint) from web_sales__refresh;
create temp view retours as
  select 'magasin' canal, try_cast(sr_item_sk as bigint) item, try_cast(sr_return_quantity as bigint) qte,
         try_cast(sr_reason_sk as bigint) motif from store_returns
  union all select 'magasin', try_cast(sr_item_sk as bigint), try_cast(sr_return_quantity as bigint),
         try_cast(sr_reason_sk as bigint) from store_returns__refresh
  union all select 'web', try_cast(wr_item_sk as bigint), try_cast(wr_return_quantity as bigint),
         try_cast(wr_reason_sk as bigint) from web_returns
  union all select 'web', try_cast(wr_item_sk as bigint), try_cast(wr_return_quantity as bigint),
         try_cast(wr_reason_sk as bigint) from web_returns__refresh;
""")

# 1. taux de retour par catégorie et canal
rows = q("""
with v as (select i.categorie, x.canal, sum(x.qte) qv from ventes x left join item_all i on i.sk=x.item group by 1,2),
     r as (select i.categorie, x.canal, sum(x.qte) qr, count(*) nr from retours x left join item_all i on i.sk=x.item group by 1,2)
select v.canal, v.categorie, v.qv, coalesce(r.qr,0), coalesce(r.nr,0),
       round(100.0*coalesce(r.qr,0)/v.qv, 2)
from v left join r using (categorie, canal) order by v.canal, 6 desc""")
with open(OUT / "retours_par_categorie.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["canal", "categorie", "qte_vendue", "qte_retournee", "lignes_retour", "taux_retour_pct"])
    w.writerows(rows)

# 2. répartition par motif
mot = q("""
select r.r_reason_sk, r.r_reason_desc, count(x.item) n
from (select try_cast(r_reason_sk as bigint) r_reason_sk, r_reason_desc from reason) r
left join retours x on x.motif=r.r_reason_sk group by 1,2 order by 3 desc""")
total_mot = sum(m[2] for m in mot)
with open(OUT / "retours_par_motif.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["motif_sk", "libelle_motif", "lignes_retour", "part_pct"])
    for sk, d, n in mot:
        w.writerow([sk, d, n, round(100.0 * n / total_mot, 2)])

# 3. contrôles de qualité utiles à la décision
ctrl = []
def c(nom, valeur, total, note):
    ctrl.append([nom, valeur, total, round(100.0 * valeur / total, 3) if total else "", note])
tot_ret = q("select count(*) from retours")[0][0]
c("retours sans motif", q("select count(*) from retours where motif is null")[0][0], tot_ret, "motif absent")
c("retours dont le motif n'existe pas dans reason",
  q("select count(*) from retours x where motif is not null and motif not in (select try_cast(r_reason_sk as bigint) from reason)")[0][0],
  tot_ret, "orphelins vers reason")
c("retours dont le produit est absent du référentiel item",
  q("select count(*) from retours x where item not in (select sk from item_all)")[0][0], tot_ret, "orphelins vers item")
c("retours sans catégorie renseignée", q("select count(*) from retours x join item_all i on i.sk=x.item where i.categorie='(vide)'")[0][0],
  tot_ret, "catégorie vide")
c("quantité de retour <= 0", q("select count(*) from retours where qte is null or qte<=0")[0][0], tot_ret, "quantité invalide")
with open(OUT / "controles_retours.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["controle", "lignes_concernees", "total_lignes", "pct", "note"])
    w.writerows(ctrl)

# 4. synthèse
glob = q("""
with v as (select canal, sum(qte) qv from ventes group by 1), r as (select canal, sum(qte) qr, count(*) nr from retours group by 1)
select v.canal, v.qv, r.qr, r.nr, round(100.0*r.qr/v.qv,2) from v join r using (canal) order by 1""")
parts = [m[2] / total_mot * 100 for m in mot]
synth = {
    "canaux": [{"canal": g[0], "qte_vendue": g[1], "qte_retournee": g[2], "lignes_retour": g[3], "taux_retour_pct": float(g[4])} for g in glob],
    "nb_motifs": len(mot), "part_motif_min_pct": round(min(parts), 2), "part_motif_max_pct": round(max(parts), 2),
    "ecart_relatif_max_min": round(max(parts) / min(parts), 2),
    "exemple_libelles_motifs": [m[1] for m in mot[:3]],
    "total_lignes_retour": tot_ret,
}
for canal in ("magasin", "web"):
    cats = [r for r in rows if r[0] == canal and r[1] != "(vide)"]
    synth[f"categorie_taux_max_{canal}"] = {"categorie": cats[0][1], "taux_pct": float(cats[0][5])}
    synth[f"categorie_taux_min_{canal}"] = {"categorie": cats[-1][1], "taux_pct": float(cats[-1][5])}
    synth[f"nb_categories_{canal}"] = len(cats)
(OUT / "retours_synthese.json").write_text(json.dumps(synth, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(synth, ensure_ascii=False, indent=1))
print(*ctrl, sep="\n")
