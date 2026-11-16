#!/usr/bin/env python3
"""Génère les livrables PDF de l'UC-02 (architecture Data) dans 02_UC02_architecture/ :

  UC02_comparaison_architectures.pdf   UC02_architecture_cible.pdf     UC02_schema_flux.pdf
  UC02_positionnement_composants.pdf   UC02_gouvernance.pdf            UC02_local_vers_azure.pdf

Les sources, volumes et contraintes viennent des preuves de l'UC-01 (profil.json).
Tout est de la CONCEPTION LOGIQUE : rien n'est présenté comme déployé ou testé.
Usage : python scripts/build_uc02.py [comparaison|cible|flux|composants|gouvernance|azure|all]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preuves import (P, ROOT, col, couverture, domaines, fichiers, fmt, kpi, lignes, mo, pct, qual,  # noqa: E402
                     relations_resume, total_octets)
from rapport import (B, Doc, S, check_chrome, svg_arrow, svg_box, svg_wrap)  # noqa: E402
from schemas import SCHEMAS  # noqa: E402

OUT = ROOT / "02_UC02_architecture"
MISSION = ("**Votre mission.** Consultant Data auprès de Retail Intelligence : concevoir et justifier une première "
           "architecture Data à partir des besoins (UC-01) et des données réellement observées. Ce document traite "
           "**UC-02** ; il s'agit d'une **conception logique**, rien n'est présenté comme déployé.")

# ----------------------------------------------------------------------------- groupes de tables (observés en UC-01)
REFERENTIELS = ["customer", "customer_address", "customer_demographics", "household_demographics", "income_band",
                "date_dim", "time_dim", "item", "promotion", "reason", "ship_mode", "store", "warehouse", "web_page",
                "web_site"]
FAITS = ["store_sales", "web_sales", "store_returns", "web_returns", "inventory"]
COMPORTEMENT = ["web_clickstreams", "product_reviews", "item_marketprices"]
assert set(REFERENTIELS + FAITS + COMPORTEMENT) == set(SCHEMAS), "tous les tables observées doivent être classées"


def groupe(tables: list[str], source: str = "data") -> tuple[int, int, int]:
    """(nb tables, lignes, octets) d'un groupe dans une source."""
    fs = [f for f in P["fichiers"] if f["table"] in tables and f["source"] == source and f["format"] == "dat"]
    return len(fs), sum(int(f["lignes"]) for f in fs), sum(int(f["taille_octets"]) for f in fs)


G = {nom: groupe(t) for nom, t in (("ref", REFERENTIELS), ("faits", FAITS), ("comp", COMPORTEMENT))}
NB_REFRESH = len([f for f in P["fichiers"] if f["source"] == "data_refresh" and f["format"] == "dat"])


# ----------------------------------------------------------------------------- briques SVG
def box(x, y, w, h, t, st="x", size=9, bold=False, sub=""):
    return svg_box(x, y, w, h, t.replace("`", ""), st, size=size, bold=bold, sub=sub.replace("`", ""))


def arrow(x1, y1, x2, y2, **k):
    return svg_arrow(x1, y1, x2, y2, **k)


def titre_col(x, w, t):
    return (f'<text x="{x + w / 2}" y="16" text-anchor="middle" font-size="10" font-weight="700" '
            f'fill="#1b3a57">{t}</text>')


def svg_architecture() -> str:
    """Architecture logique cible (sources -> ingestion -> zones -> exposition + gouvernance)."""
    W, H = 800, 520
    s = []
    # titres
    for x, w, t in ((10, 160, "1. Sources"), (200, 140, "2. Ingestion"), (370, 215, "3-5. Stockage et préparation"),
                    (620, 170, "6. Exposition")):
        s.append(titre_col(x, w, t))
    # sources
    s.append(box(10, 36, 160, 62, "TPCx-BB `data/`", "v", 9, True,
                 f"{G['ref'][0] + G['faits'][0] + G['comp'][0]} tables .dat, {mo(sum(g[2] for g in G.values()))}"))
    s.append(box(10, 110, 160, 56, "TPCx-BB `data_refresh/`", "v", 9, True,
                 f"{NB_REFRESH} tables .dat, complément incrémental"))
    s.append(box(10, 178, 160, 44, "Fichiers d'audit .csv", "v", 9, False, "item_marketprices_audit"))
    s.append(box(10, 234, 160, 62, "Sources complémentaires", "h", 9, True, "à identifier séparément (sessions web, devise...)"))
    # ingestion
    s.append(box(200, 36, 140, 190, "Apache NiFi", "t", 10, True,
                 "ListFile / GetFile, contrôle du nombre de champs, empreinte du fichier, PutHDFS, planification batch"))
    s.append(box(200, 240, 140, 56, "Quarantaine", "n", 9, True, "fichiers rejetés + motif"))
    for y in (67, 138, 200):
        s.append(arrow(170, y, 200, y + (30 if y == 67 else 0), curve=False))
    s.append(arrow(170, 265, 200, 190, dash="4 3", curve=False))
    s.append(arrow(270, 226, 270, 240, curve=False, dash="4 3"))
    # zones
    zx, zw = 370, 215
    s.append(box(zx, 36, zw, 78, "BRONZE / Raw  (HDFS)", "p", 10, True,
                 "Fichiers .dat tels que reçus, partitionnés par source et date d'ingestion, avec manifeste de provenance"))
    s.append(box(zx + 30, 124, zw - 60, 34, "Spark : typage, nettoyage, contrôles", "x", 8.5))
    s.append(box(zx, 168, zw, 78, "SILVER  (HDFS, Parquet)", "d", 10, True,
                 "Tables typées et nommées, doublons traités, relations contrôlées, lignes rejetées isolées"))
    s.append(box(zx + 30, 256, zw - 60, 34, "Spark : jointures, agrégats, modèle", "x", 8.5))
    s.append(box(zx, 300, zw, 78, "GOLD  (HDFS, Parquet)", "v", 10, True,
                 "Modèle en étoile : faits partitionnés par date, dimensions conformes, KPI du dictionnaire"))
    s.append(arrow(340, 80, 370, 75, curve=False))
    for ya, yb in ((114, 124), (158, 168), (246, 256), (290, 300)):
        s.append(arrow(zx + zw / 2, ya, zx + zw / 2, yb, curve=False))
    s.append(f'<text x="{zx + zw / 2 + 8}" y="136" font-size="8" fill="#5b6770"></text>')
    # exposition
    s.append(box(620, 36, 170, 58, "Spark SQL / requêtes", "t", 9, True, "KPI et analyses ad hoc"))
    s.append(box(620, 106, 170, 58, "Tableaux de bord KPI", "t", 9, True, "CA, panier, retours, stocks"))
    s.append(box(620, 176, 170, 58, "Notebooks Python", "t", 9, True, "exploration et data science"))
    s.append(box(620, 246, 170, 58, "Équipe Data", "t", 9, True, "qualité et pilotage de la plateforme"))
    s.append(arrow(zx + zw, 339, 620, 65, dash="", curve=True))
    s.append(arrow(zx + zw, 339, 620, 135, curve=True))
    s.append(arrow(zx + zw, 207, 620, 205, curve=True, dash="4 3"))
    s.append(arrow(zx + zw, 207, 620, 275, curve=True, dash="4 3"))
    # gouvernance transversale
    s.append(box(10, 410, 780, 100, "7. SUPERVISION ET GOUVERNANCE (transversales)", "b", 10, True,
                 "Traçabilité de la provenance et lignage - catalogue et documentation des tables - contrôles qualité par zone - "
                 "gestion des accès par zone - protection des données personnelles - journaux des traitements - maîtrise des coûts et volumes"))
    s.append('<line x1="10" y1="396" x2="790" y2="396" stroke="#c9d3da" stroke-dasharray="3 3"/>')
    return svg_wrap(W, H, "".join(s))


