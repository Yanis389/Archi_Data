"""Tests et vérifications finales UC-06 : chaque test reprend une case à cocher du sujet (§8.1 à §8.5).

Les tests RELISENT les sorties produites (pipeline déjà exécuté, voir run_all.sh) et recalculent ce qui peut
l'être ; ils ne font confiance à aucun rapport sans le recouper avec les données.

Lancement : python -m unittest tests.test_final_uc06 -v
"""
import csv
import unittest

from pyspark.sql import functions as F

from lib import config, schemas
from lib.spark_utils import get_spark, lire_brut
from transformations import regles

GOLD = ["ventes_par_magasin_mois", "ventes_par_categorie_annee", "retours_par_motif", "taux_retour_par_magasin"]
OUT, DOCS = config.OUTPUTS_DIR, config.TP3_ROOT / "docs"


def csv_lignes(nom):
    with open(OUT / nom, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def texte(chemin):
    return chemin.read_text(encoding="utf-8")


class BaseSpark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = get_spark("TP3-Tests-Finaux")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()


class Test81Lecture(BaseSpark):
    def test_sources_accessibles(self):
        for t in config.SOURCES:
            with open(config.chemin_source(t), "rb") as f:
                self.assertTrue(f.read(1), f"{t} : fichier vide ou illisible")

    def test_formats_correctement_identifies(self):
        for r in csv_lignes("inventaire_sources.csv"):
            self.assertIn("pipe", r["format"], r["table"])
            self.assertIn("UTF-8 valide", r["format"], r["table"])
            self.assertEqual(r["structure_coherente"], "True", f"{r['table']} : nombre de champs variable selon les lignes")

    def test_schemas_lisibles(self):
        for t in config.SOURCES:
            df = lire_brut(self.spark, t)
            self.assertEqual(df.columns, schemas.colonnes(t))   # FAILFAST : lève une erreur si une ligne n'a pas le bon nombre de champs
            self.assertTrue(df.first() is not None)

    def test_volumes_releves(self):
        for r in csv_lignes("inventaire_sources.csv"):
            lignes_texte = self.spark.read.text(config.chemin_source(r["table"])).count()
            self.assertEqual(int(r["nb_lignes"]), lignes_texte, r["table"])
            self.assertGreater(int(r["nb_lignes"]), 0)


class Test82Transformation(BaseSpark):
    def test_regles_de_nettoyage_documentees(self):
        doc = texte(DOCS / "transformations" / "regles_nettoyage.md")
        for t in config.SOURCES:
            self.assertIn(f"### {t}", doc)
            # chaque règle spécifique est documentée avec sa justification
            spec = regles.SPECIFIQUES[t]
            for rid in [x[0] for x in spec["rejets"]] + [x[1] for x in spec["drapeaux"]] + [x[0] for x in spec.get("transfos", [])] + [x[0] for x in spec.get("notes", [])]:
                self.assertIn(f"| {rid} |", doc, f"règle {rid} absente du document")

    def test_types_coherents(self):
        for t in config.SOURCES:
            silver = self.spark.read.parquet(config.chemin("silver", t))
            attendu = {c: tp.lower() for c, tp in schemas.SCHEMAS[t]}
            reel = {f.name: f.dataType.simpleString() for f in silver.schema.fields}
            for c, tp in attendu.items():
                self.assertEqual(reel[c], tp, f"{t}.{c}")

    def test_transformations_executables(self):
        for r in csv_lignes("silver_controle.csv"):
            self.assertEqual(r["bilan_conservation"], "OK", r["table"])
            self.assertEqual(int(r["lignes_bronze"]), int(r["lignes_silver"]) + int(r["lignes_quarantaine"]) + int(r["doublons_exacts_retires"]))

    def test_jointures_justifiees(self):
        jointures = csv_lignes("jointures_verifiees.csv")
        self.assertGreaterEqual(len(jointures), 1)
        for j in jointures:
            self.assertEqual(j["verdict"], "OK", j["jointure"])
            self.assertEqual(j["cle_droite_unique"], "True", j["jointure"])
            self.assertEqual(j["lignes_avant"], j["lignes_apres"], j["jointure"])
        doc = texte(DOCS / "transformations" / "jointures_et_agregations.md")
        for j in jointures:
            self.assertIn(j["cle_gauche"], doc.replace("`", ""), j["jointure"])

    def test_agregations_ont_une_granularite_definie(self):
        doc = texte(DOCS / "data-dictionary" / "gold_jeux_analytiques.md")
        for g in csv_lignes("gold_controle.csv"):
            self.assertTrue(g["granularite"])
            self.assertEqual(g["granularite_unique"], "True", g["jeu"])
            self.assertIn(g["jeu"], doc)
            self.assertIn("Granularité", doc)


class Test83Zones(BaseSpark):
    def test_silver_produites(self):
        for t in config.SOURCES:
            self.assertGreater(self.spark.read.parquet(config.chemin("silver", t)).count(), 0, t)

    def test_gold_produites(self):
        for g in GOLD:
            self.assertGreater(self.spark.read.parquet(config.chemin("gold", g)).count(), 0, g)

    def test_chemins_documentes(self):
        readme = texte(config.TP3_ROOT / "README.md")
        for chemin in ["data/bronze", "data/silver", "data/gold", "data/quarantaine", "data/parquet_test"]:
            self.assertIn(chemin, readme)
        self.assertIn("donnees_sources", texte(OUT / "fiche_environnement.json"))

    def test_provenance_conservee(self):
        for t in config.SOURCES:
            silver = self.spark.read.parquet(config.chemin("silver", t))
            for c in ["_source_file", "_batch", "_ingested_at", "_silver_at", "_regles_version"]:
                self.assertIn(c, silver.columns, f"{t}.{c}")
            fichier = silver.select("_source_file").distinct().collect()
            self.assertEqual([r[0] for r in fichier], [f"retail_project/data/{t}/{t}.dat"], t)
        for g in GOLD:
            self.assertIn("_sources", self.spark.read.parquet(config.chemin("gold", g)).columns)
        self.assertIn("_ligne_brute", self.spark.read.parquet(config.chemin("quarantaine", "store_sales")).columns)


class Test84Parquet(BaseSpark):
    def test_resultat_ecrit_en_parquet(self):
        for g in GOLD:
            fichiers = list((config.GOLD_DIR / g).glob("*.parquet"))
            self.assertTrue(fichiers, g)
            with open(fichiers[0], "rb") as f:
                self.assertEqual(f.read(4), b"PAR1", "signature Parquet attendue en début de fichier")

    def test_resultat_relu_schema_et_lignes(self):
        for r in csv_lignes("parquet_relecture.csv"):
            self.assertEqual(r["statut"], "OK", r["jeu"])
            self.assertEqual(r["schema_identique"], "True", r["jeu"])
            self.assertEqual(r["lignes_original"], r["lignes_relues"], r["jeu"])
            self.assertEqual(r["lignes_differentes_exceptAll"], "0", r["jeu"])
        # recoupement indépendant : on relit nous-mêmes l'original et la copie
        original = self.spark.read.parquet(config.chemin("gold", "retours_par_motif"))
        copie = self.spark.read.parquet(str(config.PARQUET_TEST_DIR / "gold_retours_par_motif_copie"))
        self.assertEqual(original.count(), copie.count())
        self.assertEqual([(f.name, f.dataType) for f in original.schema.fields], [(f.name, f.dataType) for f in copie.schema.fields])
        self.assertEqual(original.exceptAll(copie).count(), 0)


class Test85Qualite(BaseSpark):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rapport = csv_lignes("rapport_qualite.csv")

    def familles(self, nom):
        return [r for r in self.rapport if r["famille"].startswith(nom)]

    def test_valeurs_manquantes_controlees(self):
        c = self.familles("Complétude")
        self.assertGreaterEqual(len(c), len(config.SOURCES))
        # recoupement : aucune valeur obligatoire manquante dans store_sales
        ss = self.spark.read.parquet(config.chemin("silver", "store_sales"))
        self.assertEqual(ss.filter(" OR ".join(f"{c} IS NULL" for c in schemas.OBLIGATOIRES["store_sales"])).count(), 0)

    def test_doublons_examines(self):
        doublons = [r for r in self.rapport if "dupliqu" in r["regle"] or "unique" in r["regle"]]
        self.assertTrue(doublons)
        # le doublon de clé est connu et documenté, pas caché : recalcul indépendant
        ss = self.spark.read.parquet(config.chemin("silver", "store_sales"))
        exces = ss.count() - ss.select("ss_ticket_number", "ss_item_sk").distinct().count()
        self.assertEqual(exces, 4136)
        self.assertEqual(ss.filter("qa_cle_dupliquee").count(), 8174)

    def test_cles_candidates_verifiees(self):
        cles = self.familles("Unicité")
        self.assertTrue(any("ss_ticket_number+ss_item_sk" in r["regle"] for r in cles))
        for t in ["item", "store", "date_dim", "reason"]:
            self.assertTrue(any(r["table"] == t and r["statut"] == "OK" for r in cles), t)

    def test_aucun_echec_et_anomalies_documentees(self):
        self.assertEqual([r["id"] for r in self.rapport if r["statut"] == "ECHEC"], [])
        self.assertTrue((OUT / "valeurs_atypiques.csv").exists())
        doc = texte(DOCS / "quality" / "rapport_qualite.md")
        for r in self.rapport:
            if r["statut"] == "AVERTISSEMENT":
                self.assertIn(r["id"], doc)
                self.assertTrue(r["commentaire"], f"{r['id']} : un avertissement doit être expliqué")

    def test_limites_des_controles_precisees(self):
        doc = texte(DOCS / "quality" / "rapport_qualite.md")
        self.assertIn("Limites des contrôles", doc)
        for mot in ["déduits", "synthétique", "data_refresh"]:
            self.assertIn(mot, doc)

    def test_reconciliation_gold_silver_et_jour1(self):
        rec = self.familles("Réconciliation")
        self.assertGreaterEqual(len(rec), 14)
        self.assertTrue(all(r["statut"] == "OK" for r in rec))


if __name__ == "__main__":
    unittest.main(verbosity=2)
