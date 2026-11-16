#!/usr/bin/env python3
"""Génère 03_complementaire/UC-C1_processus_decisionnel.pdf (partie complémentaire, facultative).

Processus décisionnel complet sur la question Q05 de l'UC-01 : produits retournés et motifs.
Les chiffres viennent de 03_complementaire/preuves/ (script profil_complementaire.py).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preuves import ROOT, fmt  # noqa: E402
from rapport import Doc, S, check_chrome, svg_wrap  # noqa: E402

OUT = ROOT / "03_complementaire"
PREUVES = OUT / "preuves"
MISSION = ("**Votre mission.** Consultant Data auprès de Retail Intelligence : approfondir un processus décisionnel "
           "complet, de la question métier à la mesure des effets de la décision. Ce document traite **UC-C1** "
           "(partie complémentaire, hors validation de UC-01 et UC-02).")


def lire(nom):
    with open(PREUVES / nom, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pc(x):
    return f"{float(x):.2f}".replace(".", ",") + " %"


def barres(lignes, titre):
    """Diagramme à barres horizontales : [(libellé, taux, couleur)] sur un axe 0-4 %."""
    w, h0, pas = 760, 34, 22
    h = h0 + pas * len(lignes) + 22
    x0, xmax = 230, 700
    ech = (xmax - x0) / 4.0
    s = [f'<text x="{x0}" y="16" font-size="10" font-weight="700" fill="#1b3a57">{titre}</text>']
    for t in (0, 1, 2, 3, 4):
        x = x0 + t * ech
        s.append(f'<line x1="{x}" y1="{h0 - 8}" x2="{x}" y2="{h - 20}" stroke="#d5dde3" stroke-width="0.6"/>'
                 f'<text x="{x}" y="{h - 8}" text-anchor="middle" font-size="8.5" fill="#5b6770">{t} %</text>')
    for i, (lib, val, coul) in enumerate(lignes):
        y = h0 + i * pas
        s.append(f'<text x="{x0 - 8}" y="{y + 11}" text-anchor="end" font-size="9.5" fill="#1b2a38">{lib}</text>'
                 f'<rect x="{x0}" y="{y}" width="{val * ech:.1f}" height="14" rx="2" fill="{coul}"/>'
                 f'<text x="{x0 + val * ech + 5:.1f}" y="{y + 11}" font-size="9" fill="#1b2a38">{pc(val)}</text>')
    return svg_wrap(w, h, "".join(s))


def build() -> None:
    syn = json.loads((PREUVES / "retours_synthese.json").read_text(encoding="utf-8"))
    cats = lire("retours_par_categorie.csv")
    motifs = lire("retours_par_motif.csv")
    ctrl = lire("controles_retours.csv")
    mag = next(c for c in syn["canaux"] if c["canal"] == "magasin")
    web = next(c for c in syn["canaux"] if c["canal"] == "web")
    tot_q = mag["qte_retournee"] + web["qte_retournee"]
    par_cat = {}
    for r in cats:
        par_cat[r["categorie"]] = par_cat.get(r["categorie"], 0) + int(r["qte_retournee"])
    top = sorted(par_cat.items(), key=lambda kv: -kv[1])
    part2 = sum(v for _, v in top[:2]) / tot_q * 100
    tmin = min(float(r["taux_retour_pct"]) for r in cats)
    tmax = max(float(r["taux_retour_pct"]) for r in cats)

    d = Doc("Processus décisionnel : les retours produits",
            "De la question métier à la mesure des effets (question Q05)",
            "UC-C1 - Approfondir le processus décisionnel", MISSION)

    d.h1("1. Question métier retenue")
    d.p("La question retenue est **Q05** de l'UC-01 : *« Quels produits font l'objet de retours, et pour quel motif ? »*. "
        "Elle appartient à la Direction commerciale (priorité **indispensable**, faisabilité **partielle** dans l'UC-01). "
        "Elle a été choisie parce qu'elle relie une décision concrète (agir auprès des fournisseurs) à des données "
        "présentes dans le kit, tout en exposant une limite de données qu'il faut traiter honnêtement.")

    d.h1("2. Problème initial")
    d.p("La Direction commerciale veut réduire le coût des retours et traiter les problèmes de qualité produit. Elle ne sait "
        "pas aujourd'hui **où** se concentrent les retours ni **pourquoi** les clients retournent. Sans cela, une action "
        "fournisseur serait lancée sans cible.")
    d.box("Question de décision", "Sur quels produits ou catégories faut-il concentrer l'effort de réduction des retours, et "
          "à partir de quelle information (catégorie, canal, motif) peut-on le justifier ?")

    d.h1("3. Indicateurs nécessaires")
    d.table(["Indicateur", "Définition", "Usage dans la décision"], [
        ["Taux de retour (quantité)", "Quantité retournée / quantité vendue, par catégorie et par canal", "Repérer les catégories où l'on retourne proportionnellement plus"],
        ["Quantité retournée", "Somme des quantités de retour", "Mesurer le volume à traiter, indépendamment du taux"],
        ["Part par motif", "Lignes de retour d'un motif / total des lignes de retour", "Identifier la cause dominante"],
        ["Montant retourné", "Somme des montants de retour", "Chiffrer l'enjeu financier"],
    ])
    d.p("Les définitions détaillées sont dans `UC01_dictionnaire_KPI.xlsx`. Le montant retourné n'est pas exploité ici : "
        "la marge n'étant pas fiable dans les données (UC-01), un enjeu financier ne serait pas fiable non plus. " + S("D"))

    d.h1("4. Sources mobilisées")
    d.table(["Table", "Rôle", "Remarque"], [
        ["`store_returns`, `web_returns`", "Lignes de retour (produit, motif, quantité)", "data + data_refresh"],
        ["`store_sales`, `web_sales`", "Dénominateur du taux (quantité vendue)", "data + data_refresh"],
        ["`item`", "Catégorie du produit", "Le référentiel initial est complété par `data_refresh/item`"],
        ["`reason`", "Libellé du motif", "35 motifs ; libellés non exploitables (voir §6)"],
    ])
    d.p("Périmètre : `data` et `data_refresh` réunis, car leurs clés sont disjointes (UC-01). Les chiffres ci-dessous sont produits "
        "par `scripts/profil_complementaire.py` et écrits dans `03_complementaire/preuves/`. " + S("V"))

    d.h1("5. Contrôles de qualité à effectuer")
    noms = {"retours sans motif": "Motif renseigné", "retours dont le motif n'existe pas dans reason": "Motif présent dans `reason`",
            "retours dont le produit est absent du référentiel item": "Produit présent dans `item`",
            "retours sans catégorie renseignée": "Catégorie renseignée", "quantité de retour <= 0": "Quantité de retour strictement positive"}
    d.table(["Contrôle", "Lignes en défaut", "Total de lignes de retour", "%"],
            [[noms[r["controle"]], fmt(int(r["lignes_concernees"])), fmt(int(r["total_lignes"])), pc(r["pct"])] for r in ctrl],
            num_cols=(1, 2, 3))
    sans_motif = fmt(int(ctrl[0]["lignes_concernees"]))
    d.p(f"Les contrôles de jointure sont indispensables : sans la clé produit vers `item`, un retour ne peut pas être "
        f"rattaché à une catégorie. Ici, ils ne révèlent aucun orphelin ; {sans_motif} retours seulement n'ont pas de motif. " + S("V"))

    d.h1("6. Ce que les données montrent")
    d.kpis([(pc(mag["taux_retour_pct"]), "taux de retour magasin"), (pc(web["taux_retour_pct"]), "taux de retour web"),
            (fmt(syn["total_lignes_retour"]).replace("\u202f", " "), "lignes de retour"), (str(syn["nb_motifs"]), "motifs distincts")])
    lignes = [(r["categorie"], float(r["taux_retour_pct"]), "#2c6fb0") for r in cats if r["canal"] == "magasin"]
    d.figure(barres(lignes, "Taux de retour par catégorie - magasin (quantité retournée / quantité vendue)"),
             "Figure 1 - Les taux par catégorie sont très proches.")
    d.ul([
        f"**Taux de retour par catégorie** : entre {pc(tmin)} et {pc(tmax)} selon la catégorie et le canal, soit moins d'un point "
        f"d'écart. Aucune catégorie ne se détache nettement. " + S("V"),
        f"**Motifs** : les {syn['nb_motifs']} motifs représentent chacun entre {pc(syn['part_motif_min_pct'])} et "
        f"{pc(syn['part_motif_max_pct'])} des retours, soit un rapport de {str(syn['ecart_relatif_max_min']).replace('.', ',')} entre le "
        f"plus fréquent et le moins fréquent : la répartition est quasi uniforme. " + S("V"),
        f"**Libellés des motifs** : ce sont des phrases génériques sans signification (exemple : « {syn['exemple_libelles_motifs'][0]} »). "
        "Ils ne permettent pas de qualifier une cause. " + S("V"),
        f"**Volume** : {top[0][0]} et {top[1][0]} concentrent {pc(part2)} des quantités retournées, parce qu'elles pèsent le "
        "plus dans les ventes, et non parce qu'on y retourne davantage. " + S("D"),
    ])

    d.h1("7. Restitution adaptée à l'utilisateur")
    d.p("Utilisateur : **Direction commerciale**, non technicienne, qui arbitre des actions fournisseur.")
    d.table(["Élément de restitution", "Contenu", "Pourquoi"], [
        ["Un indicateur d'ensemble", "Taux de retour magasin et web, évolution dans le temps", "Savoir si le niveau global est stable"],
        ["Un classement des catégories", "Taux et quantité retournée côte à côte, avec l'écart au taux moyen", "Ne pas confondre fort volume et fort taux"],
        ["Un encart de fiabilité", "Les motifs ne sont pas lisibles ; l'écart entre catégories est faible", "Éviter une décision sur un écart non significatif"],
        ["Un filtre canal", "Magasin / web", "Les catégories à risque diffèrent selon le canal"],
    ])

    d.h1("8. Décision ou action possible")
    d.box("Ce que les données permettent de décider",
          "Avec ces données, **aucune action ciblée sur une catégorie ou un motif n'est justifiée** : les écarts sont trop "
          "faibles. Une décision défendable est de **ne pas lancer d'action fournisseur sur la seule base des retours "
          "actuels**, et d'abord de rendre le motif de retour exploitable (liste de motifs courte, obligatoire à la saisie).",
          "ok")
    d.ul([
        "**Action 1** : rendre les motifs de retour lisibles et obligatoires dans les systèmes de saisie.",
        "**Action 2** : suivre le taux de retour par catégorie dans le temps pour détecter un écart durable.",
        "**Action 3** : si un écart apparaît, cibler en priorité les catégories de fort volume avant les catégories de petit volume.",
    ])
    d.p("Le fait que les écarts soient faibles peut venir du caractère **synthétique** du jeu de données : sur des données "
        "réelles, la même méthode peut donner un résultat différent. " + S("H"))

    d.h1("9. Mesurer les effets de la décision")
    d.table(["Élément", "Proposition"], [
        ["Indicateur de résultat", "Part de retours avec un motif exploitable ; taux de retour par catégorie"],
        ["Situation de référence", "Mesure actuelle : motif non exploitable pour 100 % des retours ; taux de retour par catégorie ci-dessus"],
        ["Comparaison", "Avant / après le changement de saisie ; magasins ou catégories témoins sans changement"],
        ["Fréquence", "Mensuelle, sur au moins plusieurs mois pour lisser la saisonnalité"],
        ["Seuil de décision", "À fixer avec la Direction commerciale : un écart durable de taux entre catégories justifie une action"],
        ["Risque d'interprétation", "Une baisse du taux peut venir d'un changement de ventes (dénominateur) et non d'une amélioration produit"],
    ])
    d.h2("Limites de cette analyse")
    d.ul([
        "Données synthétiques : les résultats illustrent une méthode, ils ne décrivent pas une enseigne réelle. " + S("V"),
        "Le taux est calculé en quantité ; le taux en montant n'est pas fiable (prix de vente sous le coût d'achat). " + S("V"),
        "L'effet d'une action ne peut pas être mesuré avec ces données : elles ne contiennent aucune intervention. " + S("V"),
    ])
    d.save_pdf(OUT / "UC-C1_processus_decisionnel.pdf")
    print("écrit UC-C1_processus_decisionnel.pdf")


if __name__ == "__main__":
    check_chrome()
    build()