def svg_etoile() -> str:
    """Modèle Gold en étoile : 7 faits, 9 dimensions."""
    W, H = 800, 470
    s = []
    faits = [("fait_vente_magasin", ["date", "heure", "produit", "promo", "client", "magasin"]),
             ("fait_vente_web", ["date", "heure", "produit", "promo", "client", "site", "entrepot"]),
             ("fait_retour", ["date", "produit", "client", "motif", "magasin", "site"]),
             ("fait_stock", ["date", "produit", "entrepot"]),
             ("fait_clic_web", ["date", "heure", "produit", "site", "client"]),
             ("fait_avis_produit", ["date", "produit", "client"]),
             ("fait_prix_concurrent", ["produit", "date"])]
    left = [("date", "dim_date"), ("heure", "dim_heure"), ("produit", "dim_produit"), ("promo", "dim_promotion"),
            ("motif", "dim_motif_retour")]
    right = [("client", "dim_client"), ("magasin", "dim_magasin"), ("site", "dim_site_web"), ("entrepot", "dim_entrepot")]
    s.append(titre_col(10, 150, "Dimensions conformes"))
    s.append(titre_col(330, 150, "Faits"))
    s.append(titre_col(640, 150, "Dimensions conformes"))
    lx, rx, fx, fw, dw = 10, 640, 310, 180, 150
    pos = {}
    for i, (k, nm) in enumerate(left):
        y = 40 + i * 76
        pos[k] = (lx + dw, y + 24)
        s.append(box(lx, y, dw, 48, nm, "d", 9, True))
    for i, (k, nm) in enumerate(right):
        y = 62 + i * 92
        pos[k] = (rx, y + 24)
        s.append(box(rx, y, dw, 48, nm, "d", 9, True))
    fpos = {}
    for i, (nm, _) in enumerate(faits):
        y = 34 + i * 60
        fpos[nm] = y + 22
        s.append(box(fx, y, fw, 44, nm, "v", 9, True))
    edges = []
    for nm, dims in faits:
        for d in dims:
            xd, yd = pos[d]
            if d in dict(left):
                edges.append(arrow(xd, yd, fx, fpos[nm], curve=True))
            else:
                edges.append(arrow(fx + fw, fpos[nm], xd + 5, yd, curve=True))
    return svg_wrap(W, H, "".join(edges).replace('stroke="#5b6770"', 'stroke="#aab4bb"') + "".join(s))


def svg_flux() -> str:
    """Flux principaux : 4 voies (référentiels, faits, comportement, refresh) de la source au consommateur."""
    W = 800
    etapes = ["Source", "Ingestion", "Bronze", "Contrôles", "Silver", "Transformation", "Gold", "Consommateur"]
    lanes = [
        ("Référentiels", "15 tables .dat", "NiFi : lecture + empreinte", "tels que reçus", "nb de champs, clé unique",
         "typage, noms", "dimensions conformes", "dim_*", "BI, Équipe Data"),
        ("Faits transactionnels", "5 tables .dat", "NiFi : lecture + empreinte", "tels que reçus", "nb de champs, doublons, orphelins",
         "typage, dédoublonnage", "faits par date", "fait_vente_*, retour, stock", "KPI, Contrôle de gestion"),
        ("Navigation et avis", "3 tables .dat", "NiFi : lecture + empreinte", "tels que reçus", "anonymat, notes 1 à 5",
         "typage, marquage clics", "faits agrégés", "fait_clic_web, avis", "E-commerce, Data"),
        ("data_refresh", "11 tables .dat", "NiFi : même flux, source=refresh", "partition refresh", "collisions de clés",
         "append ordonné (réf. d'abord)", "mise à jour des faits", "mêmes tables Gold", "tous"),
    ]
    st = ["h", "t", "p", "x", "d", "x", "v", "t"]
    bw, gap, left, top, lh = 82, 15, 10, 40, 92
    s = []
    for j, e in enumerate(etapes):
        x = left + j * (bw + gap)
        s.append(f'<text x="{x + bw / 2}" y="22" text-anchor="middle" font-size="9.5" font-weight="700" fill="#1b3a57">{e}</text>')
    for i, ln in enumerate(lanes):
        y = top + i * lh
        s.append(f'<text x="{left}" y="{y - 4}" font-size="8.5" font-weight="700" fill="#5b6770">{ln[0]}</text>')
        for j in range(8):
            x = left + j * (bw + gap)
            txt = ln[1 + j]
            s.append(box(x, y + 4, bw, 62, txt, st[j], 8.2, j in (2, 4, 6)))
            if j < 7:
                s.append(arrow(x + bw, y + 35, x + bw + gap, y + 35, curve=False))
    H = top + len(lanes) * lh + 12
    return svg_wrap(W, H, "".join(s))


