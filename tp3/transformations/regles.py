"""Règles de nettoyage UC-06 : définition déclarative, source unique de vérité.

`silver.py` applique ces règles et compte leurs effets ; `docs/transformations/regles_nettoyage.md`
est généré à partir de ce fichier et des comptages réels. Une règle = une anomalie, une décision,
une justification (règle de justification du sujet §3.2 : on ne supprime ni ne remplace rien sans règle explicite).

Types d'action :
  REJET        la ligne est mise à l'écart dans data/quarantaine/<table> avec l'identifiant de règle ;
  SIGNALEMENT  la ligne est conservée, une colonne booléenne `qa_*` la marque ;
  TRANSFO      la valeur est modifiée (et la modification est comptée) ;
  DEDOUBLON    une seule occurrence d'une ligne entièrement identique est conservée.

Les conditions sont des expressions SQL Spark sur les colonnes TYPÉES. Une condition NULL est
traitée comme fausse (la manquante est gérée par la règle des données obligatoires).
Catégories d'anomalie = celles du tableau du sujet (§4.7.1).
"""
from lib import schemas

# Règles communes à toutes les tables -----------------------------------------------------------
COMMUNES = [
    ("R01", "TRANSFO", "Valeur manquante",
     "Espaces en début ou fin de valeur, ou valeur vide après suppression des espaces",
     "trim() de toutes les colonnes texte ; une valeur vide devient NULL",
     "Évite que « Music » et « Music  » soient deux catégories distinctes dans un regroupement ou une jointure."),
    ("R02", "REJET", "Type incorrect",
     "Valeur non vide qui ne peut pas être convertie dans le type déclaré (entier, décimal, date)",
     "mise en quarantaine de la ligne (try_cast puis comparaison NULL avant/après)",
     "Une conversion échouée produit un NULL silencieux : on préfère isoler la ligne que fausser une somme."),
    ("R03", "REJET", "Identifiant invalide",
     "Donnée obligatoire manquante (clé, date, quantité, montant selon la table, voir lib/schemas.py)",
     "mise en quarantaine de la ligne",
     "Une ligne sans clé ou sans mesure ne peut être ni jointe ni agrégée ; elle est conservée à part, pas supprimée."),
    ("R04", "DEDOUBLON", "Doublon",
     "Ligne dont TOUTES les colonnes métier sont identiques à une autre ligne",
     "conservation d'une seule occurrence (dropDuplicates sur les colonnes métier)",
     "Définition claire et sans ambiguïté d'un doublon : aucune information n'est perdue."),
]

