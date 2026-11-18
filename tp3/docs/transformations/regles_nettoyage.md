# Règles de nettoyage (UC-06, étapes 4 et 6)

Document **généré** par `python -m transformations.silver` à partir de `transformations/regles.py` et des comptages réels (preuve : `preuves/05_silver.txt`, détail : `outputs/regles_nettoyage_resultats.csv`).

Principes (sujet §3.2) : aucune ligne n'est supprimée arbitrairement ; une ligne rejetée est mise en **quarantaine** avec sa ligne brute et l'identifiant de règle ; une valeur atypique mais plausible est **conservée et signalée** par une colonne `qa_*` ; toute valeur remplacée l'est par une règle explicite et tracée.

Actions : `REJET` (quarantaine) · `SIGNALEMENT` (conservée + colonne `qa_*`) · `TRANSFO` (valeur modifiée) · `DEDOUBLON` (une occurrence conservée) · `DECISION` (décision documentée sans traitement).

## Bilan de conservation

| Table | Bronze | Silver | Quarantaine | Doublons exacts retirés | Bronze = Silver + quarantaine + doublons |
|---|---|---|---|---|---|
| store_sales | 667 579 | 667 579 | 0 | 0 | OK |
| store_returns | 37 902 | 37 902 | 0 | 0 | OK |
| item | 17 820 | 17 820 | 0 | 0 | OK |
| store | 12 | 12 | 0 | 0 | OK |
| date_dim | 109 573 | 109 573 | 0 | 0 | OK |
| reason | 35 | 35 | 0 | 0 | OK |

## Règles par table

### store_sales

| Règle | Anomalie (catégorie) | Constat | Action appliquée | Justification | Concerné |
|---|---|---|---|---|---|
| R01 | Valeur manquante | Espaces en début ou fin de valeur, ou valeur vide après suppression des espaces | TRANSFO : trim() de toutes les colonnes texte ; une valeur vide devient NULL | Évite que « Music » et « Music  » soient deux catégories distinctes dans un regroupement ou une jointure. | 0 valeurs |
| R02 | Type incorrect | Valeur non vide qui ne peut pas être convertie dans le type déclaré (entier, décimal, date) | REJET : mise en quarantaine de la ligne (try_cast puis comparaison NULL avant/après) | Une conversion échouée produit un NULL silencieux : on préfère isoler la ligne que fausser une somme. | 0 lignes |
| R03 | Identifiant invalide | Donnée obligatoire manquante (clé, date, quantité, montant selon la table, voir lib/schemas.py) | REJET : mise en quarantaine de la ligne | Une ligne sans clé ou sans mesure ne peut être ni jointe ni agrégée ; elle est conservée à part, pas supprimée. | 0 lignes |
| R04 | Doublon | Ligne dont TOUTES les colonnes métier sont identiques à une autre ligne | DEDOUBLON : conservation d'une seule occurrence (dropDuplicates sur les colonnes métier) | Définition claire et sans ambiguïté d'un doublon : aucune information n'est perdue. | 0 lignes |
| SS-R05 | Valeur atypique | Quantité vendue <= 0 | REJET : mise en quarantaine de la ligne | Un ticket de vente ne peut pas contenir une quantité nulle ou négative ; les retours sont dans store_returns. | 0 lignes |
| SS-R06 | Valeur atypique | Prix de vente ou montant de ligne négatif | REJET : mise en quarantaine de la ligne | Même raison : aucun montant négatif légitime dans une vente (un négatif serait un retour, traité à part). | 0 lignes |
| SS-R07 | Valeur atypique | Montant de ligne différent de quantité x prix (écart > 0,02) | REJET : mise en quarantaine de la ligne | Mesures internes incohérentes : sommer ce montant fausserait le chiffre d'affaires. | 0 lignes |
| SS-R08 | Doublon | Clé (ticket, article) présente plusieurs fois | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | NON supprimé : les lignes dupliquées ont même client, magasin et date mais des quantités et prix différents. Ce sont des lignes distinctes (un article scanné plusieurs fois), pas des doublons. | 8 174 lignes |
| SS-R09 | Valeur atypique | Prix de vente égal à 0 | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Article offert ou promotion : cas métier possible, donc conservé et signalé. | 3 324 lignes |
| SS-R10 | Valeur atypique | Prix de vente inférieur au coût d'achat | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Concerne la majorité des lignes : particularité du jeu synthétique. Conservé ; la marge n'est pas un indicateur fiable. | 462 852 lignes |
| SS-R11 | Valeur atypique | Marge nette négative | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Idem : valeur atypique mais pas impossible, conservée et signalée. | 495 971 lignes |