# ----------------------------------------------------------------------------- 1. comparaison
def build_comparaison() -> None:
    d = Doc("Comparaison Data Warehouse, Data Lake et Lakehouse",
            "Contraintes du projet, trois approches et choix argumenté", "UC-02 - Concevoir et justifier une architecture Data", MISSION)
    tot_lignes = sum(int(f["lignes"]) for f in P["fichiers"] if f["format"] == "dat" and f["source"] == "data")
    dat_data = sorted((f for f in P["fichiers"] if f["format"] == "dat" and f["source"] == "data"),
                      key=lambda f: -int(f["taille_octets"]))
    top3 = dat_data[:3]
    part3 = 100 * sum(int(f["taille_octets"]) for f in top3) / sum(int(f["taille_octets"]) for f in dat_data)
    d.h1("1. Contraintes du projet (étape A)")
    d.p("Les contraintes sont tirées des fichiers **observés** en UC-01, pas de suppositions sur TPCx-BB en général.")
    d.table(["Contrainte", "Constat sur les données", "Conséquence pour l'architecture", "Statut"], [
        ["Formats", "36 fichiers : `.dat` délimité `|` sans en-tête (34) et `.csv` d'audit (2) ; texte libre dans `product_reviews`.",
         "Accepter des fichiers bruts, typer et nommer plus tard ; prévoir un stockage du texte.", S("V")],
        ["Volumes", f"{mo(total_octets())} au total ; {fmt(tot_lignes)} lignes dans `data` ; trois tables ({', '.join('`' + f['table'] + '`' for f in top3)}) pèsent {fmt(part3, 0)} % du volume de `data`.",
         "Stockage colonnaire (Parquet) et partitionnement par date pour les tables volumineuses.", S("V")],
        ["Diversité des domaines", f"{len(SCHEMAS)} tables en {len(domaines())} domaines : ventes, retours, stocks, produits, clients, magasins, navigation, avis, promotions, logistique, dates.",
         "Un modèle commun (dimensions conformes) pour relier les domaines.", S("V")],
        ["Historisation", "`data_refresh` complète `data` ; aucun historique des référentiels (`*_rec_end_date` vides) ; stocks hebdomadaires.",
         "Conserver chaque lot reçu (rejeu possible) ; prévoir un suivi des changements si le besoin apparaît.", S("V") + " " + S("H")],
        ["Qualité", f"{len(P['qualite'])} contrôles : doublons de clé composite, produits manquants dans le référentiel initial, marge non fiable, relation `pr_order_sk` ambiguë.",
         "Zone intermédiaire dédiée aux contrôles ; lignes rejetées isolées, pas supprimées.", S("V")],
        ["Usages analytiques", "KPI de reporting (CA, panier, retours, stocks) + exploration (clics, avis).",
         "Une couche modélisée pour le SQL/BI et une couche intermédiaire pour l'exploration.", S("D")],
        ["Sécurité et accès", "Colonnes personnelles dans `customer` (nom, e-mail, naissance) ; jeu synthétique.",
         "Droits par zone ; colonnes personnelles pseudonymisées ou masquées hors zone restreinte.", S("D")],
        ["Évolution", "Cible Azure (ADLS Gen2) ; HBase et Delta Lake facultatifs.",
         "Organisation des zones indépendante de la technologie, transposable sur ADLS Gen2.", S("V")],
    ], widths=[13, 36, 36, 15])

    d.h1("2. Les trois approches comparées (étape B)")
    A = lambda t: B(t, "v")  # noqa: E731
    d.table(["", "Data Warehouse", "Data Lake organisé en zones", "Data Lakehouse"], [
        ["**Principe**", "Entrepôt centralisé au schéma défini **à l'écriture** (étoile / flocon), alimenté par ETL.",
         "Stockage de fichiers à faible coût, schéma défini **à la lecture** ; zones Raw/Bronze, Silver, Gold ; ELT.",
         "Data Lake + couche de gestion de tables (Delta Lake, Iceberg...) : transactions, schéma imposé, historique de versions."],
        ["**Types de données adaptés**", "Structurées et stables (ventes, stocks, référentiels).",
         "Tous : structurées (`.dat`), semi-structurées (JSON), non structurées (texte des avis).",
         "Tous, avec des **tables** gérées en colonnaire."],
        ["**Avantages**", "SQL rapide ; définitions de KPI cohérentes ; qualité contrôlée avant chargement ; BI mature.",
         "Conserve le brut et la provenance ; faible coût ; absorbe volumes et formats ; permet de rejouer un traitement.",
         "Fiabilité des mises à jour (ACID) ; évolution de schéma contrôlée ; un seul socle pour BI et data science."],
        ["**Limites**", "Mal adapté au texte libre et au brut ; modèle à fixer tôt ; évolutions coûteuses ; le brut peut être perdu.",
         "Sans catalogue, qualité et sécurité : *Data Swamp* ; pas de transactions natives sur fichiers ; mises à jour difficiles.",
         "Complexité et dépendance à une techno de table ; **Delta Lake est facultatif** dans ce parcours ; Parquet seul ne suffit pas."],
        ["**Usages permis**", "Reporting, tableaux de bord, KPI standardisés.", "Ingestion, exploration, préparation, historique brut, data science.",
         "BI et data science sur les mêmes tables ; upserts ; audit par historique."],
        ["**Contraintes de gouvernance**", "Modèle et dictionnaire centralisés ; droits par schéma ; historisation (SCD) à concevoir.",
         "Catalogue, conventions de nommage, contrôles par zone, accès par zone, politique de rétention.",
         "Celles du lake + gestion des versions de tables (compactage, rétention, vacuum)."],
        ["**Pertinence pour Retail Intelligence**", "Excellente pour les KPI, **insuffisante seule** : ne conserve pas le brut, ne gère pas le texte, fige le modèle avant que la qualité soit connue.",
         "**Très pertinente** : fichiers `.dat` bruts, refresh incrémental, reprise après erreur, outils imposés (HDFS, NiFi, Spark).",
         "Pertinente comme **évolution** (dédoublonnage et upserts du refresh) mais non nécessaire pour valider le Jour 1."],
    ], widths=[12, 29, 30, 29])

    d.h1("3. Adéquation aux contraintes")
    d.p("Évaluation qualitative (adapté / partiel / peu adapté) plutôt qu'un score chiffré : les pondérations seraient "
        "arbitraires. " + S("H") + " Les appréciations sont à discuter.")
    ad, pa, pe = B("Adapté", "v"), B("Partiel", "h"), B("Peu adapté", "n")
    d.table(["Critère (issu de l'UC-01)", "Data Warehouse", "Data Lake zoné", "Lakehouse"], [
        ["Conservation du brut et de la provenance", pe, ad, ad],
        ["Hétérogénéité des formats (`.dat`, texte, clics)", pe, ad, ad],
        ["Cohérence et performance des KPI en SQL", ad, pa + " (via Gold)", ad],
        ["Rejeu du refresh incrémental", pa, ad, ad],
        ["Contrôle de qualité avant exposition", ad, pa + " (zone Silver)", ad],
        ["Conformité au référentiel du parcours (HDFS, NiFi, Spark)", pe, ad, pa + " (Delta facultatif)"],
        ["Coût et complexité d'exploitation", pa, ad, pa],
        ["Transposition vers ADLS Gen2", pa, ad, ad],
    ], widths=[40, 20, 20, 20])

    d.h1("4. Choix retenu et justification")
    d.box("Décision", "**Data Lake organisé en zones Bronze / Silver / Gold, au format Parquet, dont la zone Gold est "
          "modélisée en étoile pour le SQL et les KPI.** La couche Lakehouse (Delta Lake) est une évolution "
          "**facultative**, non requise au Jour 1.", "ok")
    d.ul([
        "**Pourquoi pas un Data Warehouse seul** : il ne conserve pas le brut et fixerait un modèle alors que le dictionnaire est "
        "déduit et que des doublons de clé restent à arbitrer (limites L02 et L11 de l'UC-01).",
        "**Pourquoi un lake zoné** : fichiers `.dat` bruts à conserver, refresh à rejouer, texte des avis, volumes en hausse, "
        "et les outils du parcours (HDFS, NiFi, Spark) sont ceux d'un lake.",
        "**Pourquoi une zone Gold dimensionnelle** : les KPI (CA, panier, retours, stocks) demandent des définitions stables et du SQL rapide : c'est la force du Warehouse, absorbée dans le lake.",
        "**Pourquoi pas le Lakehouse d'emblée** : Delta Lake est facultatif, ajoute une dépendance, et le besoin d'ACID/upserts n'est pas démontré au Jour 1. "
        "Il deviendra pertinent si le refresh impose des mises à jour fréquentes. " + S("H"),
    ])
    d.box("Limites de ce choix", "Un lake sans gouvernance devient un *Data Swamp* (voir `UC02_gouvernance.pdf`). Le Parquet seul "
          "n'apporte ni transactions, ni garantie de schéma, ni historique : le dédoublonnage et les mises à jour devront être "
          "gérés par les traitements Spark. La performance SQL du lake reste inférieure à celle d'un entrepôt dédié.", "warn")

    d.h1("5. Questions de recul (UC-02)")
    d.table(["Question du sujet", "Réponse argumentée"], [
        ["Pourquoi un Data Lake peut-il compléter un Data Warehouse ?",
         "Le Warehouse sert les KPI modélisés ; le Lake conserve le brut, le texte (avis) et les volumes de clics à coût faible, et alimente le Warehouse (ELT). Ici, la zone Gold joue le rôle d'entrepôt dans le lake."],
        ["Dans quels cas un Lakehouse est-il pertinent ?",
         "Quand on a besoin de mises à jour fiables (upserts du refresh, dédoublonnage), d'évolution de schéma contrôlée et d'un historique de versions, sur un seul socle pour BI et data science."],
        ["Pourquoi conserver les données brutes ?",
         "Pour rejouer un traitement après correction, prouver la provenance, absorber une erreur de nettoyage. Ex. les 4 clés de retours du refresh déjà présentes dans `data` ne peuvent être arbitrées que si le brut est intact."],
        ["Pourquoi organiser les données en zones ?",
         "Chaque zone a un rôle et des garanties croissantes (brut, contrôlé, prêt à l'emploi) : cela limite les erreurs, clarifie les responsabilités et les droits d'accès."],
        ["Quelles garanties ne sont pas apportées par le seul stockage Parquet ?",
         "Transactions ACID, isolation entre lecteurs et écrivains, garantie de schéma à l'écriture, historique de versions, suppression/mise à jour fiable d'une ligne."],
        ["Quels risques si la gouvernance est insuffisante ?",
         "*Data Swamp*, doublons non maîtrisés, accès aux colonnes personnelles de `customer`, KPI contradictoires, coûts de stockage non maîtrisés."],
        ["Quels composants sont indispensables au socle et lesquels relèvent de l'approfondissement ?",
         "Socle : Linux, Python, HDFS, NiFi, Spark/PySpark, Parquet, objectif ADLS Gen2. Approfondissement facultatif : HBase, Delta Lake. À étudier sans déployer : Azure Data Factory, Synapse."],
    ], widths=[32, 68])
    d.save_pdf(OUT / "UC02_comparaison_architectures.pdf")
    print("écrit UC02_comparaison_architectures.pdf")


