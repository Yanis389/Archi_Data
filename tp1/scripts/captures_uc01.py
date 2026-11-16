"""Contrôles simples affichés à l'écran (destinés aux captures d'écran des preuves UC-01).

Usage (dans le conteneur Ubuntu, données montées dans /data) :
    python3 scripts/captures_uc01.py colonnes   store_sales
    python3 scripts/captures_uc01.py controles  store_sales
    python3 scripts/captures_uc01.py jointures

Les noms de colonnes sont DÉDUITS (voir schemas.py) : les .dat n'ont pas d'en-tête.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schemas import SCHEMAS  # noqa: E402

DATA = Path("/data/data")


def vue(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    cols = SCHEMAS[table][1]
    path = DATA / table / f"{table}.dat"
    spec = ", ".join(f"'{c}': 'VARCHAR'" for c in cols)
    con.execute(
        f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_csv('{path}', delim='|', header=false, "
        f"columns={{{spec}}}, quote='', escape='', null_padding=false)"
    )
    return cols


def colonnes(table: str) -> None:
    con = duckdb.connect()
    cols = vue(con, table)
    total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"Table : {table}   |   lignes : {total:,}".replace(",", " "))
    print(f"{'#':>2}  {'colonne':<26}{'type observé':<14}{'nulls':>8}{'distincts':>11}  exemple")
    for i, c in enumerate(cols, 1):
        n_null, n_dist, ex = con.execute(
            f"SELECT count(*) FILTER (WHERE {c} IS NULL OR {c} = ''), count(DISTINCT {c}), any_value({c}) FROM {table}"
        ).fetchone()
        non_vide = con.execute(f"SELECT count(*) FROM {table} WHERE {c} <> ''").fetchone()[0]
        # regex : TRY_CAST('4.05' AS BIGINT) arrondirait au lieu d'échouer
        num_int = con.execute(f"SELECT count(*) FROM {table} WHERE regexp_matches({c}, '^-?[0-9]+$')").fetchone()[0]
        num_dec = con.execute(f"SELECT count(*) FROM {table} WHERE {c} <> '' AND TRY_CAST({c} AS DOUBLE) IS NOT NULL").fetchone()[0]
        typ = "texte"
        if non_vide and num_int == non_vide:
            typ = "entier"
        elif non_vide and num_dec == non_vide:
            typ = "décimal"
        print(f"{i:>2}  {c:<26}{typ:<14}{n_null:>8}{n_dist:>11}  {str(ex)[:28]}")


def controles(table: str) -> None:
    con = duckdb.connect()
    cols = vue(con, table)
    total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"Contrôles simples sur {table} ({total:,} lignes)".replace(",", " "))
    print("-" * 78)
    if table == "store_sales":
        n = con.execute("SELECT count(*) FROM store_sales WHERE ss_customer_sk = ''").fetchone()[0]
        print(f"Lignes sans client (ss_customer_sk vide)      : {n:>9}  ({100*n/total:6.2f} %)")
        # même définition que le profileur : lignes en trop = lignes - clés (ticket, produit) distinctes
        n = con.execute("SELECT count(*) - count(DISTINCT (ss_ticket_number, ss_item_sk)) FROM store_sales").fetchone()[0]
        print(f"Doublons sur (ticket, produit) [lignes en trop]: {n:>8}  ({100*n/total:6.2f} %)")
        n = con.execute("SELECT count(*) FROM store_sales WHERE TRY_CAST(ss_sales_price AS DOUBLE) < "
                        "TRY_CAST(ss_wholesale_cost AS DOUBLE)").fetchone()[0]
        print(f"Prix de vente < coût d'achat                  : {n:>9}  ({100*n/total:6.2f} %)")
        n = con.execute("SELECT count(*) FROM store_sales WHERE TRY_CAST(ss_net_profit AS DOUBLE) < 0").fetchone()[0]
        print(f"Marge nette négative                          : {n:>9}  ({100*n/total:6.2f} %)")
        d0, d1 = con.execute("SELECT min(TRY_CAST(ss_sold_date_sk AS BIGINT)), max(TRY_CAST(ss_sold_date_sk AS BIGINT)) FROM store_sales").fetchone()
        print(f"Plage de ss_sold_date_sk                      : {d0} -> {d1}")
    nulls = [(c, con.execute(f"SELECT count(*) FROM {table} WHERE {c} IS NULL OR {c} = ''").fetchone()[0]) for c in cols]
    print("\nColonnes avec valeurs vides :")
    for c, n in nulls:
        if n:
            print(f"  {c:<26}{n:>9}  ({100*n/total:6.2f} %)")
    if not any(n for _, n in nulls):
        print("  aucune")


def jointures() -> None:
    con = duckdb.connect()
    for t in ("store_sales", "item", "store", "date_dim", "customer"):
        vue(con, t)
    tests = [
        ("store_sales.ss_item_sk      -> item.i_item_sk", "store_sales", "ss_item_sk", "item", "i_item_sk"),
        ("store_sales.ss_store_sk     -> store.s_store_sk", "store_sales", "ss_store_sk", "store", "s_store_sk"),
        ("store_sales.ss_sold_date_sk -> date_dim.d_date_sk", "store_sales", "ss_sold_date_sk", "date_dim", "d_date_sk"),
        ("store_sales.ss_customer_sk  -> customer.c_customer_sk", "store_sales", "ss_customer_sk", "customer", "c_customer_sk"),
    ]
    print("Vérification des relations (lignes orphelines = sans correspondance dans la table parent)")
    print("-" * 92)
    print(f"{'relation':<56}{'renseignées':>12}{'orphelines':>12}   verdict")
    for lib, e, ce, p, cp in tests:
        ren = con.execute(f"SELECT count(*) FROM {e} WHERE {ce} <> ''").fetchone()[0]
        orph = con.execute(
            f"SELECT count(*) FROM {e} WHERE {ce} <> '' AND {ce} NOT IN (SELECT {cp} FROM {p})").fetchone()[0]
        print(f"{lib:<56}{ren:>12}{orph:>12}   {'relation vérifiée' if orph == 0 else 'à confirmer'}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    {"colonnes": colonnes, "controles": controles, "jointures": jointures}[cmd](*args)
