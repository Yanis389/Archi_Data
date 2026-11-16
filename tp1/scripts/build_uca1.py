#!/usr/bin/env python3
"""Génère les trois livrables de la partie avancée (UC-A1) dans 04_avance/ :

  UC-A1_architecture_detaillee.pdf   UC-A1_strategie_donnees.pdf   UC-A1_gouvernance_et_supervision.pdf

Conception logique détaillée, fondée sur les constats de l'UC-01 et l'architecture de l'UC-02.
Rien n'est déployé ni testé : les seuils chiffrés sont des PROPOSITIONS à valider.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preuves import P, ROOT, couverture, fmt, lignes, mo, pct, qual, total_octets  # noqa: E402
from rapport import S, Doc, check_chrome, svg_arrow, svg_box, svg_wrap  # noqa: E402

OUT = ROOT / "04_avance"
MISSION = ("**Votre mission.** Consultant Data auprès de Retail Intelligence : détailler l'architecture logique de l'UC-02 "
           "pour plusieurs usages et plusieurs types de données. Ce document relève de **UC-A1** (partie avancée, hors "
           "validation du TP) ; c'est une **conception logique**, rien n'est présenté comme déployé.")

QD = qual("store_sales", "Doublons")["nb_concernes"]
NB_DAT = len([f for f in P["fichiers"] if f["format"] == "dat"])


# ----------------------------------------------------------------------------- 1. architecture détaillée
def pipeline_svg() -> str:
    y, h, w = 40, 46, 100
    xs = [10 + i * 122 for i in range(6)]
    etapes = [("Dépôt du lot", "NiFi : liste et lit les fichiers", "x"), ("Manifeste", "nom, source, taille, lignes, empreinte", "x"),
              ("Contrôle de format", "champs par ligne = schéma", "t"), ("Bronze", "brut, immuable, partitionné par lot", "p"),
              ("Silver", "typage, doublons, jointures", "d"), ("Gold", "étoile, mesures agrégées", "v")]
    s = ['<text x="10" y="18" font-size="10" font-weight="700" fill="#1b3a57">Chemin d\'un lot batch</text>']
    for x, (t, sub, st) in zip(xs, etapes):
        s.append(svg_box(x, y, w, h, t, st, size=9, bold=True, sub=sub))
    for a, b in zip(xs[:-1], xs[1:]):
        s.append(svg_arrow(a + w, y + h / 2, b, y + h / 2, curve=False))
    s.append(svg_box(xs[2] - 6, 150, w + 12, 38, "Quarantaine", "n", size=9, bold=True, sub="fichier rejeté + motif"))
    s.append(svg_box(xs[4] - 6, 150, w + 12, 38, "Table de rejets", "n", size=9, bold=True, sub="lignes écartées + règle"))
    s.append(svg_arrow(xs[2] + w / 2, y + h, xs[2] + w / 2 + 5, 150, curve=False, dash="4 3"))
    s.append(svg_arrow(xs[4] + w / 2, y + h, xs[4] + w / 2 + 5, 150, curve=False, dash="4 3"))
    s.append(svg_box(10, 215, 724, 30, "Journal de suivi : lot, table, lignes lues / écrites / rejetées, durée, version du code, état", "b", size=9, bold=True))
    return svg_wrap(744, 255, "".join(s))


def build_architecture() -> None:
    d = Doc("Architecture détaillée", "Flux d'ingestion, points de conception et évolutions",
            "UC-A1 - Architecture analytique cible détaillée", MISSION)
    d.h1("1. Points de l'UC-02 qui demandent plus de détail")
    d.table(["Point", "Pourquoi", "Traité dans"], [
        ["Chemin d'un lot et reprise sur erreur", "Un lot rejeté ou interrompu doit pouvoir être rejoué sans doublon", "§2"],
        ["Règle de dédoublonnage des faits", f"{fmt(QD)} doublons de clé en magasin ; règle non validée " + S("A"), "§4"],
        ["Intégration de `data_refresh`", "Clés disjointes, 2005 complétée de 347 à 365 jours, collisions sur 2 tables de retours", "§4"],
        ["Texte libre et journal de clics", "Seules données qui s'écartent du modèle relationnel", "§3 et stratégie de données"],
        ["Évolution vers le cloud", "Objectif obligatoire du parcours (ADLS Gen2)", "§6"],
    ])

    d.h1("2. Flux d'ingestion batch")
    d.figure(pipeline_svg(), "Figure 1 - Chemin d'un lot de la source à la zone Gold, avec les points de rejet.")
    d.table(["Étape", "Règle", "Si échec"], [
        ["Dépôt du lot", "Un lot = un dossier `source/table/ingest_date=AAAA-MM-JJ/`", "Reprise du dépôt, aucun effet en aval"],
        ["Manifeste", "Écrit avant tout traitement : nom d'origine, source (`data` ou `data_refresh`), taille, lignes, empreinte", "Lot refusé sans manifeste"],
        ["Contrôle de format", "Nombre de champs par ligne égal au schéma attendu ; fichier non vide", "Quarantaine du fichier avec le motif"],
        ["Bronze", "Copie sans transformation ; **immuable**", "—"],
        ["Silver", "Typage, noms de colonnes, doublons, contrôle des clés et des orphelins", "Lignes écartées dans une table de rejets, le lot continue si le taux de rejet reste sous le seuil"],
        ["Gold", "Dimensions et faits, mesures du dictionnaire de KPI", "Publication bloquée si la réconciliation des totaux échoue"],
    ])
    d.p("Le chargement suit l'ordre **référentiels, puis faits**, pour que les jointures soient contrôlables. Un traitement Silver ou "
        "Gold qui échoue est **relancé depuis Bronze** : il est idempotent, c'est-à-dire qu'il réécrit sa partition sans doubler les lignes. " + S("H"))

    d.h1("3. Flux continu éventuel")
    d.p("Aucun besoin de latence de quelques secondes n'est exprimé (UC-01) : le **batch reste le mode retenu**. Un flux continu "
        "n'est envisagé que si un cas d'usage de réaction en temps réel apparaît, par exemple détecter un abandon de panier.")
    d.table(["Donnée", "Mode retenu", "Condition pour envisager le continu", "Statut"], [
        ["Ventes, retours", "Batch quotidien", "Pilotage intra-journalier demandé par les magasins", S("H")],
        ["Stocks", "Batch hebdomadaire (relevé hebdomadaire observé)", "Alerte de rupture en cours de journée", S("H")],
        ["Clics web", "Batch quotidien", "Besoin d'action pendant la visite (recommandation, panier abandonné)", S("H")],
        ["`data_refresh`", "Lot périodique", "—", S("D")],
    ])

    d.h1("4. Points de conception à trancher")
    d.table(["Sujet", "Option proposée", "Alternative", "Décision"], [
        ["Doublons de clé des faits", "Conserver toutes les lignes en Silver avec un identifiant technique et marquer les doublons", "Supprimer les doublons dès Silver", S("A")],
        ["Collisions `data` / `data_refresh`", "Garder les deux sources, trancher par règle documentée (ex. refresh prioritaire)", "Écraser `data`", S("A")],
        ["Produits d'inventaire absents de `item`", "Complément par `data_refresh/item` en Silver", "Rejeter les lignes", S("D")],
        ["Colonnes personnelles de `customer`", "Masquer ou hacher en Silver/Gold", "Conserver en clair", S("A")],
    ])

    d.h1("5. Besoins d'accès et de requête")
    d.table(["Usage", "Zone lue", "Outil logique"], [
        ["Indicateurs de pilotage (KPI)", "Gold (étoile)", "Spark SQL"],
        ["Exploration et contrôle de qualité", "Silver", "Python / PySpark"],
        ["Analyse des avis (texte)", "Silver (texte conservé)", "PySpark ; besoin à confirmer " + S("H")],
        ["Reconstruction après correction de règle", "Bronze", "PySpark"],
    ])

    d.h1("6. Évolution vers le cloud")
    d.p("Les zones et les règles sont **indépendantes de la technologie** : seul l'outil de chaque couche change. "
        "Stockage HDFS vers ADLS Gen2, NiFi vers Azure Data Factory, Spark vers Azure Synapse (ou Spark géré). Les détails "
        "figurent dans `UC02_local_vers_azure.pdf` ; ils restent une conception, non déployée. " + S("H"))

    d.h1("7. Limites et risques de la proposition")
    d.ul([
        "Aucun composant n'a été installé ni mesuré : les performances et la taille réelle en Parquet sont inconnues. " + S("V"),
        "Les noms de colonnes sont déduits ; une erreur de déduction se propagerait jusqu'à Gold. " + S("D"),
        "Les règles de doublons et de collisions sont à valider ; un mauvais choix fausse les mesures. " + S("A"),
        f"Les jeux de données sont synthétiques ({mo(total_octets())}) : la conception n'est pas éprouvée à grande échelle. " + S("V"),
    ])
    d.save_pdf(OUT / "UC-A1_architecture_detaillee.pdf")
    print("écrit UC-A1_architecture_detaillee.pdf")


# ----------------------------------------------------------------------------- 2. stratégie de données
def build_strategie() -> None:
    d = Doc("Stratégie de données", "Partitionnement, formats, nommage et traçabilité",
            "UC-A1 - Architecture analytique cible détaillée", MISSION)
    ss, wr, sr, inv, wc = (couverture(t) for t in ("store_sales", "web_returns", "store_returns", "inventory", "web_clickstreams"))
    n_ss = lignes("store_sales")

    d.h1("1. Partitionnement")
    d.p("Le partitionnement vise des lectures par période sans multiplier les petits fichiers. Il s'appuie sur les périodes "
        "réellement observées (UC-01).")
    d.table(["Table", "Période observée (`data`)", "Lignes", "Partition proposée", "Raison"], [
        ["`store_sales`", f"{ss['date_min']} à {ss['date_max']}", fmt(n_ss), "année de vente", f"Environ {fmt(n_ss // 5)} lignes par année ; un découpage par mois donnerait environ {fmt(n_ss // 60)} lignes par partition, trop petit " + S("D")],
        ["`web_sales`", "idem", fmt(lignes("web_sales")), "année de vente", "Même raisonnement"],
        ["`store_returns`", f"{sr['date_min']} à {sr['date_max']}", fmt(lignes("store_returns")), "année de retour", "Retours datés jusqu'en 2007 ; faible volume"],
        ["`web_returns`", f"{wr['date_min']} à {wr['date_max']}", fmt(lignes("web_returns")), "année de retour", "Retours datés jusqu'en 2008"],
        ["`inventory`", f"{inv['date_min']} à {inv['date_max']} ({inv['jours_distincts']} relevés)", fmt(lignes("inventory")), "année du relevé", "Relevé hebdomadaire ; table la plus volumineuse en lignes"],
        ["`web_clickstreams`", f"{wc['date_min']} à {wc['date_max']}", fmt(lignes("web_clickstreams")), "année puis mois du clic", "Table la plus lourde ; lectures sur des fenêtres courtes " + S("H")],
        ["Référentiels (15 tables)", "—", "—", "aucune", "Petites tables, lues en entier"],
        ["`product_reviews`", f"{couverture('product_reviews')['date_min']} à {couverture('product_reviews')['date_max']}", fmt(lignes("product_reviews")), "année de l'avis", "Volume modéré ; texte long"],
    ])
    d.box("À vérifier", "Les tailles de partition sont des **estimations** déduites des lignes ; la taille réelle après conversion en "
          "Parquet n'a pas été mesurée. Un fichier de quelques Mo par partition est un minimum à viser. " + S("H"), "warn")

    d.h1("2. Positionnement des formats")
    d.table(["Format", "Usage proposé", "Présent dans le kit", "Remarque"], [
        ["**Texte délimité `.dat` / CSV**", "Format d'entrée en Bronze, conservé tel que reçu", f"Oui : {NB_DAT} `.dat` et 2 `.csv`", "Pas d'en-tête sur les `.dat` ; lecture lente sur de gros volumes " + S("V")],
        ["**Parquet**", "Silver et Gold : stockage colonnaire, compression, schéma embarqué", "Non (format cible)", "Bien adapté aux agrégations par colonne " + S("D")],
        ["**JSON**", "Manifestes de lot et journaux de suivi ; source semi-structurée éventuelle", "**Non** : aucun fichier JSON dans le kit", "Utilisé pour les métadonnées produites par la plateforme, pas pour les données TPCx-BB " + S("N")],
    ])
    d.p("Un fichier délimité qui exporte une table relationnelle reste une donnée **structurée** ; le format ne dit pas à lui seul "
        "le niveau de structure.")

    d.h1("3. Règles de nommage")
    d.table(["Élément", "Règle", "Exemple"], [
        ["Zones", "Trois zones en minuscules", "`bronze`, `silver`, `gold`"],
        ["Chemin Bronze", "`/datalake/bronze/<source>/<table>/ingest_date=AAAA-MM-JJ/`", "`/datalake/bronze/tpcxbb/store_sales/ingest_date=2026-11-16/`"],
        ["Chemin Silver", "`/datalake/silver/<domaine>/<table>/`", "`/datalake/silver/ventes/store_sales/`"],
        ["Chemin Gold", "`/datalake/gold/<table>/annee=AAAA/`", "`/datalake/gold/fait_vente_magasin/annee=2005/`"],
        ["Tables Gold", "`dim_` pour les dimensions, `fait_` pour les faits", "`dim_produit`, `fait_retour`"],
        ["Colonnes", "Noms d'origine conservés en Bronze ; noms explicites en Silver, avec la correspondance documentée", "`ss_sold_date_sk` vers `date_vente_sk`"],
        ["Fichiers", "Pas d'espace ni de majuscule ; la date de lot dans le chemin", "—"],
    ])

    d.h1("4. Traçabilité")
    d.table(["Information", "Où elle est écrite", "Pourquoi"], [
        ["Manifeste de lot (nom d'origine, source, taille, lignes, empreinte, date)", "Dossier du lot en Bronze", "Prouver ce qui a été reçu"],
        ["Identifiant de lot", "Colonne `lot_id` ajoutée en Silver et Gold", "Remonter d'une ligne Gold à son fichier d'origine"],
        ["Source (`data` ou `data_refresh`)", "Colonne `source`", "Distinguer le chargement initial du complément"],
        ["Version des règles de transformation", "Journal de suivi", "Rejouer à l'identique"],
        ["Statut de certitude des colonnes (Vérifié / Déduit)", "Dictionnaire de données versionné avec le code", "Ne pas présenter une déduction comme un fait"],
    ])

    d.h1("5. Règles propres à ce kit")
    d.ul([
        f"**Doublons de clé** : {fmt(QD)} en magasin ; conservation de la ligne en Bronze, règle de Silver à valider. " + S("A"),
        "**Références d'avis** : le lien `pr_order_sk` est ambigu entre commande web et ticket magasin ; il n'est pas relié à une commande. " + S("V"),
        "**Dates de fermeture de magasins** : jugées incohérentes ; non utilisées pour filtrer. " + S("V"),
        "**Conservation** : Bronze conservé durablement ; Silver et Gold reconstruisibles depuis Bronze. " + S("D"),
    ])
    d.save_pdf(OUT / "UC-A1_strategie_donnees.pdf")
    print("écrit UC-A1_strategie_donnees.pdf")


# ----------------------------------------------------------------------------- 3. gouvernance et supervision
def build_gouvernance() -> None:
    d = Doc("Gouvernance et supervision", "Contrôle, reprise sur erreur, surveillance et responsabilités",
            "UC-A1 - Architecture analytique cible détaillée", MISSION)
    d.h1("1. Stratégie de contrôle")
    d.p("Les règles reprennent les contrôles réellement exécutés dans l'UC-01 (fichiers `controles_qualite.csv` et "
        "`controles_relations.csv`). Les **seuils** ci-dessous sont des propositions à fixer avec les utilisateurs métier. " + S("A"))
    d.table(["Zone", "Contrôle", "Constat de l'UC-01", "Seuil proposé", "Action"], [
        ["Bronze", "Nombre de champs par ligne = schéma", "34 fichiers sur 34 conformes", "0 écart toléré", "Quarantaine du fichier"],
        ["Bronze", "Fichier non vide, empreinte enregistrée", "36 fichiers lus", "0 fichier vide", "Rejet du lot"],
        ["Silver", "Clé primaire unique et non vide (référentiels)", "17 clés simples uniques", "0 doublon", "Rejet des lignes"],
        ["Silver", "Doublons de clé composite des faits", f"{fmt(QD)} en magasin (environ 0,6 %)", "Alerte au-delà du taux observé", "Marquer, ne pas supprimer, règle à valider"],
        ["Silver", "Orphelins vers les référentiels", "60 relations sur 61 sans orphelin", "0 % attendu ; alerte au premier cas", "Alerte et ligne marquée « inconnue »"],
        ["Silver", "Produits d'inventaire absents de `item`", "232 380 lignes, 180 produits (couverts par `data_refresh/item`)", "0 après intégration du refresh", "Alerte"],
        ["Gold", "Réconciliation : somme des faits Gold = somme Silver", "—", "Écart nul", "Blocage de la publication"],
        ["Gold", "Fraîcheur : date maximale des faits", "`data` s'arrête au 2005-12-13", "Écart à fixer", "Alerte"],
    ])

    d.h1("2. Reprise sur erreur")
    d.table(["Situation", "Détection", "Traitement"], [
        ["Fichier mal formé", "Contrôle du nombre de champs", "Quarantaine ; le reste du lot continue si les fichiers sont indépendants"],
        ["Traitement interrompu", "État du lot dans le journal de suivi", "Relance depuis Bronze ; partition réécrite (idempotence)"],
        ["Règle de transformation corrigée", "Changement de version du code", "Reconstruction de Silver et Gold depuis Bronze"],
        ["Lot déjà chargé", "Empreinte déjà connue", "Ignoré, sans doublon"],
        ["Échec de réconciliation Gold", "Écart entre Silver et Gold", "Publication bloquée ; la version précédente reste lisible"],
    ])
    d.p("Ces mécanismes sont décrits, non testés : aucune reprise n'a été simulée. " + S("V"))

    d.h1("3. Besoins de supervision")
    d.table(["Indicateur", "Ce qu'il montre", "Alerte proposée"], [
        ["Lots réussis / en échec", "Santé générale des chargements", "Tout échec"],
        ["Lignes lues, écrites, rejetées par table", "Perte ou excès de lignes", "Taux de rejet au-dessus du seuil de la zone"],
        ["Durée des traitements", "Dérive de performance", "Durée supérieure à un multiple de la durée habituelle (à calibrer)"],
        ["Fraîcheur par zone", "Retard d'alimentation", "Dernier lot plus ancien que la fréquence attendue"],
        ["Volume par zone", f"Croissance du stockage (kit actuel : {mo(total_octets())})", "Croissance anormale ; petits fichiers"],
        ["Résultat des contrôles de qualité", "Dégradation des données", "Contrôle qui passe de conforme à non conforme"],
        ["Coût (cloud)", "Stockage, transactions, sorties réseau", "Dépassement du budget fixé"],
    ])
    d.p("Sources de ces mesures : journaux NiFi et Spark et table de suivi (en local) ; services de supervision du cloud "
        "(Azure Monitor) en cible. Aucun outil n'est installé à ce stade. " + S("H"))

    d.h1("4. Gouvernance et responsabilités")
    d.table(["Rôle", "Responsabilité", "Décisions"], [
        ["Équipe Data", "Ingestion, transformations, contrôles, supervision", "Règles techniques, reprise sur erreur"],
        ["Propriétaire de domaine (ventes, stocks, produits...)", "Définition des KPI et des règles métier", "Règle de dédoublonnage, traitement des collisions"],
        ["Contrôle de gestion", "Validation des mesures financières", "Définition de la marge (prix sous coût observé)"],
        ["Référent protection des données", "Colonnes personnelles de `customer`", "Masquage et droits d'accès"],
    ])
    d.h2("Accès par zone")
    d.table(["Rôle", "Bronze", "Silver", "Gold"], [
        ["Ingestion", "Écriture", "—", "—"], ["Traitements Spark", "Lecture", "Écriture", "Écriture"],
        ["Équipe Data", "Lecture", "Lecture / écriture", "Lecture / écriture"], ["Analystes et métiers", "—", "—", "Lecture"],
    ])

    d.h1("5. Risques et limites")
    d.ul([
        "Les seuils sont des propositions : sans validation métier, ils peuvent déclencher trop ou trop peu d'alertes. " + S("A"),
        "Le contrôle de fraîcheur dépend de la fréquence réelle des livraisons, inconnue pour ce kit. " + S("V"),
        "Sans propriétaire de domaine désigné, les règles métier (doublons, marge) restent sans arbitre. " + S("H"),
        "La conception n'a été ni déployée ni testée. " + S("V"),
    ])
    d.save_pdf(OUT / "UC-A1_gouvernance_et_supervision.pdf")
    print("écrit UC-A1_gouvernance_et_supervision.pdf")


if __name__ == "__main__":
    check_chrome()
    cible = sys.argv[1] if len(sys.argv) > 1 else "all"
    for nom, fn in (("architecture", build_architecture), ("strategie", build_strategie), ("gouvernance", build_gouvernance)):
        if cible in ("all", nom):
            fn()