# ----------------------------------------------------------------------------- 2. architecture cible
def build_cible() -> None:
    d = Doc("Architecture logique cible", "Sources, ingestion, zones Bronze / Silver / Gold, exposition et gouvernance",
            "UC-02 - Concevoir et justifier une architecture Data", MISSION)
    d.h1("1. Vue d'ensemble")
    d.p("L'architecture est un **Data Lake en zones** (Bronze, Silver, Gold) dont la dernière zone est modélisée en étoile. "
        "Elle est décrite de façon **logique** : aucun composant n'est déployé ni testé à ce stade.")
    d.figure(svg_architecture(), "Figure 1 - Architecture logique cible. Les flèches pointillées indiquent des usages secondaires ou des rejets.")
    d.table(["N°", "Couche", "Rôle", "Composant (statut du parcours)"], [
        ["1", "Sources", "Fichiers TPCx-BB `data/` et `data_refresh/` ; sources complémentaires éventuelles identifiées **séparément**.", "Fichiers `.dat` / `.csv`"],
        ["2", "Ingestion", "Lire, valider le format, empreinter (hash), déposer dans le brut ; isoler les rejets.", "Apache NiFi (obligatoire)"],
        ["3", "Stockage brut", "Conserver les données reçues et leur provenance, sans transformation.", "HDFS (obligatoire)"],
        ["4", "Préparation et contrôle", "Typer, nommer, dédoublonner, contrôler les clés et les relations.", "Spark / PySpark (obligatoire), Python"],
        ["5", "Stockage analytique", "Données modélisées pour les indicateurs.", "Parquet sur HDFS (format de référence)"],
        ["6", "Exposition", "Requêtes SQL, tableaux de bord, notebooks.", "Spark SQL, Python"],
        ["7", "Supervision et gouvernance", "Traçabilité, qualité, accès, journaux, coûts.", "Voir `UC02_gouvernance.pdf`"],
    ], widths=[5, 20, 50, 25])

    d.h1("2. Zones Bronze, Silver et Gold")
    d.p("Les termes Raw, Bronze, Silver et Gold sont des **conventions d'organisation** : leur rôle est précisé ici. "
        "Ici, *Raw* et *Bronze* sont confondus (une seule zone brute).")
    d.table(["", "Bronze (brut)", "Silver (contrôlé)", "Gold (prêt à l'analyse)"], [
        ["**Rôle**", "Conserver les données reçues, leur format et leur provenance.", "Nettoyer, harmoniser, contrôler et préparer.", "Données organisées pour les indicateurs et les usages."],
        ["**Contenu**", f"{G['ref'][0] + G['faits'][0] + G['comp'][0]} tables de `data/` + {NB_REFRESH} de `data_refresh/`, `.dat` et `.csv` tels quels.",
         "Mêmes tables typées, avec noms de colonnes explicites, doublons traités, lignes rejetées à part.",
         "7 faits et 9 dimensions conformes (figure 2)."],
        ["**Format**", "Fichier d'origine, inchangé (+ manifeste JSON de provenance).", "Parquet, schéma typé.", "Parquet, partitionné par date pour les faits."],
        ["**Modifications**", "Aucune (écriture seule, jamais de mise à jour).", "Typage, dédoublonnage, jointures de contrôle.", "Jointures, agrégats, mesures du dictionnaire de KPI."],
        ["**Organisation**", "`/datalake/bronze/tpcxbb/<source>/<table>/ingest_date=AAAA-MM-JJ/`",
         "`/datalake/silver/<domaine>/<table>/`", "`/datalake/gold/<table>/annee=AAAA/mois=MM/`"],
        ["**Qualité**", "Nombre de champs par ligne ; empreinte ; fichier non vide.",
         "Unicité des clés ; orphelins ; types ; plages de valeurs ; doublons.", "Réconciliation des totaux avec Silver ; fraîcheur."],
        ["**Accès**", "Équipe Data (écriture NiFi, lecture Spark).", "Équipe Data.", "Analystes et métiers en lecture."],
        ["**Rétention**", "Longue (preuve et rejeu) : tout lot reçu est gardé.", "Reconstruisible depuis Bronze.", "Reconstruisible depuis Silver."],
    ], widths=[11, 29, 30, 30])
    d.box("Principe de reconstruction", "Seule la zone Bronze est irremplaçable. Silver et Gold peuvent être **reconstruites** à "
          "tout moment depuis Bronze : c'est ce qui permet de corriger une règle de nettoyage sans perdre de donnée.", "ok")

    d.h1("3. Zone Gold : modèle en étoile")
    d.figure(svg_etoile(), "Figure 2 - Modèle dimensionnel de la zone Gold (liaisons fait -> dimension).")
    rl = relations_resume("data")
    d.p(f"Les liaisons du schéma s'appuient sur des relations **contrôlées** en UC-01 : {rl['verifiees']} sur {rl['total']} "
        "n'ont aucun orphelin. Les points d'attention qui conditionnent le modèle :")
    d.ul([
        f"{S('V')} **Produits** : `dim_produit` doit être construite à partir de `item` de `data` **et** de `data_refresh` "
        f"({fmt(qual('inventory', 'absents de item')['nb_concernes'])} lignes d'inventaire visent des produits du refresh).",
        f"{S('V')} **Faits de vente** : la clé (ticket ou commande, produit) n'est pas unique ({fmt(qual('store_sales', 'Doublons')['nb_concernes'])} doublons "
        "en magasin) : une clé technique et une règle de dédoublonnage sont nécessaires. " + S("A"),
        f"{S('V')} **Clics** : {pct(qual('web_clickstreams', 'anonymes')['pct'], 1)} sont anonymes ; `dim_client` est optionnelle pour `fait_clic_web`.",
        f"{S('H')} **Retours** : `fait_retour` regroupe retours magasin et web (colonne canal) ; le lien `pr_order_sk` de `fait_avis_produit` n'est pas résolu et ne sera pas relié à une dimension de commande.",
        f"{S('V')} **Marge** : le modèle expose les mesures de coût mais le KPI de marge reste **non fiable** (prix sous le coût d'achat).",
    ])

    d.h1("4. Partitionnement et format")
    rows = []
    for t, part, raison in [
        ("store_sales, web_sales", "année / mois de vente", "Lectures par période ; élagage des partitions"),
        ("store_returns, web_returns", "année / mois de retour", "Retours datés jusqu'en 2007-2008 : partition propre"),
        ("inventory", "année (relevés hebdomadaires)", f"{fmt(lignes('inventory'))} lignes ; relevés par date"),
        ("web_clickstreams", "année / mois du clic", f"{fmt(lignes('web_clickstreams'))} lignes ; table la plus fine"),
        ("Référentiels (15 tables)", "aucun (petites tables)", f"{mo(G['ref'][2])} au total ; `customer_demographics` est la plus lourde"),
        ("product_reviews", "année de l'avis", "Texte conservé en Silver ; note exposée en Gold"),
    ]:
        rows.append([f"`{t}`", part, raison])
    d.table(["Table(s)", "Partition", "Raison"], rows, widths=[30, 28, 42])
    d.p("Le format **Parquet** est retenu pour Silver et Gold (stockage colonnaire, compression, schéma embarqué). La taille "
        "réelle après conversion n'est pas connue : elle n'a pas été mesurée. " + S("H"))

    d.h1("5. Ce que cette architecture ne fait pas")
    d.ul([
        "Elle n'est **ni déployée ni testée** : c'est une conception logique à valider avec le formateur.",
        "Elle ne traite pas de flux continu : aucun besoin identifié au Jour 1 (voir `UC02_schema_flux.pdf`).",
        "Elle n'ajoute pas de source : les données complémentaires (sessions web, devise) sont listées comme besoins non couverts.",
        "Elle ne rend obligatoire aucun composant facultatif (HBase, Delta Lake).",
    ])
    d.save_pdf(OUT / "UC02_architecture_cible.pdf")
    (OUT / "preuves" / "architecture_cible.svg").write_text(svg_architecture(), encoding="utf-8")
    (OUT / "preuves" / "modele_gold_etoile.svg").write_text(svg_etoile(), encoding="utf-8")
    print("écrit UC02_architecture_cible.pdf + 2 svg")