# Règles propres à chaque table ------------------------------------------------------------------
# rejets : (id, categorie, description, condition_sql, justification)
# drapeaux : (colonne_qa, id, categorie, description, condition_sql, justification)
SPECIFIQUES = {
    "store_sales": {
        "rejets": [
            ("SS-R05", "Valeur atypique", "Quantité vendue <= 0", "ss_quantity <= 0",
             "Un ticket de vente ne peut pas contenir une quantité nulle ou négative ; les retours sont dans store_returns."),
            ("SS-R06", "Valeur atypique", "Prix de vente ou montant de ligne négatif",
             "ss_sales_price < 0 OR ss_ext_sales_price < 0",
             "Même raison : aucun montant négatif légitime dans une vente (un négatif serait un retour, traité à part)."),
            ("SS-R07", "Valeur atypique", "Montant de ligne différent de quantité x prix (écart > 0,02)",
             "abs(ss_ext_sales_price - ss_quantity * ss_sales_price) > 0.02",
             "Mesures internes incohérentes : sommer ce montant fausserait le chiffre d'affaires."),
        ],
        "drapeaux": [
            ("qa_cle_dupliquee", "SS-R08", "Doublon",
             "Clé (ticket, article) présente plusieurs fois", "qa_cle_dupliquee",
             "NON supprimé : les lignes dupliquées ont même client, magasin et date mais des quantités et prix différents. "
             "Ce sont des lignes distinctes (un article scanné plusieurs fois), pas des doublons."),
            ("qa_prix_nul", "SS-R09", "Valeur atypique", "Prix de vente égal à 0", "ss_sales_price = 0",
             "Article offert ou promotion : cas métier possible, donc conservé et signalé."),
            ("qa_vente_a_perte", "SS-R10", "Valeur atypique", "Prix de vente inférieur au coût d'achat",
             "ss_sales_price < ss_wholesale_cost",
             "Concerne la majorité des lignes : particularité du jeu synthétique. Conservé ; la marge n'est pas un indicateur fiable."),
            ("qa_marge_negative", "SS-R11", "Valeur atypique", "Marge nette négative", "ss_net_profit < 0",
             "Idem : valeur atypique mais pas impossible, conservée et signalée."),
        ],
    },
    "store_returns": {
        "rejets": [
            ("SR-R05", "Valeur atypique", "Quantité retournée <= 0", "sr_return_quantity <= 0",
             "Un retour porte au moins une unité."),
            ("SR-R06", "Valeur atypique", "Montant remboursé négatif", "sr_return_amt < 0",
             "Un remboursement est un montant positif ; un négatif serait une inversion de signe."),
        ],
        "drapeaux": [
            ("qa_cle_dupliquee", "SR-R07", "Doublon", "Clé (ticket, article) présente plusieurs fois", "qa_cle_dupliquee",
             "Conservé : lignes de retour distinctes (quantités ou montants différents), pas des doublons exacts."),
            ("qa_remboursement_nul", "SR-R08", "Valeur atypique", "Montant remboursé égal à 0", "sr_return_amt = 0",
             "Retour sans remboursement (geste commercial, échange) : cas possible, conservé."),
            ("qa_motif_manquant", "SR-R09", "Valeur manquante", "Motif de retour non renseigné", "sr_reason_sk IS NULL",
             "Conservé ; en Gold le motif est libellé « Motif non renseigné » pour ne pas perdre ces retours."),
        ],
    },
    "item": {
        "rejets": [],
        "drapeaux": [
            ("qa_prix_invalide", "IT-R05", "Valeur atypique", "Prix courant vide ou <= 0",
             "i_current_price IS NULL OR i_current_price <= 0",
             "Un produit sans prix reste une dimension valide (les ventes y renvoient) : conservé et signalé."),
            ("qa_prix_sous_cout", "IT-R06", "Valeur atypique", "Prix courant inférieur au coût d'achat",
             "i_current_price < i_wholesale_cost", "Observation métier sur un jeu synthétique, conservée."),
            ("qa_marque_imputee", "IT-R07", "Valeur manquante", "Marque non renseignée", "i_brand IS NULL",
             "Voir transformation IT-T01 : libellé explicite plutôt que NULL, et la ligne reste identifiable."),
        ],
        "transfos": [
            ("IT-T01", "Valeur manquante", "Marque vide (i_brand NULL)",
             "remplacée par le libellé « Non renseigné » (les identifiants i_brand_id restent NULL)",
             "Règle explicite et tracée par qa_marque_imputee ; évite qu'un regroupement par marque ignore ces produits.",
             "qa_marque_imputee"),
        ],
    },
    "store": {
        "rejets": [],
        "drapeaux": [],
        "notes": [
            ("ST-R05", "Date incohérente", "Colonne s_closed_date_sk (date de fermeture du magasin)",
             "colonne conservée telle quelle, jugée NON exploitable ; aucun filtre sur la fermeture",
             "5 magasins sur 12 ont une fermeture déclarée (1917 à 1968) antérieure à leur première vente (2001) et les 7 autres une date "
             "future (2019 à 2141), invérifiable (preuve : preuves/03_exploration.txt, outputs/valeurs_atypiques.csv). "
             "Filtrer dessus supprimerait à tort 276 032 lignes de vente (41 %)."),
        ],
    },
    "date_dim": {"rejets": [
        ("DD-R05", "Date incohérente", "Année ou mois incohérent avec la date (d_year != year(d_date) ou d_moy != month(d_date))",
         "d_year != year(d_date) OR d_moy != month(d_date)",
         "Le calendrier sert de référence pour tous les regroupements par période : une incohérence interne fausserait les Gold."),
    ], "drapeaux": []},
    "reason": {"rejets": [], "drapeaux": []},
}

# Pour les dimensions : une clé de substitution dupliquée rendrait les jointures ambiguës (multiplication de lignes).
DIMENSIONS = ["item", "store", "date_dim", "reason"]
REGLE_CLE_DIMENSION = ("R05", "REJET", "Identifiant invalide",
                       "Clé de substitution dupliquée dans une dimension",
                       "mise en quarantaine de toutes les lignes en doublon de clé (aucun choix arbitraire)",
                       "Une dimension à clé non unique multiplierait les lignes de ventes lors des jointures.")


def colonnes_obligatoires(table):
    return schemas.OBLIGATOIRES[table]
