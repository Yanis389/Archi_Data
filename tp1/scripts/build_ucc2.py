#!/usr/bin/env python3
"""Génère 03_complementaire/UC-C2_limites_BI_et_evolutions.pdf (partie complémentaire, facultative).

Limites d'une architecture décisionnelle classique (Data Warehouse), volume / vélocité / variété,
classement structuré / semi-structuré / non structuré à partir des fichiers réellement observés.
Chiffres issus des preuves de l'UC-01 (profil.json) via preuves.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preuves import P, ROOT, fmt, lignes, mo, pct, qual, total_octets  # noqa: E402
from rapport import S, Doc, check_chrome  # noqa: E402

OUT = ROOT / "03_complementaire"
MISSION = ("**Votre mission.** Consultant Data auprès de Retail Intelligence : identifier les situations où une "
           "architecture décisionnelle classique doit évoluer, à partir des fichiers réellement observés. Ce document "
           "traite **UC-C2** (partie complémentaire, hors validation de UC-01 et UC-02).")


def taille(table: str) -> int:
    return sum(int(f["taille_octets"]) for f in P["fichiers"] if f["table"] == table and f["format"] == "dat")


def build() -> None:
    total = total_octets()
    nb_dat = len([f for f in P["fichiers"] if f["format"] == "dat"])
    nb_csv = len([f for f in P["fichiers"] if f["format"] == "csv"])
    nb_lignes = sum(int(f["lignes"]) for f in P["fichiers"] if f["format"] == "dat")
    clics, avis = taille("web_clickstreams"), taille("product_reviews")
    nb_autres = len([f for f in P["fichiers"] if f["format"] == "dat" and f["table"] in ("web_clickstreams", "product_reviews", "item_marketprices")])
    n_clics = lignes("web_clickstreams")

    d = Doc("Limites de la BI classique et évolutions", "Volume, vélocité, variété et classement des données observées",
            "UC-C2 - Étudier les limites de la BI classique", MISSION)

    d.h1("1. Limites d'une architecture Data Warehouse seule")
    d.p("On suppose une architecture décisionnelle classique : les sources sont extraites, transformées vers un schéma "
        "défini à l'avance, chargées dans un Data Warehouse, puis interrogées en SQL (principe *schema-on-write*). Elle est "
        "adaptée aux indicateurs stables. Appliquée à ce kit, ses limites sont les suivantes.")
    d.table(["Limite du Data Warehouse seul", "Ce qu'on observe dans le kit", "Statut"], [
        ["Le schéma doit être défini avant le chargement", "Aucun dictionnaire fourni : les noms de colonnes sont **déduits**. Un chargement direct imposerait de les figer sans validation.", S("V")],
        ["Les données brutes ne sont pas conservées", "Les clés des tables de faits ne sont pas uniques (environ 0,6 % de doublons) : sans le brut, la règle de dédoublonnage choisie ne peut plus être corrigée.", S("V")],
        ["Le texte libre est mal adapté", f"`product_reviews` contient un champ de texte long ({mo(avis)}, {fmt(lignes('product_reviews'))} lignes dans `data`).", S("V")],
        ["Le rafraîchissement incrémental est lourd à rejouer", "`data_refresh` complète `data` (clés disjointes) : il faut ajouter sans écraser, puis arbitrer les collisions.", S("V")],
        ["L'historisation n'est pas fournie", "Les colonnes de fin de validité sont vides à 100 % sur 4 tables : un suivi de l'évolution des référentiels n'est pas possible.", S("V")],
        ["Le coût et la rigidité augmentent avec les nouveaux usages", "Aucun besoin de ce type n'est exprimé dans le kit : limite **théorique** pour ce projet.", S("H")],
    ])

    d.h1("2. Volume, vélocité et variété")
    d.table(["Dimension", "Constat dans le kit", "Conséquence"], [
        ["**Volume**", f"{mo(total)} sur {nb_dat + nb_csv} fichiers ; {fmt(nb_lignes)} lignes ; la navigation web seule pèse {mo(clics)} ({fmt(n_clics)} lignes).",
         "Volume **modeste** : un Data Warehouse classique ou une seule machine le supporte. Le volume ne justifie pas à lui seul un Data Lake. " + S("D")],
        ["**Vélocité**", "Fichiers fournis en lots ; `data_refresh` couvre 19 jours supplémentaires ; stocks relevés une fois par semaine ; aucun flux continu.",
         "Traitement par lots suffisant. Un flux continu n'est pas justifié par les données observées. " + S("D")],
        ["**Variété**", "Tables relationnelles, journal de clics, texte libre dans les avis, 2 petits fichiers CSV d'audit. Aucun fichier JSON, image ou son.",
         "Variété **faible à moyenne** : le texte libre et le journal de clics sont les deux éléments qui s'écartent du modèle relationnel. " + S("V")],
    ])
    d.box("Point de méthode", "Ce kit ne ressemble pas à un cas de Big Data par son volume ou sa vélocité. L'argument pour un "
          "Data Lake est ici surtout la **conservation du brut**, la **variété des usages** et la **croissance possible**, pas "
          "la taille actuelle. C'est une évaluation honnête, pas une surenchère technologique.", "warn")

    d.h1("3. Classement des données observées")
    d.p("Le classement se fait sur le **contenu** des fichiers et non sur leur extension : un fichier qui exporte une table "
        "relationnelle reste **structuré**, même au format CSV ou texte délimité.")
    d.table(["Données", "Fichiers", "Classe", "Justification tirée des fichiers"], [
        ["Tables de ventes, retours, stocks, clients, produits, magasins, dates, promotions...", f"{nb_dat - nb_autres} `.dat`", "**Structuré**",
         "Lignes délimitées par `|`, nombre de champs identique à chaque ligne pour les 34 fichiers, colonnes typables (entiers, décimaux, dates), clés qui se rejoignent. " + S("V")],
        ["Journal de navigation web", "`web_clickstreams` (2 fichiers)", "**Structuré**",
         "Même format tabulaire à 6 colonnes (date, heure, produit, page, utilisateur, vente). Il a l'aspect d'un journal d'événements, mais son contenu est tabulaire : ce n'est pas du semi-structuré. " + S("V")],
        ["Prix des concurrents", "`item_marketprices` (2 fichiers)", "**Structuré**", "Table tabulaire de prix par produit et concurrent. " + S("V")],
        ["Audit des prix concurrents", "`item_marketprices_audit.csv` (2 fichiers)", "**Structuré**",
         "CSV avec en-tête et colonnes définies (une ligne de statistiques, puis une liste d'identifiants) : tabulaire, donc structuré. " + S("V")],
        ["Avis clients (texte)", "`product_reviews` (colonne `pr_review_content`)", "**Non structuré** (colonne)",
         f"Le fichier est tabulaire, mais la colonne de contenu est du texte libre (en moyenne environ 580 caractères, jusqu'à plus de 5 700). Seule cette colonne est non structurée. " + S("V")],
        ["JSON, XML, images, sons", "aucun", "**Semi-structuré / non structuré**", "**Aucun fichier de ce type** dans le kit : aucune donnée n'a été classée semi-structurée. " + S("N")],
    ])
    d.p(f"En volume, les {nb_dat} fichiers `.dat` sont **tous tabulaires** ; la seule donnée non structurée est une colonne de texte "
        f"(au plus {mo(avis)}, soit {pct(avis / total * 100, 1)} du volume total). " + S("D"))

    d.h1("4. Quand un Data Lake complète le Data Warehouse")
    d.table(["Situation", "Pourquoi le Data Warehouse seul est limité", "Apport du Data Lake", "Pertinence ici"], [
        ["Conserver le brut tel que reçu", "On ne garde que le résultat de la transformation", "Rejouer un traitement si la règle de nettoyage change", "**Forte** (doublons de clés à arbitrer) " + S("D")],
        ["Analyser le texte des avis", "Pas de traitement du texte natif", "Stockage du texte brut et traitements dédiés (Spark, Python)", "Moyenne : besoin non exprimé (Q15 partielle) " + S("H")],
        ["Ajouter de nouvelles sources (JSON, météo, logistique)", "Schéma à définir avant chargement", "Dépôt en l'état puis structuration à la demande", "Possible : aucune source de ce type fournie " + S("H")],
        ["Croissance du volume ou de la fréquence de refresh", "Coût et rigidité d'un entrepôt dimensionné à l'avance", "Stockage et calcul séparés, montée en charge progressive", "Faible aujourd'hui (~1 Go) " + S("D")],
        ["Exploration par la Data Science", "Accès limité à des tables déjà modélisées", "Accès aux données détaillées par zone", "Moyenne " + S("H")],
    ])

    d.h1("5. Risques de qualité, gouvernance, sécurité et coûts")
    qd = qual("store_sales", "Doublons")["nb_concernes"]
    d.table(["Axe", "Risque d'un Data Lake mal maîtrisé", "Ce qu'on observe dans le kit", "Parade"], [
        ["Qualité", "Des données brutes de mauvaise qualité alimentent directement les analyses", f"{fmt(qd)} doublons de clé en magasin ; prix sous le coût d'achat ; dates de fermeture de magasins incohérentes", "Zones Bronze / Silver / Gold et contrôles entre zones"],
        ["Gouvernance", "*Data Swamp* : on ne sait plus ce que contiennent les fichiers", "Aucun dictionnaire ; noms de colonnes déduits", "Catalogue, manifeste de lot, documentation par table"],
        ["Sécurité", "Accès trop larges aux données brutes", f"`customer` : {fmt(lignes('customer'))} lignes avec nom, e-mail et naissance (données synthétiques)", "Droits par zone, masquage des colonnes personnelles"],
        ["Coûts", "Stockage sans rétention, petits fichiers, sorties réseau", f"Peu de fichiers aujourd'hui ({nb_dat + nb_csv}) ; refresh à surveiller", "Rétention, compactage, suivi des volumes"],
    ])

    d.h1("6. Évolution proposée de l'architecture")
    d.p("Pour ce projet, l'évolution cohérente consiste à **garder la couche d'analyse en modèle relationnel** (étoile) et "
        "à y ajouter une **zone de stockage du brut** qui l'alimente. C'est ce que décrit l'architecture logique de l'UC-02.")
    d.table(["Étape", "Évolution", "Condition de déclenchement"], [
        ["Socle", "Data Lake en zones Bronze / Silver / Gold, zone Gold modélisée en étoile", "Situation actuelle de la conception (UC-02)"],
        ["Texte", "Analyse des avis à partir du texte brut conservé en Silver", "Besoin métier confirmé sur les avis (Q15)"],
        ["Mises à jour", "Format de table transactionnel (Delta Lake), **facultatif**", "Refresh fréquent avec corrections ou suppressions"],
        ["Temps réel", "Traitement continu des clics", "Besoin de réaction en quelques secondes, non exprimé aujourd'hui"],
    ])
    d.h2("Limites de cette analyse")
    d.ul([
        "Il s'agit d'un raisonnement sur les fichiers fournis : aucun entrepôt ni lac n'a été déployé ni mesuré. " + S("V"),
        "Le jeu de données est synthétique et de petite taille : les seuils de passage à une autre architecture ne sont pas démontrés. " + S("V"),
        "Les besoins de vélocité et de variété sont ceux de l'UC-01 ; ils changeraient si de nouvelles sources apparaissaient. " + S("H"),
    ])
    d.save_pdf(OUT / "UC-C2_limites_BI_et_evolutions.pdf")
    print("écrit UC-C2_limites_BI_et_evolutions.pdf")


if __name__ == "__main__":
    check_chrome()
    build()