# ----------------------------------------------------------------------------- 3. flux
def build_flux() -> None:
    d = Doc("Schéma des flux de données", "De la source au consommateur : formats, contrôles, transformations",
            "UC-02 - Concevoir et justifier une architecture Data", MISSION)
    d.h1("1. Vue d'ensemble des flux")
    d.p("Quatre voies d'ingestion couvrent les données observées. Chacune traverse les mêmes zones ; seuls les contrôles "
        "et les transformations changent.")
    d.figure(svg_flux(), "Figure 1 - Flux principaux, de la source au consommateur final.")
    d.table(["Voie", "Tables", "Lignes (data)", "Taille (data)"], [
        ["Référentiels", str(G["ref"][0]), fmt(G["ref"][1]), mo(G["ref"][2])],
        ["Faits transactionnels", str(G["faits"][0]), fmt(G["faits"][1]), mo(G["faits"][2])],
        ["Navigation, avis, prix concurrents", str(G["comp"][0]), fmt(G["comp"][1]), mo(G["comp"][2])],
        ["data_refresh (incrémental)", str(NB_REFRESH), fmt(sum(int(f["lignes"]) for f in P["fichiers"] if f["source"] == "data_refresh" and f["format"] == "dat")),
         mo(sum(int(f["taille_octets"]) for f in P["fichiers"] if f["source"] == "data_refresh"))],
    ], num_cols=(1, 2, 3), widths=[40, 15, 22, 23])

    d.h1("2. Description détaillée de chaque flux")
    d.p("Pour chaque flux : source, format d'entrée, ingestion, zone de destination, contrôles, transformations, résultat et consommateur (étape E).")
    flux = [
        ("F1 - Référentiels", "Clients, adresses, démographie, dates, heures, produits, promotions, motifs, modes d'expédition, magasins, entrepôts, pages et sites web (15 tables).",
         "`.dat`, `|`, sans en-tête", "NiFi : ListFile + GetFile, empreinte, PutHDFS", "Bronze `tpcxbb/data/`",
         "Nombre de champs = schéma déduit ; clé primaire unique et non vide ; plages (dates, années).",
         "Typage, noms de colonnes, harmonisation des dates ; jointure de contrôle (0 orphelin attendu).", "Dimensions conformes (`dim_*`).",
         "Analystes, Équipe Data."),
        ("F2 - Faits transactionnels", "Ventes magasin et web, retours, stocks (5 tables).", "`.dat`, `|`", "NiFi (même flux que F1)", "Bronze, puis Silver, puis Gold",
         "Doublons sur la clé composite ; quantité > 0 ; prix de vente <= prix catalogue ; expédition >= commande ; relations vers produits, clients, dates, magasins.",
         "Typage, dédoublonnage (règle **À valider**), ajout de la date calendaire, calcul des mesures du dictionnaire de KPI.",
         "Faits partitionnés par date (`fait_vente_*`, `fait_retour`, `fait_stock`).", "Direction commerciale, Contrôle de gestion, Responsable des stocks."),
        ("F3 - Navigation web", "Clics (`web_clickstreams`).", "`.dat`, `|`", "NiFi", "Bronze, Silver, Gold",
         "Clics anonymes marqués (clé client vide) ; clics sans commande ; lignes totalement dupliquées signalées.",
         "Typage, marquage de l'anonymat, rattachement à la commande si présent ; agrégation journalière par page et produit.",
         "`fait_clic_web` agrégé.", "E-commerce / marketing."),
        ("F4 - Avis produits", "`product_reviews` (texte libre + note).", "`.dat`, `|`, texte long", "NiFi", "Bronze, Silver, Gold",
         "Note entre 1 et 5 ; avis sans texte signalés ; clé d'avis unique.",
         "Typage ; **texte conservé en Silver** (non transformé) ; note et date exposées en Gold.", "`fait_avis_produit`.", "E-commerce, Équipe Data."),
        ("F5 - Prix concurrents", "`item_marketprices` + `item_marketprices_audit.csv`.", "`.dat` + `.csv`", "NiFi", "Bronze, Silver, Gold",
         "Prix > 0 ; fin de validité >= début ; produit existant.", "Typage ; calcul de l'écart vs prix courant (**médiane** privilégiée).", "`fait_prix_concurrent`.", "Direction commerciale."),
        ("F6 - Rafraîchissement", f"`data_refresh/` ({NB_REFRESH} tables).", "`.dat`, `|`", "NiFi (même flux, `source=data_refresh`)", "Bronze, partition `data_refresh`",
         "Collisions de clés avec `data` (4 clés de retours) ; prolongement de la numérotation ; ordre de chargement.",
         "**Référentiels d'abord, faits ensuite** ; ajout en Silver sans écraser `data` ; arbitrage des collisions **À valider**.",
         "Gold complétée (année 2005 complète).", "Tous."),
        ("F7 - Sources complémentaires", "Aucune fournie dans le kit ; éventuelles (sessions web, devise, objectifs).", "Selon la source", "NiFi, flux séparé",
         "Bronze `complementaire/`", "Provenance et nature synthétique documentées.", "Jamais fusionnée silencieusement avec TPCx-BB.", "À définir.", "À définir."),
    ]
    for nom, src, fmt_in, ing, zone, ctr, trf, res, conso in flux:
        d.h2(nom)
        d.table(["Élément", "Description"], [
            ["Source", src], ["Format d'entrée", fmt_in], ["Ingestion", ing], ["Zone de destination", zone],
            ["Contrôles", ctr], ["Transformations", trf], ["Résultat attendu", res], ["Consommateur final", conso],
        ], widths=[22, 78])

    d.h1("3. Batch ou flux continu ?")
    d.table(["Besoin identifié (UC-01)", "Rythme", "Traitement"], [
        ["Ventes, retours, indicateurs commerciaux", "Quotidien ou hebdomadaire", "**Batch**"],
        ["Stocks", "Hebdomadaire (grain des relevés)", "**Batch**"],
        ["Rafraîchissement `data_refresh`", "Lot périodique (rôle à confirmer)", "**Batch**"],
        ["Navigation web", "Analyse quotidienne de conversion", "**Batch** (le temps réel n'est pas justifié au Jour 1)"],
    ], widths=[40, 30, 30])
    d.box("Décision", "Tous les flux sont en **batch**. Aucun besoin du Jour 1 n'exige une latence de quelques secondes ; un "
          "traitement en continu n'a donc pas été conçu. Il serait à étudier si un besoin de détection en temps réel "
          "des comportements web apparaissait. " + S("H"), "ok")
    d.h2("Reprise sur erreur")
    d.ul([
        "Un fichier dont le nombre de champs ne correspond pas est envoyé en **quarantaine** avec le motif ; il n'entre jamais en Bronze.",
        "Un lot Bronze est **immuable** : un traitement Silver ou Gold en échec est simplement relancé depuis Bronze.",
        "Chaque exécution écrit un enregistrement de suivi (lot, table, lignes lues et écrites, rejets, durée).",
    ])
    d.save_pdf(OUT / "UC02_schema_flux.pdf")
    (OUT / "preuves" / "schema_flux.svg").write_text(svg_flux(), encoding="utf-8")
    print("écrit UC02_schema_flux.pdf + svg")


