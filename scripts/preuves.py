"""Accès aux preuves générées par `profiler_tpcx_bb.py` (profil.json).

Tous les chiffres cités dans les livrables passent par ce module : aucune valeur n'est saisie à la main.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREUVES = ROOT / "01_UC01_besoin_exploration" / "preuves"
P = json.loads((PREUVES / "profil.json").read_text(encoding="utf-8"))


def fmt(n, dec: int = 0) -> str:
    """Nombre formaté à la française (espace fine insécable comme séparateur de milliers)."""
    if n is None or n == "":
        return "-"
    n = float(n)
    s = f"{n:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def pct(n, dec: int = 2) -> str:
    return f"{fmt(n, dec)} %"


def mo(n_octets) -> str:
    n = float(n_octets)
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{fmt(n, 0 if unit == 'o' else 1)} {unit}"
        n /= 1024
    return str(n)


def fichiers(source: str | None = None, fmt_: str | None = None) -> list[dict]:
    return [f for f in P["fichiers"] if (source is None or f["source"] == source)
            and (fmt_ is None or f["format"] == fmt_)]


def lignes(table: str, source: str = "data") -> int:
    for f in P["fichiers"]:
        if f["table"] == table and f["source"] == source and f["format"] == "dat":
            return int(f["lignes"])
    raise KeyError((table, source))


def total_octets() -> int:
    return sum(int(f["taille_octets"]) for f in P["fichiers"])


def col(table: str, colonne: str, source: str = "data") -> dict:
    for c in P["colonnes"]:
        if c["table"] == table and c["colonne"] == colonne and c["source"] == source:
            return c
    raise KeyError((table, colonne, source))


def kpi(nom: str, canal: str):
    for k in P["kpi"]:
        if k["kpi"] == nom and k["canal"] == canal:
            v = k["valeur"]
            try:
                return float(v)
            except (TypeError, ValueError):
                return v
    raise KeyError((nom, canal))


def rel(child: str, colonne: str, parent: str, source: str = "data") -> dict:
    for r in P["relations"]:
        if (r["table_enfant"] == child and r["colonne_enfant"] == colonne and r["table_parent"] == parent
                and r["source"] == source):
            return r
    raise KeyError((child, colonne, parent, source))


def qual(table: str, contient: str) -> dict:
    for q in P["qualite"]:
        if q["table"] == table and contient.lower() in q["controle"].lower():
            return q
    raise KeyError((table, contient))


def couverture(table: str, source: str = "data") -> dict:
    for c in P["couverture"]:
        if c["table"] == table and c["source"] == source:
            return c
    raise KeyError((table, source))


def serie(canal: str, perimetre: str, annee: int) -> dict:
    for s in P["kpi_series"]:
        if s["canal"] == canal and s["perimetre"] == perimetre and int(s["annee"]) == annee:
            return s
    raise KeyError((canal, perimetre, annee))


def domaines() -> dict[str, list[str]]:
    """domaine -> tables (ordre du dictionnaire des schémas)."""
    from schemas import SCHEMAS
    out: dict[str, list[str]] = {}
    for t, (d, _) in SCHEMAS.items():
        out.setdefault(d, []).append(t)
    return out


def relations_resume(source: str = "data") -> dict[str, int]:
    rs = [r for r in P["relations"] if r["source"] == source]
    return {"total": len(rs),
            "verifiees": sum(1 for r in rs if r["verdict"] == "relation vérifiée"),
            "partielles": sum(1 for r in rs if r["verdict"].startswith("relation partielle")),
            "sans_valeur": sum(1 for r in rs if r["verdict"].startswith("à confirmer"))}
