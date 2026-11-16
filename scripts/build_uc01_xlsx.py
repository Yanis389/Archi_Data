#!/usr/bin/env python3
"""Génère les deux classeurs Excel de l'UC-01 à partir des preuves :
  - UC01_dictionnaire_KPI.xlsx
  - UC01_inventaire_sources.xlsx
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preuves import (P, ROOT, col, couverture, domaines, fmt, kpi, lignes, mo, pct,  # noqa: E402
                     relations_resume, serie, total_octets)

OUT = ROOT / "01_UC01_besoin_exploration"
BLEU, TEAL = "1B3A57", "1A8F8F"
THIN = Side(style="thin", color="C9D3DA")
BORD = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
STATUT_FILL = {"V": "DDF1E5", "D": "E0ECF7", "H": "FBEFC9", "N": "F6DCDC", "A": "EADDF5"}


def entete(ws, headers, row=1):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=BLEU)
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = BORD


def ecrire(ws, rows, start=2, wrap=True):
    for r, row in enumerate(rows, start):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.alignment = Alignment(wrap_text=wrap, vertical="top")
            cell.border = BORD


def largeurs(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def titre(ws, texte, sous=None, ncols=8):
    ws["A1"] = texte
    ws["A1"].font = Font(bold=True, size=14, color=BLEU)
    if sous:
        ws["A2"] = sous
        ws["A2"].font = Font(italic=True, color="5B6770")
        ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
        ws.row_dimensions[2].height = 44


def colorer_statut(ws, colonne, start, end, mapping):
    for r in range(start, end + 1):
        cell = ws.cell(row=r, column=colonne)
        for prefixe, couleur in mapping.items():
            if str(cell.value or "").startswith(prefixe):
                cell.fill = PatternFill("solid", fgColor=couleur)
                cell.font = Font(bold=True)
                break


# =============================================================================== KPI
def build_kpi():
    ca_m, ca_w = kpi("Chiffre d'affaires", "Magasin"), kpi("Chiffre d'affaires", "Web")
    tick, cmd = kpi("Nombre de transactions", "Magasin"), kpi("Nombre de transactions", "Web")
    cats_m = [c for c in P["kpi_categories"] if c["canal"] == "Magasin"]
    stores = P["kpi_magasins"]
    s04m, s05m = serie("Magasin", "data", 2004), serie("Magasin", "data", 2005)
    s05mr = serie("Magasin", "data + data_refresh", 2005)
    inv_vide = [q for q in P["qualite"] if q["table"] == "inventory" and "vide" in q["controle"]][0]
    ligne_perte_m = [q for q in P["qualite"] if q["table"] == "store_sales" and "perte" in q["controle"]][0]
    sous_cout_m = [q for q in P["qualite"] if q["table"] == "store_sales" and "inférieur au coût" in q["controle"]][0]
    ret_ok = [q for q in P["relations"] if q["table_enfant"] == "store_returns" and q["source"] == "data"
              and "+" in q["colonne_enfant"]][0]
    clics_anon = [q for q in P["qualite"] if "anonymes" in q["controle"]][0]
    pr_sans_txt = [q for q in P["qualite"] if q["table"] == "product_reviews" and "sans texte" in q["controle"]][0]

    # (nom, definition, formule, unite, perimetre, frequence, sources, manquantes, limites, calculabilite,
    #  valeur_test, priorite, utilisateurs)
    K = [
        ("Chiffre d'affaires magasin",
         "Montant net encaissé sur les ventes en magasin, hors taxe, après remises.",
         "SUM(ss_net_paid)", "Devise non précisée",
         "Table store_sales ; tous magasins ; toutes dates ; une ligne = un article d'un ticket.",
         "Quotidien (agrégé au mois / trimestre / année)", "store_sales ; date_dim ; store",
         "Devise et taux de change non fournis. Taxe exclue (ss_net_paid_inc_tax existe mais non retenue).",
         f"Données synthétiques : ordres de grandeur non comparables à une enseigne réelle. {fmt(qual_store_dup())} "
         "lignes dupliquées sur (ticket, produit) : sans effet sur la somme mais à connaître.",
         "Calculable (vérifié)", f"{fmt(ca_m, 2)}", "Indispensable",
         "Direction générale ; Direction commerciale ; Contrôle de gestion"),
        ("Chiffre d'affaires web",
         "Montant net payé sur les commandes web, hors taxe et hors frais de port.",
         "SUM(ws_net_paid)", "Devise non précisée",
         "Table web_sales ; tous sites ; toutes dates ; une ligne = un article d'une commande.",
         "Quotidien (agrégé au mois / trimestre / année)", "web_sales ; date_dim ; web_site",
         "Devise non fournie. Frais de port disponibles à part (ws_net_paid_inc_ship).",
         "Vente web et vente magasin ne sont pas nécessairement modélisées de la même façon : "
         "leur somme suppose des définitions de « net payé » comparables (Hypothèse).",
         "Calculable (vérifié)", f"{fmt(ca_w, 2)}", "Indispensable",
         "Direction générale ; Direction commerciale ; Contrôle de gestion"),
        ("Chiffre d'affaires total (omnicanal)",
         "Somme du CA magasin et du CA web sur une même période.",
         "CA magasin + CA web", "Devise non précisée",
         "Magasin + web ; périodes identiques.", "Mensuel", "store_sales ; web_sales ; date_dim",
         "Canal catalogue absent du kit (voir inventaire des sources).",
         "Additionne deux canaux aux grains comparables mais non garantis identiques (Hypothèse). "
         "Le canal catalogue de TPC-DS n'est pas fourni : le total n'est pas exhaustif si l'enseigne en a un.",
         "Calculable avec réserves", f"{fmt(ca_m + ca_w, 2)}", "Indispensable",
         "Direction générale"),
        ("Nombre de transactions",
         "Nombre de tickets de caisse (magasin) ou de commandes (web) distincts.",
         "COUNT(DISTINCT ss_ticket_number) ; COUNT(DISTINCT ws_order_number)", "Transactions",
         "Un ticket / une commande regroupe plusieurs lignes de vente.", "Quotidien",
         "store_sales ; web_sales",
         "-",
         f"Une ligne de vente n'est pas une transaction. Valeur identique ({fmt(tick)}) pour les deux canaux : "
         "artefact probable du générateur, à ne pas lire comme un fait commercial (Hypothèse).",
         "Calculable (vérifié)", f"Magasin {fmt(tick)} ; Web {fmt(cmd)}", "Indispensable",
         "Direction commerciale ; Responsable de magasin"),
        ("Panier moyen",
         "Chiffre d'affaires moyen par transaction.",
         "SUM(net_paid) / COUNT(DISTINCT ticket ou commande)", "Devise / transaction",
         "Par canal ; peut être décliné par magasin, période, catégorie.", "Quotidien / mensuel",
         "store_sales ; web_sales", "-",
         f"Valeurs très élevées ({fmt(kpi('Panier moyen', 'Magasin'), 0)} en magasin) car environ "
         f"{fmt(kpi('Quantités vendues', 'Magasin') / lignes('store_sales'), 0)} unités par ligne : "
         "profil synthétique non réaliste pour du retail (Déduit).",
         "Calculable avec réserves",
         f"Magasin {fmt(kpi('Panier moyen', 'Magasin'), 2)} ; Web {fmt(kpi('Panier moyen', 'Web'), 2)}",
         "Indispensable", "Direction commerciale ; Responsable de magasin"),
        ("Quantités vendues",
         "Nombre total d'unités vendues.", "SUM(ss_quantity) ; SUM(ws_quantity)", "Unités",
         "Par canal, produit, catégorie, magasin, période.", "Quotidien",
         "store_sales ; web_sales ; item", "-",
         "Unités non comparables entre catégories très différentes (Music, Books, Electronics).",
         "Calculable (vérifié)",
         f"Magasin {fmt(kpi('Quantités vendues', 'Magasin'))} ; Web {fmt(kpi('Quantités vendues', 'Web'))}",
         "Indispensable", "Direction commerciale ; Responsable des stocks"),
        ("Évolution du CA (variation annuelle)",
         "Variation relative du CA entre deux années consécutives.",
         "(CA année N / CA année N-1) - 1", "%",
         "Par canal, sur des périodes de même durée.", "Annuel / mensuel",
         "store_sales ; web_sales ; date_dim ; data_refresh",
         "L'année 2005 est incomplète dans data seul.",
         f"Dans data seul, 2005 ne couvre que {s05m['jours_distincts']} jours sur 365 : le CA 2005 magasin "
         f"({fmt(s05m['chiffre_affaires'], 0)}) paraît baisser de "
         f"{fmt(100 * (1 - s05m['chiffre_affaires'] / s04m['chiffre_affaires']), 1)} % à tort. Avec data_refresh : "
         f"{s05mr['jours_distincts']} jours, {fmt(s05mr['chiffre_affaires'], 0)} (Vérifié).",
         "Calculable avec réserves",
         f"Magasin 2005 : {fmt(100 * (s05mr['chiffre_affaires'] / s04m['chiffre_affaires'] - 1), 2)} % "
         "(data + data_refresh)", "Indispensable", "Direction générale ; Contrôle de gestion"),
        ("Taux de remise",
         "Part du prix catalogue abandonnée en remises.",
         "SUM(ext_discount_amt) / SUM(ext_list_price)", "%", "Par canal ; par produit ou promotion.",
         "Mensuel", "store_sales ; web_sales ; promotion", "-",
         f"Environ 50 % dans les deux canaux : valeur trop régulière et trop élevée pour du réel, qui traduit "
         "le mode de génération (Hypothèse). Calculable mais non interprétable commercialement.",
         "Calculable avec réserves",
         f"Magasin {fmt(kpi('Taux de remise', 'Magasin'), 2)} % ; Web {fmt(kpi('Taux de remise', 'Web'), 2)} %",
         "Utile", "Direction commerciale ; Contrôle de gestion"),
        ("Marge nette",
         "Résultat net de la ligne : net payé moins coût d'achat.", "SUM(ss_net_profit) ; SUM(ws_net_profit)",
         "Devise non précisée", "Par canal, produit, catégorie.", "Mensuel",
         "store_sales ; web_sales ; item", "Coûts de structure (personnel, loyers) absents.",
         f"{pct(ligne_perte_m['pct'], 1)} des lignes magasin sont en perte et le prix de vente unitaire est "
         f"inférieur au coût d'achat sur {pct(sous_cout_m['pct'], 1)} d'entre elles. Un KPI de marge calculé "
         "ici serait trompeur.",
         "Non fiable en l'état",
         f"Magasin {fmt(kpi('Marge nette', 'Magasin'), 0)} ; Web {fmt(kpi('Marge nette', 'Web'), 0)}",
         "Utile", "Contrôle de gestion ; Direction générale"),
        ("Taux de retour en quantité",
         "Part des unités vendues qui sont retournées.",
         "SUM(sr_return_quantity) / SUM(ss_quantity) ; idem web", "%",
         "Par canal ; rapprochement retour -> vente par (ticket, produit).", "Mensuel",
         "store_returns ; web_returns ; store_sales ; web_sales ; reason",
         "Date de vente d'origine non portée par le retour (à retrouver par jointure).",
         f"Les retours sont datés jusqu'en {couverture('store_returns')['date_max'][:4]} / "
         f"{couverture('web_returns')['date_max'][:4]} alors que les ventes s'arrêtent en 2005 : un taux calculé "
         f"par mois de retour n'est pas comparable à un taux par mois de vente. {ret_ok['lignes_orphelines']} "
         "retour(s) sans vente d'origine dans data.",
         "Calculable (vérifié)",
         f"Magasin {fmt(kpi('Taux de retour en quantité', 'Magasin'), 2)} % ; "
         f"Web {fmt(kpi('Taux de retour en quantité', 'Web'), 2)} %", "Indispensable",
         "Direction commerciale ; Responsable de magasin"),
        ("Montant retourné",
         "Valeur remboursée aux clients au titre des retours (hors taxe).",
         "SUM(sr_return_amt) ; SUM(wr_return_amt)", "Devise non précisée",
         "Par canal, produit, motif.", "Mensuel", "store_returns ; web_returns ; reason", "-",
         "Les retours doivent être distingués des ventes : ne pas les déduire sans règle de rattachement.",
         "Calculable (vérifié)",
         f"Magasin {fmt(kpi('Montant retourné', 'Magasin'), 0)} ; Web {fmt(kpi('Montant retourné', 'Web'), 0)}",
         "Utile", "Direction commerciale ; Contrôle de gestion"),
        ("CA par catégorie de produit",
         "Chiffre d'affaires ventilé par catégorie, et part dans le total.",
         "SUM(net_paid) GROUP BY i_category", "Devise / %",
         "Par canal ; 9 catégories dans item.", "Mensuel", "store_sales ; web_sales ; item",
         "Hiérarchie produit limitée à catégorie / classe / marque.",
         "Concentration forte sur Music et Books (voir valeur de test) : une catégorie peut masquer les autres.",
         "Calculable (vérifié)",
         f"{cats_m[0]['categorie']} {fmt(cats_m[0]['part_ca_pct'], 1)} % ; {cats_m[1]['categorie']} "
         f"{fmt(cats_m[1]['part_ca_pct'], 1)} % (magasin)", "Indispensable",
         "Direction commerciale"),
        ("CA par magasin",
         "Chiffre d'affaires de chaque point de vente.", "SUM(ss_net_paid) GROUP BY ss_store_sk", "Devise non précisée",
         f"{len(stores)} magasins.", "Quotidien / mensuel", "store_sales ; store ; date_dim",
         "Surface et effectif existent dans store mais n'ont pas été contrôlés.",
         "Magasins très proches en CA (écart max. de "
         f"{fmt(100 * (stores[0]['chiffre_affaires'] / stores[-1]['chiffre_affaires'] - 1), 1)} %) : "
         "peu de différenciation, jeu synthétique. Les dates de fermeture sont incohérentes (voir limites).",
         "Calculable (vérifié)",
         f"Du {fmt(stores[-1]['chiffre_affaires'], 0)} ({stores[-1]['nom']}) au "
         f"{fmt(stores[0]['chiffre_affaires'], 0)} ({stores[0]['nom']})", "Indispensable",
         "Responsable de magasin ; Direction commerciale"),
        ("Stock moyen par relevé",
         "Quantité moyenne en stock par produit, entrepôt et date de relevé.", "AVG(inv_quantity_on_hand)",
         "Unités", "Par entrepôt (5), produit, date de relevé.", "Hebdomadaire (grain des relevés)",
         "inventory ; item ; warehouse ; date_dim",
         f"{fmt(inv_vide['nb_concernes'])} relevés sans quantité.",
         "Le stock est un instantané hebdomadaire, pas un mouvement : on ne peut pas reconstituer les "
         "entrées/sorties. Les relevés vides sont à distinguer d'un stock nul (Hypothèse).",
         "Calculable (vérifié)", f"{fmt(kpi('Stock moyen par relevé', 'Entrepôts'), 2)} unités",
         "Utile", "Responsable des stocks"),
        ("Taux de rupture de stock",
         "Part des relevés où le stock d'un produit est nul.",
         "COUNT(inv_quantity_on_hand = 0) / COUNT(inv_quantity_on_hand)", "%",
         "Par entrepôt, produit, semaine.", "Hebdomadaire", "inventory ; item ; warehouse", "Demande non servie.",
         "Une rupture mesurée sur des relevés hebdomadaires sous-estime les ruptures intra-semaine.",
         "Calculable (vérifié)", f"{fmt(kpi('Part des relevés de stock à zéro (rupture)', 'Entrepôts'), 3)} %",
         "Utile", "Responsable des stocks"),
        ("Taux de conversion clic -> commande",
         "Part des clics qui sont rattachés à une commande web.",
         "COUNT(wcs_sales_sk) / COUNT(*)", "%", "Clics de web_clickstreams.", "Quotidien",
         "web_clickstreams ; web_sales ; web_page",
         "Ajouts au panier, sessions et canal d'acquisition absents.",
         f"Un clic n'est pas un achat ni un ajout au panier. {pct(clics_anon['pct'], 1)} des clics sont "
         "anonymes (pas de client) : analyse par client impossible sur cette part (Vérifié).",
         "Calculable avec réserves", f"{fmt(kpi('Part des clics aboutissant à une commande', 'Web'), 2)} %",
         "Utile", "Direction commerciale ; Équipe Data"),
        ("Note moyenne des avis",
         "Moyenne des notes laissées par les clients sur les produits.", "AVG(pr_review_rating)", "Note sur 5",
         "Par produit, catégorie, période.", "Mensuel", "product_reviews ; item",
         "Pas de lien direct note -> retour sans analyse de texte.",
         f"Contenu textuel libre non structuré ({pr_sans_txt['nb_concernes']} avis sans texte) : exploitation "
         "du texte hors périmètre du Jour 1. Une corrélation note/ventes ne prouve pas une causalité.",
         "Calculable (vérifié)", f"{fmt(kpi('Note moyenne des avis', 'Web'), 2)} / 5", "Complémentaire",
         "Direction commerciale ; Équipe Data"),
        ("Écart de prix vs concurrents",
         "Écart relatif entre le prix concurrent constaté et le prix courant du produit.",
         "MEDIAN(imp_competitor_price / i_current_price) - 1", "%", "Par produit, catégorie.", "Hebdomadaire",
         "item_marketprices ; item", "Identité des concurrents (code seulement).",
         f"La moyenne ({fmt(kpi('Écart moyen du prix concurrent vs prix courant', 'Prix'), 1)} %) est tirée par "
         "des valeurs extrêmes : la médiane est le bon indicateur (Vérifié).",
         "Calculable avec réserves",
         f"Médiane {fmt(kpi('Écart médian du prix concurrent vs prix courant', 'Prix'), 2)} %", "Complémentaire",
         "Direction commerciale"),
        ("Clients acheteurs distincts",
         "Nombre de clients ayant réalisé au moins un achat.",
         "COUNT(DISTINCT ss_customer_sk) ; COUNT(DISTINCT ws_bill_customer_sk)", "Clients",
         "Par canal, période.", "Mensuel", "store_sales ; web_sales ; customer", "Identifiant unique cross-canal.",
         "Rien ne garantit qu'un client magasin et un client web soient le même individu au-delà de la clé "
         "customer (Hypothèse).",
         "Calculable (vérifié)",
         f"Magasin {fmt(kpi('Clients distincts acheteurs', 'Magasin'))} ; Web "
         f"{fmt(kpi('Clients distincts acheteurs', 'Web'))} sur {fmt(lignes('customer'))} clients",
         "Utile", "Direction commerciale ; Équipe Data"),
    ]

    wb = Workbook()
    # --- légende
    ws = wb.active
    ws.title = "Lisez-moi"
    titre(ws, "Dictionnaire initial des KPI - Retail Intelligence (TP J1, UC-01)",
          "Chaque KPI est défini (formule, unité, périmètre, fréquence, sources, données manquantes, limites) "
          "et testé sur les fichiers réels : la valeur de test provient de preuves/kpi_tests.csv, produite par "
          "scripts/profiler_tpcx_bb.py. Les noms de colonnes sont déduits de TPC-DS/BigBench (aucun "
          "dictionnaire n'est fourni dans le kit).", ncols=4)
    legende = [
        ("Calculable (vérifié)", "La formule a été exécutée sur les fichiers réels et les jointures nécessaires "
                                  "ont été contrôlées (0 orphelin).", "V"),
        ("Calculable avec réserves", "La valeur est calculable mais son interprétation est limitée "
                                      "(périmètre partiel, définition à valider, valeur peu réaliste).", "H"),
        ("Non fiable en l'état", "Le calcul est possible mais le résultat serait trompeur avec ces données.", "N"),
    ]
    entete(ws, ["Statut de calculabilité", "Signification", ""], row=4)
    for i, (a, b, k) in enumerate(legende, 5):
        ws.cell(row=i, column=1, value=a).fill = PatternFill("solid", fgColor=STATUT_FILL[k])
        ws.cell(row=i, column=1).font = Font(bold=True)
        ws.cell(row=i, column=2, value=b).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 32
    ws.cell(row=9, column=1, value="Priorité").font = Font(bold=True)
    ws.cell(row=9, column=2, value="Indispensable : sans lui le pilotage est impossible ; Utile : améliore l'analyse ; "
                                   "Complémentaire : à traiter si le temps le permet.").alignment = Alignment(wrap_text=True)
    ws.row_dimensions[9].height = 32
    ws.cell(row=11, column=1, value="Répartition").font = Font(bold=True)
    from collections import Counter
    rep = Counter(k[9] for k in K)
    ws.cell(row=11, column=2, value=" ; ".join(f"{v} {k.lower()}" for k, v in rep.items()))
    largeurs(ws, [28, 90, 4, 4])

    # --- dictionnaire
    ws = wb.create_sheet("Dictionnaire KPI")
    heads = ["Nom du KPI", "Définition métier", "Formule", "Unité", "Périmètre", "Fréquence de calcul",
             "Sources nécessaires", "Données manquantes", "Limites d'interprétation",
             "Calculabilité", "Valeur de test (preuve)", "Priorité", "Utilisateurs concernés"]
    entete(ws, heads)
    ecrire(ws, K)
    largeurs(ws, [28, 38, 36, 14, 34, 18, 28, 32, 60, 18, 34, 14, 28])
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(heads))}{len(K) + 1}"
    colorer_statut(ws, 10, 2, len(K) + 1, {"Calculable (v": STATUT_FILL["V"], "Calculable av": STATUT_FILL["H"],
                                            "Non fiable": STATUT_FILL["N"]})
    ws.row_dimensions[1].height = 30

    # --- valeurs de test
    ws = wb.create_sheet("Valeurs de test")
    entete(ws, ["KPI", "Canal", "Formule exécutée", "Valeur", "Unité"])
    ecrire(ws, [[k["kpi"], k["canal"], k["formule"], float(k["valeur"]) if k["valeur"] not in (None, "") else None,
                 k["unite"]] for k in P["kpi"]])
    for r in range(2, len(P["kpi"]) + 2):
        ws.cell(row=r, column=4).number_format = "#,##0.00"
    largeurs(ws, [44, 12, 60, 22, 22])
    ws.freeze_panes = "A2"

    r0 = len(P["kpi"]) + 4
    ws.cell(row=r0, column=1, value="Évolution annuelle du CA par canal").font = Font(bold=True, color=BLEU, size=12)
    entete(ws, ["Canal", "Périmètre", "Année", "CA net payé", "Jours distincts"], row=r0 + 1)
    rows = [[s["canal"], s["perimetre"], int(s["annee"]), float(s["chiffre_affaires"]), int(s["jours_distincts"])]
            for s in P["kpi_series"]]
    ecrire(ws, rows, start=r0 + 2)
    for r in range(r0 + 2, r0 + 2 + len(rows)):
        ws.cell(row=r, column=4).number_format = "#,##0.00"

    # --- dimensions
    ws = wb.create_sheet("Axes d'analyse")
    entete(ws, ["Canal", "Catégorie", "CA net payé", "Quantité", "Lignes", "Part du CA (%)"])
    ecrire(ws, [[c["canal"], c["categorie"], float(c["chiffre_affaires"]), float(c["quantite"]), int(c["lignes"]),
                 float(c["part_ca_pct"])] for c in P["kpi_categories"]])
    n = len(P["kpi_categories"])
    for r in range(2, n + 2):
        ws.cell(row=r, column=3).number_format = "#,##0.00"
        ws.cell(row=r, column=4).number_format = "#,##0"
    r0 = n + 4
    ws.cell(row=r0, column=1, value="CA par magasin (magasin)").font = Font(bold=True, color=BLEU, size=12)
    entete(ws, ["Magasin (sk)", "Nom", "État", "CA net payé", "Tickets"], row=r0 + 1)
    ecrire(ws, [[int(s["magasin_sk"]), s["nom"], s["etat"], float(s["chiffre_affaires"]), int(s["tickets"])]
                for s in P["kpi_magasins"]], start=r0 + 2)
    for r in range(r0 + 2, r0 + 2 + len(P["kpi_magasins"])):
        ws.cell(row=r, column=4).number_format = "#,##0.00"
    largeurs(ws, [14, 28, 18, 22, 14, 16])

    path = OUT / "UC01_dictionnaire_KPI.xlsx"
    wb.save(path)
    print("écrit", path.relative_to(ROOT), f"({len(K)} KPI)")


def qual_store_dup():
    return [q for q in P["qualite"] if q["table"] == "store_sales" and "Doublons" in q["controle"]][0]["nb_concernes"]


# =============================================================================== INVENTAIRE
def build_inventaire():
    wb = Workbook()
    ws = wb.active
    ws.title = "Synthèse"
    nb_dat = len([f for f in P["fichiers"] if f["format"] == "dat"])
    nb_csv = len([f for f in P["fichiers"] if f["format"] == "csv"])
    titre(ws, "Inventaire réel des sources TPCx-BB - Retail Intelligence (TP J1, UC-01)",
          f"{len(P['fichiers'])} fichiers observés ({nb_dat} .dat, {nb_csv} .csv), {mo(total_octets())}. "
          "Tout ce qui figure ici a été lu dans les fichiers (statut Vérifié) sauf les noms de colonnes "
          "(statut Déduit : aucun en-tête ni dictionnaire dans le kit).", ncols=7)
    # --- domaines
    from schemas import SCHEMAS
    doms = domaines()
    attendu_tp = ["Ventes magasin", "Ventes web", "Retours", "Produits et prix", "Clients", "Magasins et entrepôts",
                  "Stocks", "Navigation web"]
    ordre = attendu_tp + [d for d in doms if d not in attendu_tp]
    rows = []
    for d in ordre:
        tabs = doms[d]
        n_data = sum(lignes(t) for t in tabs)
        n_ref = sum(lignes(t, "data_refresh") for t in tabs if any(
            f["table"] == t and f["source"] == "data_refresh" for f in P["fichiers"]))
        refresh = [t for t in tabs if any(f["table"] == t and f["source"] == "data_refresh" for f in P["fichiers"])]
        rows.append([d, ", ".join(tabs), int(n_data), int(n_ref), ", ".join(refresh) or "-",
                     "Disponible (vérifié)"])
    entete(ws, ["Domaine", "Tables observées (data)", "Lignes (data)", "Lignes (data_refresh)",
                "Tables aussi dans data_refresh", "Statut"], row=4)
    ecrire(ws, rows, start=5)
    for r in range(5, 5 + len(rows)):
        ws.cell(row=r, column=3).number_format = "#,##0"
        ws.cell(row=r, column=4).number_format = "#,##0"
        ws.cell(row=r, column=6).fill = PatternFill("solid", fgColor=STATUT_FILL["V"])
    r = 5 + len(rows) + 1
    ws.cell(row=r, column=1, value="Domaines attendus mais absents du kit").font = Font(bold=True, color=BLEU, size=12)
    entete(ws, ["Domaine", "Tables attendues dans TPC-DS", "", "", "", "Statut"], row=r + 1)
    absents = [
        ["Ventes catalogue", "catalog_sales, catalog_returns, catalog_page", "", "", "", "Non disponible"],
        ["Centres d'appels", "call_center", "", "", "", "Non disponible"],
        ["Données complémentaires (JSON, météo, logistique, événements)", "aucun fichier de ce type dans retail_project/",
         "", "", "", "Non disponible (à confirmer avec le formateur)"],
        ["Dictionnaire de données / documentation du kit", "aucun fichier de ce type", "", "", "", "Non disponible"],
    ]
    ecrire(ws, absents, start=r + 2)
    for i in range(len(absents)):
        ws.cell(row=r + 2 + i, column=6).fill = PatternFill("solid", fgColor=STATUT_FILL["N"])
    largeurs(ws, [34, 60, 16, 20, 40, 34])
    ws.row_dimensions[4].height = 30

    # --- fichiers
    ws = wb.create_sheet("Fichiers")
    heads = ["Source", "Domaine", "Table", "Fichier", "Chemin relatif", "Format", "Délimiteur", "En-tête",
             "Taille (octets)", "Taille", "Lignes", "Colonnes observées", "Colonnes attendues (déduites)",
             "Schéma cohérent"]
    entete(ws, heads)
    rows = []
    for f in P["fichiers"]:
        rows.append([f["source"], f["domaine"], f["table"], f["fichier"], f["chemin_relatif"], f["format"],
                     f["delimiteur"], f["en_tete_present"], int(f["taille_octets"]), f["taille"],
                     int(f["lignes"]) if str(f["lignes"]).isdigit() else None,
                     f["colonnes_observees"] or None,
                     int(f["colonnes_attendues_deduites"]) if str(f["colonnes_attendues_deduites"]).isdigit() else None,
                     f["schema_coherent"] or None])
    ecrire(ws, rows, wrap=False)
    for r in range(2, len(rows) + 2):
        ws.cell(row=r, column=9).number_format = "#,##0"
        ws.cell(row=r, column=11).number_format = "#,##0"
    largeurs(ws, [14, 22, 24, 30, 46, 8, 11, 22, 16, 11, 14, 12, 16, 12])
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(heads))}{len(rows) + 1}"

    # --- colonnes
    ws = wb.create_sheet("Colonnes")
    heads = ["Source", "Domaine", "Table", "N°", "Colonne (déduite)", "Description (si documentée)",
             "Type observé", "Rôle", "Lignes", "Nulls", "% nulls", "Distincts", "Min", "Max", "Long. max",
             "Exemple"]
    entete(ws, heads)
    rows = [[c["source"], c["domaine"], c["table"], int(c["position"]), c["colonne"], c["description"],
             c["type_observe"], c["role"], int(c["nb_lignes"]), int(c["nb_nulls"]), float(c["pct_nulls"]),
             int(c["nb_distincts"]), c["min"], c["max"], int(c["longueur_max"]) if c["longueur_max"] not in (None, "") else None,
             c["exemple"]] for c in P["colonnes"]]
    ecrire(ws, rows, wrap=False)
    for r in range(2, len(rows) + 2):
        for cidx in (9, 10, 12):
            ws.cell(row=r, column=cidx).number_format = "#,##0"
        ws.cell(row=r, column=11).number_format = "0.000"
    largeurs(ws, [13, 20, 24, 5, 28, 40, 11, 28, 12, 12, 9, 12, 22, 22, 9, 34])
    ws.freeze_panes = "F2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(heads))}{len(rows) + 1}"

    # --- relations
    ws = wb.create_sheet("Relations")
    heads = ["Source", "Table enfant", "Colonne enfant", "Table parent", "Colonne parent", "Portée du parent",
             "Lignes", "Renseignées", "% nulls", "Valeurs distinctes (enfant)", "Lignes orphelines",
             "% orphelines", "Clé parent unique", "Verdict"]
    entete(ws, heads)
    rows = [[r["source"], r["table_enfant"], r["colonne_enfant"], r["table_parent"], r["colonne_parent"],
             r["portee_parent"], int(r["nb_lignes"]), int(r["nb_renseignees"]), float(r["pct_nulls"]),
             int(r["valeurs_distinctes_enfant"]) if str(r["valeurs_distinctes_enfant"]).isdigit() else None,
             int(r["lignes_orphelines"]), float(r["pct_orphelines"]), r["cle_parent_unique"], r["verdict"]]
            for r in P["relations"]]
    ecrire(ws, rows, wrap=False)
    for rr in range(2, len(rows) + 2):
        for cidx in (7, 8, 10, 11):
            ws.cell(row=rr, column=cidx).number_format = "#,##0"
        v = ws.cell(row=rr, column=14)
        v.fill = PatternFill("solid", fgColor=STATUT_FILL["V"] if v.value == "relation vérifiée" else STATUT_FILL["H"])
    largeurs(ws, [13, 20, 38, 22, 28, 18, 12, 12, 9, 16, 12, 11, 15, 30])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(heads))}{len(rows) + 1}"

    # --- qualité
    ws = wb.create_sheet("Qualité")
    entete(ws, ["Table", "Contrôle", "Nature", "Concernés", "Total", "%", "Interprétation"])
    rows = [[q["table"], q["controle"], q["nature"], int(q["nb_concernes"]), int(q["nb_total"]), float(q["pct"]),
             q["interpretation"]] for q in P["qualite"]]
    ecrire(ws, rows)
    for r in range(2, len(rows) + 2):
        ws.cell(row=r, column=4).number_format = "#,##0"
        ws.cell(row=r, column=5).number_format = "#,##0"
        ws.cell(row=r, column=6).number_format = "0.000"
    largeurs(ws, [20, 62, 12, 14, 14, 10, 70])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:G{len(rows) + 1}"

    # --- périodes
    ws = wb.create_sheet("Périodes")
    entete(ws, ["Source", "Table", "Colonne de date", "Date min", "Date max", "Jours distincts"])
    ecrire(ws, [[c["source"], c["table"], c["colonne_date"], c["date_min"], c["date_max"], int(c["jours_distincts"])]
                for c in P["couverture"]])
    largeurs(ws, [14, 22, 24, 14, 14, 16])
    r0 = len(P["couverture"]) + 4
    ws.cell(row=r0, column=1, value="data_refresh est-il un complément de data ? (recouvrement des clés)").font = \
        Font(bold=True, color=BLEU, size=12)
    entete(ws, ["Table", "Clé", "Lignes data", "Lignes refresh", "Clés refresh déjà dans data", "Clé max data",
                "Clé min refresh"], row=r0 + 1)
    ecrire(ws, [[c["table"], c.get("cle", ""), int(c["lignes_data"]), int(c["lignes_refresh"]),
                 int(c["cles_refresh_deja_presentes_dans_data"]) if c.get("cles_refresh_deja_presentes_dans_data", "") != "" else None,
                 c.get("max_cle_data") or None, c.get("min_cle_refresh") or None]
                for c in P["refresh"]], start=r0 + 2)
    path = OUT / "UC01_inventaire_sources.xlsx"
    wb.save(path)
    print("écrit", path.relative_to(ROOT), f"({len(P['fichiers'])} fichiers, {len(P['colonnes'])} colonnes)")


if __name__ == "__main__":
    build_kpi()
    build_inventaire()