# ----------------------------------------------------------------------------- 4. composants
COMPOSANTS = [
    # composant, statut du référentiel, rôle, dans la cible, justification
    ("Linux / Ubuntu", "Obligatoire", "Environnement de référence local", "Oui", "Socle d'exécution de tous les composants du parcours."),
    ("Python", "Obligatoire", "Exploration, scripts et traitements", "Oui", "Contrôles qualité, scripts de pilotage ; PySpark pour les traitements distribués."),
    ("Hadoop / HDFS", "Obligatoire", "Stockage distribué du parcours local", "Oui", "Héberge Bronze, Silver et Gold en local ; équivalent logique d'ADLS Gen2."),
    ("Apache NiFi", "Obligatoire", "Ingestion et orchestration des flux", "Oui", "Lit les `.dat`, contrôle le format, dépose dans Bronze, gère les rejets."),
    ("Apache Spark / PySpark", "Obligatoire", "Traitements distribués et transformations", "Oui", "Bronze -> Silver -> Gold ; nécessaire pour les tables volumineuses."),
    ("Parquet", "Format de référence", "Stockage analytique colonnaire", "Oui", "Format de Silver et Gold ; ne remplace pas la gestion transactionnelle."),
    ("HBase", "Facultatif", "Approfondissement NoSQL", "Non", "Pas de besoin d'accès clé-valeur à faible latence identifié ; non conditionnel à la validation."),
    ("PDGF", "Selon kit disponible", "Génération des données si le kit le permet", "Non", "Le kit fournit déjà les fichiers ; aucune trace du générateur n'est dans le dossier."),
    ("Delta Lake", "Facultatif", "Approfondissement Lakehouse", "Option", "Évolution possible pour les upserts du refresh ; non conditionnel à la validation."),
    ("ADLS Gen2", "Objectif obligatoire", "Déclinaison cloud de l'architecture", "Cible", "Même organisation de zones sur des conteneurs ; conçu ici, non déployé."),
    ("Azure Data Factory", "Présentation / étude", "Orchestration et intégration cloud", "Étudié", "Équivalent cloud logique de NiFi ; non déployé."),
    ("Azure Synapse", "Présentation / étude", "Services analytiques cloud", "Étudié", "Équivalent cloud logique de Spark SQL ; non déployé."),
]