### store_returns

| Règle | Anomalie (catégorie) | Constat | Action appliquée | Justification | Concerné |
|---|---|---|---|---|---|
| R01 | Valeur manquante | Espaces en début ou fin de valeur, ou valeur vide après suppression des espaces | TRANSFO : trim() de toutes les colonnes texte ; une valeur vide devient NULL | Évite que « Music » et « Music  » soient deux catégories distinctes dans un regroupement ou une jointure. | 0 valeurs |
| R02 | Type incorrect | Valeur non vide qui ne peut pas être convertie dans le type déclaré (entier, décimal, date) | REJET : mise en quarantaine de la ligne (try_cast puis comparaison NULL avant/après) | Une conversion échouée produit un NULL silencieux : on préfère isoler la ligne que fausser une somme. | 0 lignes |
| R03 | Identifiant invalide | Donnée obligatoire manquante (clé, date, quantité, montant selon la table, voir lib/schemas.py) | REJET : mise en quarantaine de la ligne | Une ligne sans clé ou sans mesure ne peut être ni jointe ni agrégée ; elle est conservée à part, pas supprimée. | 0 lignes |
| R04 | Doublon | Ligne dont TOUTES les colonnes métier sont identiques à une autre ligne | DEDOUBLON : conservation d'une seule occurrence (dropDuplicates sur les colonnes métier) | Définition claire et sans ambiguïté d'un doublon : aucune information n'est perdue. | 0 lignes |
| SR-R05 | Valeur atypique | Quantité retournée <= 0 | REJET : mise en quarantaine de la ligne | Un retour porte au moins une unité. | 0 lignes |
| SR-R06 | Valeur atypique | Montant remboursé négatif | REJET : mise en quarantaine de la ligne | Un remboursement est un montant positif ; un négatif serait une inversion de signe. | 0 lignes |
| SR-R07 | Doublon | Clé (ticket, article) présente plusieurs fois | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Conservé : lignes de retour distinctes (quantités ou montants différents), pas des doublons exacts. | 313 lignes |
| SR-R08 | Valeur atypique | Montant remboursé égal à 0 | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Retour sans remboursement (geste commercial, échange) : cas possible, conservé. | 190 lignes |
| SR-R09 | Valeur manquante | Motif de retour non renseigné | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Conservé ; en Gold le motif est libellé « Motif non renseigné » pour ne pas perdre ces retours. | 11 lignes |

### item

