#!/usr/bin/env python3
"""Génère les PDF « besoin » de l'UC-01 :
  - UC01_cadrage_metier.pdf
  - UC01_questions_decisionnelles.pdf (+ preuves/schema_besoins_metier.svg)
Chaque chiffre vient des preuves (profil.json) via preuves.py.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preuves import (P, ROOT, col, couverture, fmt, fichiers, kpi, lignes, mo, pct, qual, rel,  # noqa: E402
                     relations_resume, total_octets)
from rapport import Doc, F, S, check_chrome, flow_diagram  # noqa: E402

OUT = ROOT / "01_UC01_besoin_exploration"
MISSION = ("**Votre mission.** Consultant Data auprès de Retail Intelligence, une enseigne de distribution : "
           "partir des besoins métier, examiner les données réellement disponibles et proposer une première "
           "architecture cohérente. Ce document traite **UC-01 : analyser le besoin métier et explorer les sources**.")


# ----------------------------------------------------------------------------- données communes
PROFILS = [
    ("Direction générale", "Pilote la stratégie et arbitre les investissements ; veut une vision consolidée de l'activité.",
     "Fixer les objectifs de croissance ; arbitrer l'investissement entre magasins et web."),
    ("Direction commerciale", "Responsable de la performance des ventes et de l'assortiment produits.",
     "Choisir l'assortiment, les mises en avant, les promotions et la politique de prix."),
    ("Responsable de magasin", "Gère un établissement : équipe, réassort, animation commerciale.",
     "Organiser les plannings, déclencher un réassort, adapter l'animation locale."),
    ("Contrôleur de gestion", "Suit les indicateurs financiers, les écarts au budget et les comparaisons entre périodes.",
     "Valider les budgets, expliquer les écarts, suivre la rentabilité."),
    ("Responsable des stocks", "Assure la disponibilité des produits et suit les mouvements de stock.",
     "Déclencher un réapprovisionnement, traiter ruptures et surstocks."),
    ("Équipe Data", "Intègre, contrôle la qualité et met les données à disposition des autres profils.",
     "Décider du modèle de données, des contrôles qualité et de l'ordre de chargement."),
    ("Responsable e-commerce / marketing digital *(profil ajouté)*",
     "Suit le comportement des visiteurs du site, la conversion et la satisfaction client.",
     "Améliorer le parcours web, cibler les clients, agir sur les produits mal notés."),
]

# (id, profil, question, décision, KPI, sources, priorité, faisabilité code, commentaire)
# faisabilité : C = couverte, P = partielle, N = non fiable, X = non couverte
QUESTIONS = [
    ("Q01", "Direction générale", "Comment évolue le chiffre d'affaires consolidé (magasin + web) dans le temps ?",
     "Fixer les objectifs de croissance annuels.", "CA total ; évolution annuelle",
     "store_sales, web_sales, date_dim (+ data_refresh pour 2005)", "Indispensable", "P",
     "Calculable, mais 2005 est incomplet dans data seul (347 jours sur 365) et la devise n'est pas précisée."),
    ("Q02", "Direction générale", "Quelle part du chiffre d'affaires est réalisée par chaque canal ?",
     "Répartir l'investissement entre magasins et web.", "CA magasin ; CA web",
     "store_sales, web_sales", "Indispensable", "C", "Canal catalogue absent du kit : la répartition ne couvre que 2 canaux."),
    ("Q03", "Direction générale", "Quels clients achètent à la fois en magasin et en ligne ?",
     "Définir la stratégie omnicanal et les offres croisées.", "Clients acheteurs distincts par canal",
     "store_sales, web_sales, customer", "Utile", "P",
     "Même clé client dans les deux tables mais identité commune non garantie (Hypothèse)."),
    ("Q04", "Direction commerciale", "Quels produits et catégories génèrent le plus de ventes ?",
     "Ajuster l'assortiment et les mises en avant.", "CA par catégorie ; quantités vendues",
     "store_sales, web_sales, item", "Indispensable", "C", "Forte concentration sur Music et Books."),
    ("Q05", "Direction commerciale", "Quels produits font l'objet de retours, et pour quel motif ?",
     "Traiter les problèmes de qualité, agir auprès des fournisseurs.", "Taux de retour ; montant retourné",
     "store_returns, web_returns, reason, item", "Indispensable", "P",
     "Produits et quantités exploitables ; libellés de motif pseudo-aléatoires donc motifs non lisibles."),
    ("Q06", "Direction commerciale", "Les promotions augmentent-elles les ventes ?",
     "Reconduire, ajuster ou arrêter les promotions.", "CA et remise par promotion",
     "promotion, store_sales, web_sales", "Utile", "P",
     "Quasi toutes les lignes portent une promotion : pas de groupe témoin sans promotion pour comparer."),
    ("Q07", "Direction commerciale", "Comment nos prix se situent-ils par rapport à ceux des concurrents ?",
     "Aligner la politique de prix.", "Écart de prix vs concurrents",
     "item_marketprices, item", "Complémentaire", "P", "Concurrents identifiés par un code seulement ; moyenne faussée par des valeurs extrêmes."),
    ("Q08", "Responsable de magasin", "Quel est le CA et le nombre de tickets de mon magasin, et comment se situe-t-il par rapport aux autres ?",
     "Fixer les objectifs locaux, déclencher des actions d'animation.", "CA par magasin ; tickets ; panier moyen",
     "store_sales, store", "Indispensable", "C", "12 magasins très proches en CA : peu de différenciation."),
    ("Q09", "Responsable de magasin", "À quels jours et à quelles heures mon magasin vend-il le plus ?",
     "Adapter les plannings du personnel.", "CA par jour de semaine et par heure",
     "store_sales, date_dim, time_dim", "Utile", "C", "Jointures vers date_dim et time_dim vérifiées sans orphelin."),
    ("Q10", "Contrôleur de gestion", "Quel est l'écart de chiffre d'affaires par rapport à l'année précédente, par canal ?",
     "Expliquer les écarts au budget.", "Évolution annuelle du CA",
     "store_sales, web_sales, date_dim, data_refresh", "Indispensable", "P",
     "Comparable seulement sur des périodes de même durée (data_refresh nécessaire pour 2005)."),
    ("Q11", "Contrôleur de gestion", "Quelle est la marge par catégorie et par canal ?",
     "Renégocier les coûts d'achat, ajuster les prix.", "Marge nette",
     "store_sales, web_sales, item", "Utile", "N",
     "Calculable mais trompeur : le prix de vente est inférieur au coût d'achat sur la majorité des lignes."),
    ("Q12", "Responsable des stocks", "Les niveaux de stock sont-ils suffisants, et où sont les ruptures ?",
     "Déclencher un réapprovisionnement.", "Stock moyen ; taux de rupture",
     "inventory, item, warehouse", "Indispensable", "P",
     "Relevés hebdomadaires seulement ; 180 produits de l'inventaire absents du référentiel initial."),
    ("Q13", "Responsable des stocks", "Quels entrepôts servent les ventes web et avec quel délai d'expédition ?",
     "Optimiser la logistique.", "Délai d'expédition (date d'expédition - date de commande)",
     "web_sales, warehouse, ship_mode, date_dim", "Complémentaire", "P",
     "Colonnes et dates cohérentes, mais libellés des modes d'expédition illisibles ; KPI non calculé au Jour 1."),
    ("Q14", "Responsable e-commerce", "Les données de navigation permettent-elles d'étudier les comportements des visiteurs ?",
     "Améliorer le parcours web et les pages à faible conversion.", "Taux de conversion clic -> commande",
     "web_clickstreams, web_page, web_sales", "Utile", "P",
     "Environ 42 % des clics sont anonymes ; ni session ni ajout au panier."),
    ("Q15", "Responsable e-commerce", "Les avis clients expliquent-ils les ventes ou les retours ?",
     "Agir sur les produits mal notés.", "Note moyenne des avis",
     "product_reviews, item, store_returns, web_returns", "Complémentaire", "P",
     "Note exploitable ; texte libre non structuré ; une corrélation ne prouve pas une causalité."),
    ("Q16", "Responsable e-commerce", "Quelles informations permettent de caractériser les clients ?",
     "Segmenter et cibler les campagnes.", "Clients acheteurs distincts ; répartition démographique",
     "customer, customer_address, customer_demographics, household_demographics, income_band", "Utile", "C",
     "Sexe, statut marital, niveau d'études, tranche de revenus, pays, état : mais aucune donnée de consentement."),
    ("Q17", "Équipe Data", "Peut-on relier de façon fiable ventes, retours, clients, produits, magasins et dates ?",
     "Définir le modèle de données et les contrôles d'intégrité.", "Taux de correspondance des jointures",
     "toutes les tables", "Indispensable", "C", "Quasi toutes les relations vérifiées ; exceptions documentées (voir qualification)."),
    ("Q18", "Équipe Data", "Les données sont-elles complètes et à jour pour alimenter la plateforme ?",
     "Définir l'ordre de chargement et le traitement de data_refresh.", "Complétude ; recouvrement initial / refresh",
     "data, data_refresh", "Indispensable", "P",
     "data_refresh est un complément incrémental ; certains liens (retours -> ventes) y sont incomplets."),
]


def tag_faisabilite(code: str) -> str:
    return F(code)


# ----------------------------------------------------------------------------- cadrage métier
def build_cadrage() -> None:
    d = Doc("Cadrage métier", "Utilisateurs, besoins, périmètre des données et fiche du kit",
            "UC-01 - Analyser le besoin métier et explorer les sources", MISSION)
    n_data = len(fichiers("data"))
    n_ref = len(fichiers("data_refresh"))
    dat = [f for f in P["fichiers"] if f["format"] == "dat"]
    csvs = [f for f in P["fichiers"] if f["format"] == "csv"]
    mt = [os.stat(Path(P["data_root"]) / f["chemin_relatif"]).st_mtime for f in P["fichiers"]]
    mt_min, mt_max = datetime.fromtimestamp(min(mt)), datetime.fromtimestamp(max(mt))
    jours = (f"{mt_min:%d/%m/%Y}" if mt_min.date() == mt_max.date() else f"{mt_min:%d/%m/%Y} au {mt_max:%d/%m/%Y}")

    d.h1("1. Objectif du document")
    d.p("Ce document cadre le besoin de **Retail Intelligence**, enseigne de distribution disposant de plusieurs canaux de "
        "vente. Les directions commerciale et financière veulent des indicateurs cohérents, comparer les performances et "
        "mieux comprendre l'évolution de l'activité. Avant de concevoir une architecture, il faut (1) comprendre les "
        "besoins, (2) vérifier que les données nécessaires existent réellement.")
    d.p("Chaque affirmation porte un statut : " + S("V") + " observée dans un fichier, " + S("D") + " déduite avec "
        "justification, " + S("H") + " à confirmer, " + S("N") + " absente, " + S("A") + " à faire valider par le "
        "formateur. Les chiffres proviennent d'un script reproductible (`scripts/profiler_tpcx_bb.py`) et sont "
        "conservés dans `preuves/`.")

    d.h1("2. Fiche d'identification du kit de données")
    d.table(["Information", "Valeur constatée", "Statut"], [
        ["Nom du kit ou de l'archive", "Dossier `retail_project` contenant `data/` (chargement initial) et "
         "`data_refresh/` (rafraîchissement). Aucun nom d'archive ni de version n'accompagne le dossier.", S("V")],
        ["Version", "Non communiquée. Aucune version n'est déduite du nom des fichiers (consigne du TP).", S("A")],
        ["Provenance", "Non communiquée dans le kit. La structure est celle d'un jeu TPCx-BB (tables TPC-DS plus "
         "`web_clickstreams`, `product_reviews`, `item_marketprices`) : le cours indique TPCx-BB comme source du projet.",
         S("D") + " " + S("A")],
        ["Date de mise à disposition", f"Non communiquée. Les fichiers portent l'horodatage {jours} sur le poste "
         "de travail (date de copie, pas de publication).", S("A")],
        ["Source de téléchargement ou de distribution", "Non communiquée.", S("A")],
        ["Format des fichiers", f"{len(dat)} fichiers `.dat` : texte délimité par `|`, fins de ligne CRLF, **sans ligne "
         f"d'en-tête**. {len(csvs)} fichiers `.csv` (`item_marketprices_audit.csv`, une par dossier) avec en-tête.", S("V")],
        ["Volume total constaté", f"{mo(total_octets())} ({fmt(total_octets())} octets) ; "
         f"dont {mo(sum(int(f['taille_octets']) for f in fichiers('data')))} dans `data/` et "
         f"{mo(sum(int(f['taille_octets']) for f in fichiers('data_refresh')))} dans `data_refresh/`.", S("V")],
        ["Nombre de fichiers", f"{len(P['fichiers'])} ({n_data} dans `data/`, {n_ref} dans `data_refresh/`) ; "
         f"{len(set(f['table'] for f in dat))} tables distinctes.", S("V")],
        ["Outils de génération éventuellement utilisés", "Non communiqués. Les fichiers `*_audit.csv` montrent qu'un "
         "outil a audité sa sortie ; PDGF est cité par le cours comme générateur possible, sans que le kit l'atteste.",
         S("H") + " " + S("A")],
    ], widths=[24, 62, 14])
    d.box("Ce que le kit ne contient pas",
          "Aucun dictionnaire de données, aucune documentation, aucune ligne d'en-tête : les **noms de colonnes sont "
          "déduits** de la structure TPC-DS / BigBench (statut Déduit). Le nombre de champs de chaque fichier "
          "correspond au schéma déduit pour les " + str(len(dat)) + " fichiers `.dat`, et les clés étrangères se "
          "rejoignent sans orphelin dans l'immense majorité des cas : cela renforce l'hypothèse sans l'établir "
          "formellement.", "warn")

    d.h1("3. Utilisateurs concernés et responsabilités")
    d.p("Six profils sont proposés par le sujet ; un septième a été ajouté car le kit contient des données de navigation "
        "web et d'avis clients qui ne concernent aucun des six premiers de façon directe.")
    d.table(["Profil", "Responsabilités", "Décisions typiques"], [list(p) for p in PROFILS], widths=[22, 40, 38])

    d.h1("4. Besoins métier priorisés")
    d.p("Les besoins sont issus des questions initiales du sujet, reformulées en questions décisionnelles (voir le "
        "livrable `UC01_questions_decisionnelles.pdf`). Classement : **indispensable** (sans lui le pilotage est "
        "impossible), **utile**, **complémentaire**.")
    from collections import Counter
    prio = Counter(q[6] for q in QUESTIONS)
    fais = Counter(q[7] for q in QUESTIONS)
    d.kpis([(str(len(QUESTIONS)), "questions décisionnelles"), (str(prio["Indispensable"]), "indispensables"),
            (str(fais["C"]), "pleinement couvertes"), (str(fais["P"]), "partiellement couvertes"),
            (str(fais["N"] + fais["X"]), "non fiables ou non couvertes")])
    rows = []
    for niveau in ("Indispensable", "Utile", "Complémentaire"):
        for q in QUESTIONS:
            if q[6] == niveau:
                rows.append([niveau, q[0] + " - " + q[2], q[1], tag_faisabilite(q[7])])
    d.table(["Priorité", "Besoin (question décisionnelle)", "Profil", "Données"], rows, widths=[16, 52, 17, 15])

    d.h1("5. Ce que les données permettent réellement")
    d.p("Le sujet demande de ne pas confondre ce que l'entreprise souhaite analyser, ce que les fichiers permettent "
        "d'analyser, ce qui nécessiterait une source complémentaire et ce qui reste une hypothèse.")
    sr = rel("store_sales", "ss_item_sk", "item")
    d.table(["Catégorie", "Éléments", "Statut"], [
        ["**Souhaité et permis par les fichiers**",
         f"Évolution du CA par canal, par catégorie et par magasin ({fmt(lignes('store_sales'))} lignes magasin, "
         f"{fmt(lignes('web_sales'))} lignes web, jointures produit/date/magasin sans orphelin : "
         f"{pct(sr['pct_orphelines'], 1)}) ; nombre de transactions ; panier moyen ; quantités ; taux de retour ; "
         "caractérisation démographique des clients ; stocks hebdomadaires.", S("V")],
        ["**Souhaité, permis avec réserves**",
         "Marge (prix de vente sous le coût d'achat dans la majorité des lignes) ; promotions (quasi toutes les lignes en "
         "portent une) ; comportement web (42 % de clics anonymes) ; motifs de retour (libellés illisibles) ; "
         "comparaison avec les concurrents (identités absentes).", S("H")],
        ["**Souhaité mais nécessitant une source complémentaire**",
         "Devise, taxes et frais réels ; ajouts au panier et sessions web ; budgets et objectifs par magasin ; "
         "canal catalogue ; consentement et canaux de contact clients ; motifs de retour lisibles ; "
         "coûts de structure pour une vraie marge.", S("N")],
        ["**Hypothèses à vérifier**",
         "Les noms de colonnes déduits sont exacts ; un même numéro de client désigne la même personne en magasin et en "
         "ligne ; `data_refresh` complète `data` sans le remplacer ; la quasi-égalité exacte de transactions entre "
         "canaux (89 100) est un artefact du générateur.", S("H") + " " + S("A")],
    ], widths=[22, 66, 12])

    d.h1("6. Synthèse")
    rs = relations_resume("data")
    d.ul([
        f"**Couverture des besoins** : {fais['C']} questions sur {len(QUESTIONS)} sont pleinement couvertes, "
        f"{fais['P']} partiellement, {fais['N'] + fais['X']} sont non fiables ou non couvertes.",
        f"**Jointures** : {rs['verifiees']} relations sur {rs['total']} contrôlées dans `data` n'ont aucun orphelin ; "
        f"{rs['partielles']} est partielle (inventaire -> produit, 180 produits ne figurent que dans `data_refresh`).",
        "**Point de méthode** : ce cadrage est établi à partir des fichiers réellement observés ; ce qui n'a pas pu "
        "être vérifié est marqué « à valider » plutôt que supposé.",
    ])
    d.save_pdf(OUT / "UC01_cadrage_metier.pdf")
    print("écrit UC01_cadrage_metier.pdf")


# ----------------------------------------------------------------------------- questions décisionnelles + schéma
def schema_besoins() -> str:
    cols = [
        {"titre": "Utilisateurs", "noeuds": [
            {"id": "u1", "texte": "Direction générale"}, {"id": "u2", "texte": "Direction commerciale"},
            {"id": "u3", "texte": "Responsable de magasin"}, {"id": "u4", "texte": "Contrôle de gestion"},
            {"id": "u5", "texte": "Responsable des stocks"}, {"id": "u6", "texte": "E-commerce / marketing"},
            {"id": "u7", "texte": "Équipe Data"}]},
        {"titre": "Questions décisionnelles", "noeuds": [
            {"id": "q1", "texte": "Évolution et répartition du CA"}, {"id": "q2", "texte": "Produits qui vendent"},
            {"id": "q3", "texte": "Retours et leurs motifs"}, {"id": "q4", "texte": "Performance par magasin"},
            {"id": "q5", "texte": "Marge et écarts vs année N-1"}, {"id": "q6", "texte": "Stocks et ruptures"},
            {"id": "q7", "texte": "Comportement web et avis"}, {"id": "q8", "texte": "Profil des clients"},
            {"id": "q9", "texte": "Fiabilité des données"}]},
        {"titre": "Indicateurs (KPI)", "noeuds": [
            {"id": "k1", "texte": "CA, évolution", "st": "d"}, {"id": "k2", "texte": "Transactions, panier moyen", "st": "d"},
            {"id": "k3", "texte": "Quantités, remise", "st": "d"}, {"id": "k4", "texte": "Taux de retour", "st": "d"},
            {"id": "k5", "texte": "Marge nette", "st": "n"}, {"id": "k6", "texte": "Stock, taux de rupture", "st": "d"},
            {"id": "k7", "texte": "Conversion clic -> commande", "st": "p"}, {"id": "k8", "texte": "Note des avis", "st": "d"},
            {"id": "k9", "texte": "Clients distincts", "st": "d"}]},
        {"titre": "Domaines de données", "noeuds": [
            {"id": "d1", "texte": "Ventes magasin", "st": "v"}, {"id": "d2", "texte": "Ventes web", "st": "v"},
            {"id": "d3", "texte": "Retours", "st": "p"}, {"id": "d4", "texte": "Produits et prix", "st": "v"},
            {"id": "d5", "texte": "Clients", "st": "v"}, {"id": "d6", "texte": "Stocks", "st": "p"},
            {"id": "d7", "texte": "Navigation web", "st": "p"}, {"id": "d8", "texte": "Avis produits", "st": "v"},
            {"id": "d9", "texte": "Non couvert : devise, panier, budgets", "st": "n"}]},
        {"titre": "Fichiers observés", "noeuds": [
            {"id": "f1", "texte": "store_sales", "st": "v"}, {"id": "f2", "texte": "web_sales", "st": "v"},
            {"id": "f3", "texte": "store_returns, web_returns, reason", "st": "p"},
            {"id": "f4", "texte": "item, item_marketprices", "st": "v"},
            {"id": "f5", "texte": "customer + 4 tables", "st": "v"}, {"id": "f6", "texte": "inventory", "st": "p"},
            {"id": "f7", "texte": "web_clickstreams, web_page", "st": "p"}, {"id": "f8", "texte": "product_reviews", "st": "v"},
            {"id": "f9", "texte": "Absent du kit", "st": "h"}]},
    ]
    E = [("u1", "q1"), ("u1", "q8"), ("u2", "q2"), ("u2", "q3"), ("u3", "q4"), ("u4", "q5"), ("u4", "q1"),
         ("u5", "q6"), ("u6", "q7"), ("u6", "q8"), ("u7", "q9"),
         ("q1", "k1"), ("q1", "k2"), ("q2", "k3"), ("q2", "k1"), ("q3", "k4"), ("q4", "k2"), ("q4", "k1"),
         ("q5", "k5"), ("q5", "k1"), ("q6", "k6"), ("q7", "k7"), ("q7", "k8"), ("q8", "k9"), ("q9", "k9"),
         ("k1", "d1"), ("k1", "d2"), ("k2", "d1"), ("k2", "d2"), ("k3", "d1"), ("k3", "d2"), ("k4", "d3"),
         ("k5", "d1", "4 3"), ("k5", "d9", "4 3"), ("k6", "d6"), ("k7", "d7"), ("k7", "d2"), ("k8", "d8"),
         ("k9", "d5"), ("k9", "d1"), ("k2", "d9", "4 3"),
         ("d1", "f1"), ("d2", "f2"), ("d3", "f3"), ("d4", "f4"), ("d5", "f5"), ("d6", "f6"), ("d7", "f7"),
         ("d8", "f8"), ("d9", "f9", "4 3")]
    return flow_diagram(cols, E, width=780, node_h=32, gap=9,
                        legend=[("v", "Source vérifiée"), ("p", "Partielle / avec réserves"),
                                ("n", "Non fiable ou non couvert"), ("h", "Absent ou supposé"), ("d", "KPI calculable")])


def build_questions() -> None:
    d = Doc("Questions décisionnelles", "Matrice utilisateurs, questions, décisions, KPI et sources",
            "UC-01 - Analyser le besoin métier et explorer les sources", MISSION)
    d.h1("1. Principe")
    d.p("Chaque question métier est reliée à **une décision possible** (ce qu'elle permet de changer), aux **KPI** qui y "
        "répondent, aux **fichiers** nécessaires et à sa **faisabilité** constatée sur les données réelles. "
        "Les questions initiales du sujet sont toutes reprises : produits qui vendent (Q04), évolution dans le temps "
        "(Q01, Q10), performances par magasin (Q08), volumes par canal (Q02), retours (Q05), caractérisation des clients "
        "(Q16), stocks (Q12), navigation web (Q14). Les autres ont été ajoutées pour que **chaque profil** ait au moins "
        "deux questions.")
    d.table(["Faisabilité", "Signification"], [
        [F("C"), "Les fichiers et les jointures nécessaires ont été observés et contrôlés."],
        [F("P"), "Calculable, mais avec une limite documentée (période, anonymat, libellés, grain...)."],
        [F("N"), "Calculable mais le résultat serait trompeur avec ces données."],
    ], widths=[24, 76])

    d.landscape(True)
    d.h1("2. Matrice utilisateurs - questions - décisions")
    rows = [[q[0], q[1], q[2], q[3], q[4], q[5], q[6], tag_faisabilite(q[7]), q[8]] for q in QUESTIONS]
    d.table(["N°", "Profil", "Question métier", "Décision associée", "KPI", "Sources", "Priorité", "Faisabilité",
             "Commentaire"], rows, widths=[4, 9, 17, 13, 11, 13, 10, 8, 15])
    d.landscape(False)

    d.h1("3. Schéma des besoins métier")
    d.p("Le schéma relie les utilisateurs aux questions, aux indicateurs, aux domaines de données et aux fichiers "
        "effectivement observés. Les éléments **vérifiés** (vert) sont distingués de ceux qui sont partiels, non "
        "fiables ou simplement souhaités (pointillés).")
    svg = schema_besoins()
    (OUT / "preuves" / "schema_besoins_metier.svg").write_text(svg, encoding="utf-8")
    d.figure(svg, "Figure 1 - Des utilisateurs aux fichiers : ce qui est vérifié et ce qui ne l'est pas.")

    d.h1("4. Lecture des priorités")
    from collections import Counter
    by = Counter((q[1], q[6]) for q in QUESTIONS)
    profils = []
    for q in QUESTIONS:
        if q[1] not in profils:
            profils.append(q[1])
    d.table(["Profil", "Indispensable", "Utile", "Complémentaire", "Total"],
            [[p, by[(p, "Indispensable")], by[(p, "Utile")], by[(p, "Complémentaire")],
              sum(1 for q in QUESTIONS if q[1] == p)] for p in profils], num_cols=(1, 2, 3, 4),
            widths=[40, 15, 15, 17, 13])
    d.box("Contrôle de validation (sujet, §15)",
          "- Chaque profil possède des besoins identifiés : **oui**, au moins deux questions par profil.\n"
          "- Chaque question est associée à une décision : **oui** (colonne « Décision associée »).\n"
          "- Les questions sans données suffisantes sont signalées (faisabilité partielle ou non fiable) plutôt que masquées.",
          "ok")
    d.save_pdf(OUT / "UC01_questions_decisionnelles.pdf")
    print("écrit UC01_questions_decisionnelles.pdf + schema_besoins_metier.svg")


if __name__ == "__main__":
    check_chrome()
    build_cadrage()
    build_questions()
