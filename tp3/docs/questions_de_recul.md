# Questions de recul (UC-06, sujet §11)

Chaque réponse s'appuie sur une mesure ou un fichier de ce dépôt.

**1. Pourquoi vérifier les schémas avant de transformer ?**
Parce qu'une erreur de schéma ne plante pas : elle produit un résultat faux. Ici les `.dat` n'ont ni en-tête ni types, donc les noms sont déduits de
TPC-DS. Sans vérification, Spark lirait « n'importe quoi » en silence : on a imposé le schéma et lu en FAILFAST (une ligne au mauvais nombre de champs fait échouer
la lecture ; `preuves/02_inventaire.txt` montre 23 champs sur chacune des 667 579 lignes de `store_sales`). Les types inférés par Spark diffèrent des types voulus
(`DECIMAL(12,2)` inféré `double`, `bigint` inféré `int`) : en CSV 13 colonnes sur 30 perdent leur type à la relecture (`outputs/comparaison_formats.csv`). Un `double` sur un montant
fausse les sommes ; une clé lue en texte fausse les jointures.

**2. Différence entre donnée brute, Silver et Gold ?**
*Brute* (Bronze) : fidèle à la source, tout en texte, avec sa provenance : 667 579 lignes de `store_sales`, aucune correction. *Silver* : mêmes lignes, **typées**, nettoyées
(espaces, valeurs vides), avec règles appliquées, indicateurs `qa_*` et quarantaine ; question posée : « les données sont-elles propres et compréhensibles ? ». *Gold* :
**agrégées pour une question métier** : `ventes_par_magasin_mois` = 720 lignes, un chiffre d'affaires par magasin et par mois. On ne peut plus retrouver une ligne de ticket dans le Gold,
d'où l'importance de conserver Bronze et Silver.

**3. Pourquoi connaître la granularité avant d'agréger ?**
Parce que l'agrégat dépend de ce que représente une ligne. Dans `store_sales` une ligne est **une ligne d'article d'un ticket**, pas un ticket : compter les lignes
donne 667 579, compter les tickets distincts 89 100 ; le panier moyen est le CA divisé par les **tickets**, pas par les lignes. De plus la clé (ticket, article) n'est pas unique
(+4 136 lignes en excès) : on ne peut pas la traiter comme une clé de ligne.

**4. Quels risques pour une jointure sur une clé supposée ?**
Multiplication de lignes (clé non unique côté « un »), perte de lignes (clés sans correspondance), ou sens faux (deux colonnes de même nom qui ne désignent pas la même chose).
Exemple évité : joindre les retours aux ventes sur (ticket, article) multiplierait les lignes puisque 4 136 clés de ventes sont répétées ; on agrège d'abord par magasin.
Chaque jointure du Gold est vérifiée à l'exécution (clé unique côté « un », lignes avant = après, non rapprochés) et **arrête** le traitement sinon (`outputs/jointures_verifiees.csv`).

**5. Pourquoi ne pas supprimer automatiquement les valeurs atypiques ?**
Parce qu'atypique ne veut pas dire fausse. 69,3 % des lignes de ventes ont un prix inférieur au coût d'achat et 74,3 % une marge négative : les supprimer détruirait les trois quarts du jeu
et fausserait le CA. Les 3 324 prix à 0 peuvent être des articles offerts. On a donc **conservé et signalé** (`qa_vente_a_perte`, `qa_marge_negative`, `qa_prix_nul`) et on n'a rejeté que
l'impossible (quantité <= 0, montant négatif, montant ≠ quantité x prix). À l'inverse `s_closed_date_sk` est incohérente : on l'ignore plutôt que de supprimer 41 % des ventes.

**6. Quels contrôles vérifient la cohérence d'un jeu transformé ?**
Ceux du rapport qualité (81 contrôles recalculés depuis les fichiers) : complétude, unicité et clés candidates, types, cohérence interne (montant = quantité x prix, retour jamais avant la vente),
volumes (Bronze = Silver + quarantaine), intégrité référentielle (0 orphelin), et **réconciliation** : somme du Gold = somme du Silver, et Gold = KPI du Jour 1 calculés avec un autre moteur
(CA 1 150 529 586,37 ; 89 100 tickets ; taux de retour 2,88 %). Limite : un contrôle de cohérence ne dit pas si une valeur atypique est vraie.

**7. Pourquoi Parquet convient-il aux usages analytiques ?**
Stockage **en colonnes**, schéma embarqué, compression : 42,2 Mo contre 144,0 Mo (CSV) et 471,9 Mo (JSON) pour le même jeu, 0 type altéré contre 13 et 22. Agréger une colonne prend 0,14 s
contre 0,49 s (CSV) et 1,05 s (JSON), et lire 1 colonne est environ 3,7 fois plus rapide que lire les 23 colonnes numériques (0,10 s contre 0,37 s ; 6× lors d'une première exécution : les durées varient, les tailles non). Le plan d'exécution montre le pushdown de filtre et la lecture de 3
colonnes seulement. Réserve : mesures locales, petits volumes ; le classement est fiable, les valeurs absolues non.

**8. Pourquoi Parquet seul n'a-t-il pas les garanties d'une table transactionnelle ?**
Un dossier Parquet est un ensemble de fichiers sans journal de transactions. Démontré (`preuves/08_parquet_formats.txt`, section 4) : un lot à schéma différent est accepté sans erreur
et sa colonne est invisible par défaut ; rejouer un lot duplique les lignes ; pas d'isolation lecteur/écrivain, pas de `UPDATE` / `DELETE` / `MERGE`, pas de retour arrière. Delta Lake, Iceberg ou Hudi ajoutent ce journal
au-dessus de Parquet. Aucun n'est installé ici : on ne présente donc pas nos dossiers comme des tables ACID.

**9. Dans quels cas une base NoSQL pourrait-elle compléter un Data Lake ?** *(réponse conceptuelle : UC-05 non traitée, aucun HBase exécuté)*
Quand il faut un **accès par clé en faible latence** à une donnée mise à jour souvent, ce qu'un fichier Parquet analytique ne fait pas : profil ou dernier état d'un client, consultation d'un historique
d'événements récents, compteurs. Le lac reste la source pour l'analyse de masse ; la base NoSQL sert les lectures unitaires rapides.

**10. Quelles limites de TPCx-BB faut-il prendre en compte ?**
Jeu **synthétique** : libellés de motifs de retour et descriptions de produits générés au hasard (motifs non lisibles métier) ; 69 % de ventes sous le coût d'achat donc marge non exploitable ;
dates de fermeture de magasins incohérentes (5 magasins sur 12 fermés avant leurs ventes) ; clé (ticket, article) non unique ; devise non précisée ; lot initial arrêté au 13/12/2005 (2005 incomplet) ;
noms de colonnes déduits de TPC-DS faute de dictionnaire. Les résultats ne valent ni mesure de performance ni conformité à un benchmark officiel.