| Règle | Anomalie (catégorie) | Constat | Action appliquée | Justification | Concerné |
|---|---|---|---|---|---|
| R01 | Valeur manquante | Espaces en début ou fin de valeur, ou valeur vide après suppression des espaces | TRANSFO : trim() de toutes les colonnes texte ; une valeur vide devient NULL | Évite que « Music » et « Music  » soient deux catégories distinctes dans un regroupement ou une jointure. | 2 575 valeurs |
| R02 | Type incorrect | Valeur non vide qui ne peut pas être convertie dans le type déclaré (entier, décimal, date) | REJET : mise en quarantaine de la ligne (try_cast puis comparaison NULL avant/après) | Une conversion échouée produit un NULL silencieux : on préfère isoler la ligne que fausser une somme. | 0 lignes |
| R03 | Identifiant invalide | Donnée obligatoire manquante (clé, date, quantité, montant selon la table, voir lib/schemas.py) | REJET : mise en quarantaine de la ligne | Une ligne sans clé ou sans mesure ne peut être ni jointe ni agrégée ; elle est conservée à part, pas supprimée. | 0 lignes |
| R04 | Doublon | Ligne dont TOUTES les colonnes métier sont identiques à une autre ligne | DEDOUBLON : conservation d'une seule occurrence (dropDuplicates sur les colonnes métier) | Définition claire et sans ambiguïté d'un doublon : aucune information n'est perdue. | 0 lignes |
| R05 | Identifiant invalide | Clé de substitution dupliquée dans une dimension | REJET : mise en quarantaine de toutes les lignes en doublon de clé (aucun choix arbitraire) | Une dimension à clé non unique multiplierait les lignes de ventes lors des jointures. | 0 lignes |
| IT-R05 | Valeur atypique | Prix courant vide ou <= 0 | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Un produit sans prix reste une dimension valide (les ventes y renvoient) : conservé et signalé. | 0 lignes |
| IT-R06 | Valeur atypique | Prix courant inférieur au coût d'achat | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Observation métier sur un jeu synthétique, conservée. | 7 768 lignes |
| IT-R07 | Valeur manquante | Marque non renseignée | SIGNALEMENT : ligne conservée, colonne booléenne qa_* ajoutée | Voir transformation IT-T01 : libellé explicite plutôt que NULL, et la ligne reste identifiable. | 6 lignes |
| IT-T01 | Valeur manquante | Marque vide (i_brand NULL) | TRANSFO : remplacée par le libellé « Non renseigné » (les identifiants i_brand_id restent NULL) | Règle explicite et tracée par qa_marque_imputee ; évite qu'un regroupement par marque ignore ces produits. | 6 valeurs |

### store

| Règle | Anomalie (catégorie) | Constat | Action appliquée | Justification | Concerné |
|---|---|---|---|---|---|
| R01 | Valeur manquante | Espaces en début ou fin de valeur, ou valeur vide après suppression des espaces | TRANSFO : trim() de toutes les colonnes texte ; une valeur vide devient NULL | Évite que « Music » et « Music  » soient deux catégories distinctes dans un regroupement ou une jointure. | 1 valeurs |
| R02 | Type incorrect | Valeur non vide qui ne peut pas être convertie dans le type déclaré (entier, décimal, date) | REJET : mise en quarantaine de la ligne (try_cast puis comparaison NULL avant/après) | Une conversion échouée produit un NULL silencieux : on préfère isoler la ligne que fausser une somme. | 0 lignes |
| R03 | Identifiant invalide | Donnée obligatoire manquante (clé, date, quantité, montant selon la table, voir lib/schemas.py) | REJET : mise en quarantaine de la ligne | Une ligne sans clé ou sans mesure ne peut être ni jointe ni agrégée ; elle est conservée à part, pas supprimée. | 0 lignes |
| R04 | Doublon | Ligne dont TOUTES les colonnes métier sont identiques à une autre ligne | DEDOUBLON : conservation d'une seule occurrence (dropDuplicates sur les colonnes métier) | Définition claire et sans ambiguïté d'un doublon : aucune information n'est perdue. | 0 lignes |
| R05 | Identifiant invalide | Clé de substitution dupliquée dans une dimension | REJET : mise en quarantaine de toutes les lignes en doublon de clé (aucun choix arbitraire) | Une dimension à clé non unique multiplierait les lignes de ventes lors des jointures. | 0 lignes |
| ST-R05 | Date incohérente | Colonne s_closed_date_sk (date de fermeture du magasin) | DECISION : colonne conservée telle quelle, jugée NON exploitable ; aucun filtre sur la fermeture | 5 magasins sur 12 ont une fermeture déclarée (1917 à 1968) antérieure à leur première vente (2001) et les 7 autres une date future (2019 à 2141), invérifiable (preuve : preuves/03_exploration.txt, outputs/valeurs_atypiques.csv). Filtrer dessus supprimerait à tort 276 032 lignes de vente (41 %). | — |