def build_composants() -> None:
    d = Doc("Positionnement des composants technologiques", "Statut dans le parcours, rôle et place dans l'architecture",
            "UC-02 - Concevoir et justifier une architecture Data", MISSION)
    d.h1("1. Matrice de positionnement")
    d.p("Les statuts proviennent du référentiel du parcours et sont **repris tels quels** : aucun composant facultatif n'est "
        "rendu obligatoire (consigne du sujet).")
    cls = {"Obligatoire": "v", "Format de référence": "v", "Objectif obligatoire": "d", "Facultatif": "h", "Selon kit disponible": "h",
           "Présentation / étude": "d"}
    rows = [[f"**{c}**", B(st, cls[st]), role, dans, justif] for (c, st, role, dans, justif) in COMPOSANTS]
    d.table(["Composant", "Statut (référentiel)", "Rôle dans le parcours", "Dans la cible ?", "Justification"], rows,
            widths=[14, 20, 20, 9, 37])
    d.h1("2. Lecture de la matrice")
    ob = [c for c in COMPOSANTS if c[1] in ("Obligatoire", "Format de référence")]
    fa = [c for c in COMPOSANTS if c[1] in ("Facultatif", "Selon kit disponible")]
    d.ul([
        f"**Socle ({len(ob)} composants)** : " + ", ".join(c[0] for c in ob) + ". Ils composent l'architecture locale de bout en bout.",
        f"**Facultatifs ou conditionnels ({len(fa)})** : " + ", ".join(c[0] for c in fa) + ". Ils sont **hors du chemin critique** : la validation du Jour 1 n'en dépend pas.",
        "**Cloud** : ADLS Gen2 est un objectif obligatoire du parcours ; Azure Data Factory et Synapse sont **présentés** et leur déploiement complet n'est pas exigé.",
    ])
    d.h2("Outil d'exploration utilisé au Jour 1 (hors référentiel)")
    d.box("Transparence", "L'analyse des données de l'UC-01 a été exécutée avec **DuckDB** (lecture SQL directe des `.dat` sur un "
          "poste, sans cluster). C'est un outil de travail personnel, **hors référentiel du parcours** : il n'est pas retenu dans "
          "l'architecture cible. Aucun cluster HDFS/Spark n'a été utilisé à ce stade. Le script est reproductible : `scripts/profiler_tpcx_bb.py`.", "warn")
    d.h1("3. Limites et points à valider")
    d.ul([
        "Aucun de ces composants n'a été **installé ni testé** par ce travail : leur rôle est logique.",
        "Les performances réelles (temps de chargement, taille Parquet, compactage) restent à mesurer. " + S("H"),
        "Le catalogue de métadonnées (documentation des tables, lignage) n'a pas de composant imposé par le référentiel : le choix reste **à valider**. " + S("A"),
        "Le statut exact de PDGF dépend du kit : rien dans le dossier ne l'atteste. " + S("A"),
    ])
    # preuve CSV
    with (OUT / "preuves" / "matrice_composants.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["composant", "statut_referentiel", "role", "dans_la_cible", "justification"])
        w.writerows(COMPOSANTS)
    d.save_pdf(OUT / "UC02_positionnement_composants.pdf")
    print("écrit UC02_positionnement_composants.pdf + matrice_composants.csv")


# ----------------------------------------------------------------------------- 5. gouvernance
def build_gouvernance() -> None:
    d = Doc("Gouvernance minimale", "Traçabilité, qualité, accès, protection, suivi et coûts",
            "UC-02 - Concevoir et justifier une architecture Data", MISSION)
    d.h1("1. Pourquoi une gouvernance dès le Jour 1")
    d.p("Un Data Lake sans catalogue, sans contrôle de qualité et sans règles d'accès devient un *Data Swamp*. Les règles "
        "ci-dessous s'appuient sur des **constats de l'UC-01** plutôt que sur des principes génériques.")
    qd = qual("store_sales", "Doublons")["nb_concernes"]
    d.h1("2. Règles par axe")
    d.table(["Axe", "Règle proposée", "Constat de l'UC-01 qui la motive", "Mise en oeuvre (local)"], [
        ["**Traçabilité de la provenance**", "Chaque fichier déposé en Bronze porte un manifeste : nom d'origine, source (`data` / `data_refresh`), date d'ingestion, taille, nombre de lignes, empreinte.",
         "Version, provenance et date de mise à disposition du kit **non communiquées**.", "NiFi écrit le manifeste ; Spark propage l'identifiant de lot vers Silver et Gold (lignage)."],
        ["**Documentation des fichiers et tables**", "Un dictionnaire par table (colonnes, type, clé, statut Vérifié / Déduit) versionné avec le code.",
         "Aucun dictionnaire ni en-tête ; noms de colonnes **déduits**.", "`schemas.py` -> fiche de table ; catalogue à choisir " + S("A")],
        ["**Contrôles de qualité**", "Contrôles par zone (voir §3), seuils d'alerte, rejet isolé en quarantaine ou table `_rejets`.",
         f"{len(P['qualite'])} contrôles écrits ; doublons de clé ({fmt(qd)} en magasin) ; produits absents du référentiel.", "Jobs PySpark ; résultat écrit à chaque lot."],
        ["**Gestion des accès**", "Droits par zone et par rôle, moindre privilège : écriture Bronze réservée à l'ingestion, Gold en lecture pour les métiers.",
         "7 profils utilisateurs aux besoins différents (UC-01).", "Permissions et ACL HDFS par répertoire ; comptes de service."],
        ["**Protection des données**", "Colonnes personnelles de `customer` (nom, prénom, e-mail, naissance) masquées ou pseudonymisées en Silver/Gold ; accès restreint à Bronze.",
         f"`customer` : {fmt(lignes('customer'))} lignes avec identité ; données **synthétiques** mais à traiter comme sensibles.", "Hachage / suppression des colonnes personnelles dans Gold."],
        ["**Suivi des traitements**", "Chaque exécution journalise lot, table, lignes lues et écrites, rejets, durée, version du code.",
         "Reprise sur erreur nécessaire ; ordre de chargement référentiels -> faits.", "Journaux NiFi et Spark ; table de suivi."],
        ["**Maîtrise des coûts et volumes**", "Surveiller la taille par zone, éviter les petits fichiers, définir une rétention (Bronze long, Silver/Gold reconstruisibles).",
         f"{mo(total_octets())} de sources ; 3 tables concentrent l'essentiel du volume ; refresh périodique à prévoir.", "Rapport de volumes par zone ; compactage."],
    ], widths=[17, 32, 27, 24])

    d.h1("3. Contrôles de qualité par zone")
    d.p("Le catalogue de règles reprend les contrôles réellement exécutés en UC-01 (`controles_qualite.csv`, "
        "`controles_relations.csv`) : ils deviennent des règles de la plateforme.")
    d.table(["Zone", "Règle", "Origine (UC-01)", "Action si échec"], [
        ["Bronze", "Nombre de champs par ligne = schéma attendu", f"{sum(1 for f in P['fichiers'] if f['format'] == 'dat' and f['schema_coherent'] == 'oui')} fichiers sur {sum(1 for f in P['fichiers'] if f['format'] == 'dat')} conformes", "Quarantaine du fichier"],
        ["Bronze", "Fichier non vide, empreinte enregistrée", "Traçabilité (§2)", "Rejet du lot"],
        ["Silver", "Clé primaire unique et non vide (référentiels)", "17 clés simples contrôlées, toutes uniques", "Rejet de la ligne vers `_rejets`"],
        ["Silver", "Doublons sur clé composite des faits", f"{fmt(qd)} doublons (ticket, produit) en magasin", "Règle de dédoublonnage **À valider** ; journaliser"],
        ["Silver", "Relation vers le référentiel (orphelins)", f"{relations_resume('data')['verifiees']} sur {relations_resume('data')['total']} sans orphelin", "Alerte ; le fait reste, clé marquée « inconnue »"],
        ["Silver", "Quantité > 0, prix de vente <= prix catalogue, expédition >= commande", "0 anomalie constatée", "Rejet de la ligne"],
        ["Silver", "Note entre 1 et 5", "0 anomalie constatée", "Rejet de la ligne"],
        ["Gold", "Réconciliation : somme des faits = somme Silver", "Cohérence des KPI", "Blocage de la publication"],
        ["Gold", "Fraîcheur : date max attendue par table", "`data` s'arrête au 2005-12-13 ; le refresh complète", "Alerte"],
    ], widths=[10, 36, 31, 23])

    d.h1("4. Rôles et responsabilités")
    d.table(["Rôle", "Responsabilité"], [
        ["Équipe Data", "Propriétaire des zones Bronze et Silver ; écrit et surveille les contrôles ; tient le catalogue."],
        ["Propriétaire de domaine (par ex. Direction commerciale)", "Valide la définition des KPI de son domaine et arbitre les règles métier (doublons, motifs de retour)."],
        ["Contrôle de gestion", "Valide les mesures financières et la définition de la marge."],
        ["Référent protection des données", "Valide le traitement des colonnes personnelles."],
    ], widths=[35, 65])

    d.h1("5. Risques en cas de gouvernance insuffisante")
    d.table(["Risque", "Exemple dans ce projet", "Parade"], [
        ["Data Swamp", "36 fichiers sans dictionnaire : impossible de les relire dans 6 mois.", "Catalogue et manifestes de lot."],
        ["KPI contradictoires", "Marge calculée négative dans les deux canaux.", "Dictionnaire de KPI validé ; KPI non fiable bloqué."],
        ["Fuite de données personnelles", "`customer` : nom, e-mail, naissance.", "Masquage en Gold ; accès restreint."],
        ["Doublons non maîtrisés", f"{fmt(qd)} doublons de clé en ventes magasin.", "Règle de dédoublonnage validée et journalisée."],
        ["Coûts incontrôlés", "Petits fichiers et conservation illimitée en cloud.", "Rétention, compactage, budgets."],
    ], widths=[22, 44, 34])
    d.save_pdf(OUT / "UC02_gouvernance.pdf")
    print("écrit UC02_gouvernance.pdf")


# ----------------------------------------------------------------------------- 6. local -> Azure
def build_azure() -> None:
    d = Doc("De l'environnement local à la cible Azure", "Deux déclinaisons logiques de la même architecture",
            "UC-02 - Concevoir et justifier une architecture Data", MISSION)
    d.box("Statut de ce document", "**Simulation de conception.** Aucune ressource Azure n'a été créée, aucun coût engagé, rien "
          "n'a été testé. Les éléments Azure décrivent le rôle logique de chaque service d'après la documentation générale "
          "d'Azure : " + S("D") + " Les détails (limites, tarifs, noms exacts) sont à **vérifier** sur l'abonnement réel. " + S("A"), "warn")
    d.h1("1. Même architecture, deux déclinaisons")
    d.p("Les zones Bronze / Silver / Gold et les règles de gouvernance sont **indépendantes de la technologie**. Seule change "
        "l'implémentation de chaque couche.")
    d.table(["Couche logique", "Local (Linux / Ubuntu)", "Cible Azure", "Statut du composant cloud"], [
        ["Stockage des zones", "HDFS", "Azure Data Lake Storage Gen2 (compte de stockage avec espace de noms hiérarchique)", "Objectif obligatoire"],
        ["Ingestion et orchestration", "Apache NiFi", "Azure Data Factory (pipelines, activités de copie)", "Présentation / étude"],
        ["Traitements distribués", "Apache Spark / PySpark", "Spark dans Azure Synapse (ou service Spark équivalent)", "Présentation / étude"],
        ["Requêtes SQL sur Gold", "Spark SQL", "Pool SQL serverless de Synapse sur les fichiers Parquet", "Présentation / étude"],
        ["Format analytique", "Parquet", "Parquet (identique)", "Format de référence"],
        ["Identités et accès", "Utilisateurs Linux, permissions et ACL HDFS", "Microsoft Entra ID, RBAC et ACL", "Inclus dans la cible ADLS Gen2"],
        ["Secrets", "Fichiers de configuration protégés", "Azure Key Vault", "Hors référentiel (à étudier)"],
        ["Supervision", "Journaux NiFi et Spark", "Azure Monitor, journaux des pipelines", "Hors référentiel (à étudier)"],
        ["Coûts", "Matériel et disque du poste ou du serveur", "Stockage + transactions + sortie réseau, facturation à l'usage", "Critère de la cible (étape G)"],
    ], widths=[18, 24, 38, 20])

    d.h1("2. Éléments à identifier pour la cible Azure (étape G)")
    d.table(["Élément", "Proposition", "Statut"], [
        ["**Compte de stockage**", "Un compte ADLS Gen2 par environnement (développement, production), avec espace de noms hiérarchique activé. Nom : `stretailintel<env>` (minuscules et chiffres).", S("D")],
        ["**Conteneurs**", "`bronze`, `silver`, `gold`, plus un conteneur `quarantaine` pour les fichiers rejetés.", S("D")],
        ["**Organisation des données**", "Même arborescence que HDFS : `bronze/tpcxbb/<source>/<table>/ingest_date=.../`, `silver/<domaine>/<table>/`, `gold/<table>/annee=.../mois=.../`.", S("D")],
        ["**Identités**", "Groupes Microsoft Entra ID par rôle (Équipe Data, Analystes, Contrôle de gestion) ; **identités managées** pour Data Factory et Spark, sans mot de passe.", S("D")],
        ["**RBAC et ACL**", "RBAC au niveau compte ou conteneur (rôles de lecture, contributeur, propriétaire sur les données blob) ; ACL de type POSIX sur les répertoires pour le niveau fin (par exemple, masquer les colonnes personnelles par un dossier dédié).", S("D")],
        ["**Sécurité des secrets**", "Aucun secret dans le code ni dans les fichiers : Key Vault, accès par identité managée.", S("D")],
        ["**Coûts et quotas**", "Niveaux d'accès (chaud pour Gold, plus froid pour Bronze ancien), règles de cycle de vie, budgets et alertes, limitation des sorties réseau ; quotas de l'abonnement à vérifier.", S("H") + " " + S("A")],
    ], widths=[20, 66, 14])
    d.h2("Droits cibles par zone")
    d.table(["Rôle", "Bronze", "Silver", "Gold"], [
        ["Identité de l'ingestion (NiFi / Data Factory)", "Écriture", "-", "-"],
        ["Identité des traitements Spark", "Lecture", "Écriture", "Écriture"],
        ["Équipe Data", "Lecture", "Lecture / écriture", "Lecture / écriture"],
        ["Analystes et métiers", "-", "-", "Lecture"],
        ["Contrôle de gestion", "-", "-", "Lecture (mesures financières)"],
    ], widths=[40, 20, 20, 20])

    d.h1("3. Comparaison local / cloud")
    d.table(["Critère", "Local", "Azure", "Lecture"], [
        ["Coût de démarrage", "Matériel et temps d'installation", "Aucun matériel ; paiement à l'usage", "Le cloud réduit l'investissement initial."],
        ["Coût d'exploitation", "Faible pour 1 Go ; fixe", "Variable : stockage, transactions, sorties", "Le cloud demande un suivi budgétaire."],
        ["Élasticité", "Limitée par la machine", "Capacité ajustable à la demande", f"Pour {mo(total_octets())}, le besoin n'impose pas le cloud."],
        ["Sécurité et accès", "Permissions HDFS, gérées à la main", "Identités centralisées, RBAC et ACL", "Le cloud simplifie la gestion des identités."],
        ["Maîtrise", "Totale (infrastructure)", "Partagée avec le fournisseur", "Dépendance au fournisseur à évaluer."],
        ["Transposabilité", "Référence du parcours", "Même zones, mêmes formats", "Migration logique simple ; la mise en oeuvre reste à tester. " + S("H")],
    ], widths=[16, 26, 30, 28])
    d.h2("Points de vigilance de la migration")
    d.ul([
        "**Petits fichiers** : les 36 fichiers sont peu nombreux mais le refresh peut en produire beaucoup ; compactage à prévoir côté cloud comme en local.",
        "**Sortie réseau** : les lectures depuis l'extérieur d'Azure sont facturées : garder les traitements et les requêtes près du stockage.",
        "**Données personnelles** : localisation des données et protection à valider avec le référent. " + S("A"),
        "**Delta Lake / Lakehouse** : reste facultatif ; ne pas migrer vers un format de table sans besoin démontré.",
    ])
    d.save_pdf(OUT / "UC02_local_vers_azure.pdf")
    print("écrit UC02_local_vers_azure.pdf")


if __name__ == "__main__":
    check_chrome()
    cible = sys.argv[1] if len(sys.argv) > 1 else "all"
    for nom, fn in (("comparaison", build_comparaison), ("cible", build_cible), ("flux", build_flux),
                    ("composants", build_composants), ("gouvernance", build_gouvernance), ("azure", build_azure)):
        if cible in ("all", nom):
            fn()