### date_dim

| Règle | Anomalie (catégorie) | Constat | Action appliquée | Justification | Concerné |
|---|---|---|---|---|---|
| R01 | Valeur manquante | Espaces en début ou fin de valeur, ou valeur vide après suppression des espaces | TRANSFO : trim() de toutes les colonnes texte ; une valeur vide devient NULL | Évite que « Music » et « Music  » soient deux catégories distinctes dans un regroupement ou une jointure. | 0 valeurs |
| R02 | Type incorrect | Valeur non vide qui ne peut pas être convertie dans le type déclaré (entier, décimal, date) | REJET : mise en quarantaine de la ligne (try_cast puis comparaison NULL avant/après) | Une conversion échouée produit un NULL silencieux : on préfère isoler la ligne que fausser une somme. | 0 lignes |
| R03 | Identifiant invalide | Donnée obligatoire manquante (clé, date, quantité, montant selon la table, voir lib/schemas.py) | REJET : mise en quarantaine de la ligne | Une ligne sans clé ou sans mesure ne peut être ni jointe ni agrégée ; elle est conservée à part, pas supprimée. | 0 lignes |
| R04 | Doublon | Ligne dont TOUTES les colonnes métier sont identiques à une autre ligne | DEDOUBLON : conservation d'une seule occurrence (dropDuplicates sur les colonnes métier) | Définition claire et sans ambiguïté d'un doublon : aucune information n'est perdue. | 0 lignes |
| R05 | Identifiant invalide | Clé de substitution dupliquée dans une dimension | REJET : mise en quarantaine de toutes les lignes en doublon de clé (aucun choix arbitraire) | Une dimension à clé non unique multiplierait les lignes de ventes lors des jointures. | 0 lignes |
| DD-R05 | Date incohérente | Année ou mois incohérent avec la date (d_year != year(d_date) ou d_moy != month(d_date)) | REJET : mise en quarantaine de la ligne | Le calendrier sert de référence pour tous les regroupements par période : une incohérence interne fausserait les Gold. | 0 lignes |

### reason

| Règle | Anomalie (catégorie) | Constat | Action appliquée | Justification | Concerné |
|---|---|---|---|---|---|
| R01 | Valeur manquante | Espaces en début ou fin de valeur, ou valeur vide après suppression des espaces | TRANSFO : trim() de toutes les colonnes texte ; une valeur vide devient NULL | Évite que « Music » et « Music  » soient deux catégories distinctes dans un regroupement ou une jointure. | 4 valeurs |
| R02 | Type incorrect | Valeur non vide qui ne peut pas être convertie dans le type déclaré (entier, décimal, date) | REJET : mise en quarantaine de la ligne (try_cast puis comparaison NULL avant/après) | Une conversion échouée produit un NULL silencieux : on préfère isoler la ligne que fausser une somme. | 0 lignes |
| R03 | Identifiant invalide | Donnée obligatoire manquante (clé, date, quantité, montant selon la table, voir lib/schemas.py) | REJET : mise en quarantaine de la ligne | Une ligne sans clé ou sans mesure ne peut être ni jointe ni agrégée ; elle est conservée à part, pas supprimée. | 0 lignes |
| R04 | Doublon | Ligne dont TOUTES les colonnes métier sont identiques à une autre ligne | DEDOUBLON : conservation d'une seule occurrence (dropDuplicates sur les colonnes métier) | Définition claire et sans ambiguïté d'un doublon : aucune information n'est perdue. | 0 lignes |
| R05 | Identifiant invalide | Clé de substitution dupliquée dans une dimension | REJET : mise en quarantaine de toutes les lignes en doublon de clé (aucun choix arbitraire) | Une dimension à clé non unique multiplierait les lignes de ventes lors des jointures. | 0 lignes |
