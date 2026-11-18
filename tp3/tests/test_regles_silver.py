"""Test des règles de nettoyage sur des anomalies INJECTÉES.

Sur les vraies données, aucune ligne n'est rejetée (le jeu TPCx-BB est propre sur ces règles) : le
fonctionnement des règles de rejet ne serait donc jamais démontré. Ce test fabrique de fausses
tables Bronze contenant des anomalies connues, les passe dans `silver.traiter` (même code que
la production) et vérifie le résultat. Les écritures vont dans un répertoire temporaire.

Lancement : python -m unittest tests.test_regles_silver -v
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from lib import config, schemas
from lib.spark_utils import get_spark
from transformations import silver

PROV = ["_source_file", "_batch", "_ingested_at"]


def ligne(table, **valeurs):
    """Ligne Bronze (toutes colonnes en texte) : valeurs par défaut valides, surchargées par `valeurs`."""
    defauts = {
        "store_sales": dict(ss_sold_date_sk="100", ss_sold_time_sk="200", ss_item_sk="5", ss_customer_sk="7", ss_cdemo_sk="1",
                            ss_hdemo_sk="1", ss_addr_sk="1", ss_store_sk="2", ss_promo_sk="3", ss_ticket_number="1000",
                            ss_quantity="2", ss_wholesale_cost="5.00", ss_list_price="12.00", ss_sales_price="10.00",
                            ss_ext_discount_amt="0.00", ss_ext_sales_price="20.00", ss_ext_wholesale_cost="10.00",
                            ss_ext_list_price="24.00", ss_ext_tax="1.00", ss_coupon_amt="0.00", ss_net_paid="20.00",
                            ss_net_paid_inc_tax="21.00", ss_net_profit="10.00"),
        "item": dict(i_item_sk="1", i_item_id="AAA", i_rec_start_date="2000-01-14", i_rec_end_date=None, i_item_desc="desc",
                     i_current_price="10.00", i_wholesale_cost="5.00", i_brand_id="1", i_brand="Marque", i_class_id="1",
                     i_class="classe", i_category_id="1", i_category="Music", i_manufact_id="1", i_manufact="fab",
                     i_size="M", i_formulation="f", i_color="rouge", i_units="Each", i_container="Unknown",
                     i_manager_id="1", i_product_name="produit"),
    }[table]
    defauts.update(valeurs)
    return tuple(defauts[c] for c in schemas.colonnes(table)) + ("retail_project/test.dat", "test", None)


class TestRegles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = get_spark("TP3-Test-Regles")
        cls.tmp = Path(tempfile.mkdtemp(prefix="tp3_test_"))
        cls.sauve = (config.BRONZE_DIR, config.SILVER_DIR, config.QUARANTAINE_DIR)
        config.BRONZE_DIR, config.SILVER_DIR, config.QUARANTAINE_DIR = (cls.tmp / "bronze", cls.tmp / "silver", cls.tmp / "quar")

    @classmethod
    def tearDownClass(cls):
        config.BRONZE_DIR, config.SILVER_DIR, config.QUARANTAINE_DIR = cls.sauve
        shutil.rmtree(cls.tmp, ignore_errors=True)
        cls.spark.stop()

    def bronze(self, table, lignes):
        schema = StructType([StructField(c, StringType(), True) for c in schemas.colonnes(table) + PROV])
        df = self.spark.createDataFrame(lignes, schema).withColumn("_ingested_at", F.current_timestamp())
        df.write.mode("overwrite").parquet(config.chemin("bronze", table))

    # ------------------------------------------------------------------------------------------
    def test_store_sales_anomalies_injectees(self):
        L = [
            ligne("store_sales", ss_ticket_number="1"),                                                    # valide
            ligne("store_sales", ss_ticket_number="2", ss_quantity="abc"),                                 # R02 type
            ligne("store_sales", ss_ticket_number=None),                                                   # R03 clé vide
            ligne("store_sales", ss_ticket_number="4", ss_quantity="-1", ss_ext_sales_price="-10.00"),     # SS-R05 + SS-R06
            ligne("store_sales", ss_ticket_number="5", ss_sales_price="-1.00", ss_ext_sales_price="-2.00"),  # SS-R06
            ligne("store_sales", ss_ticket_number="6", ss_ext_sales_price="99.99"),                        # SS-R07 incohérent
            ligne("store_sales", ss_ticket_number="7"), ligne("store_sales", ss_ticket_number="7"),        # R04 doublon EXACT
            ligne("store_sales", ss_ticket_number="8", ss_quantity="2", ss_ext_sales_price="20.00"),       # clé répétée, lignes distinctes
            ligne("store_sales", ss_ticket_number="8", ss_quantity="3", ss_ext_sales_price="30.00"),       #   -> conservées + signalées
            ligne("store_sales", ss_ticket_number="9", ss_sales_price="0.00", ss_ext_sales_price="0.00"),  # prix nul : signalé
            ligne("store_sales", ss_ticket_number="10", ss_sales_price="3.00", ss_ext_sales_price="6.00",
                  ss_wholesale_cost="5.00", ss_net_profit="-4.00"),                                        # vente à perte : signalée
            ligne("store_sales", ss_ticket_number=" 11 ", ss_store_sk=" 2 "),                              # R01 espaces
        ]
        self.bronze("store_sales", L)
        controle, res = silver.traiter(self.spark, "store_sales")

        self.assertEqual(controle["lignes_bronze"], 13)
        self.assertEqual(controle["lignes_quarantaine"], 5)
        self.assertEqual(controle["doublons_exacts_retires"], 1)
        self.assertEqual(controle["lignes_silver"], 7)
        self.assertEqual(controle["bilan_conservation"], "OK")          # 13 = 7 + 5 + 1

        quar = {r["_motifs_rejet"]: r for r in self.spark.read.parquet(config.chemin("quarantaine", "store_sales")).collect()}
        motifs = sorted(quar)
        print("\nMotifs de quarantaine :", motifs)
        self.assertTrue(any("R02" in m for m in motifs), "quantité 'abc' doit être rejetée (type)")
        self.assertTrue(any(m == "R03" for m in motifs), "ticket vide doit être rejeté (obligatoire)")
        self.assertIn("SS-R05,SS-R06", motifs)
        self.assertIn("SS-R06", motifs)
        self.assertIn("SS-R07", motifs)
        self.assertTrue(all(r["_ligne_brute"] for r in quar.values()), "la ligne brute est conservée en quarantaine")

        s = self.spark.read.parquet(config.chemin("silver", "store_sales"))
        s.printSchema()
        types = dict(s.dtypes)
        self.assertEqual(types["ss_ticket_number"], "bigint")
        self.assertEqual(types["ss_sales_price"], "decimal(12,2)")
        dup = s.filter("ss_ticket_number = 8")
        self.assertEqual(dup.count(), 2, "deux lignes distinctes de même clé ne sont PAS supprimées")
        self.assertEqual(dup.filter("qa_cle_dupliquee").count(), 2)
        self.assertEqual(s.filter("ss_ticket_number = 7").count(), 1, "doublon exact : une seule occurrence")
        self.assertEqual(s.filter("ss_ticket_number = 7 AND qa_cle_dupliquee").count(), 0,
                         "après dédoublonnage exact, la ligne restante n'est plus une clé répétée")
        self.assertEqual(s.filter("ss_ticket_number = 9 AND qa_prix_nul").count(), 1)
        self.assertEqual(s.filter("ss_ticket_number = 10 AND qa_vente_a_perte AND qa_marge_negative").count(), 1)
        self.assertEqual(s.filter("ss_ticket_number = 11 AND ss_store_sk = 2").count(), 1, "espaces retirés avant typage")
        for col in ["_source_file", "_batch", "_ingested_at", "_silver_at", "_regles_version"]:
            self.assertIn(col, s.columns, f"provenance : {col}")
        s.orderBy("ss_ticket_number").select("ss_ticket_number", "ss_quantity", "qa_cle_dupliquee", "qa_prix_nul", "qa_vente_a_perte").show()

    def test_item_marque_vide_et_cle_dupliquee(self):
        L = [
            ligne("item", i_item_sk="1", i_brand=None),                                  # marque vide -> libellé
            ligne("item", i_item_sk="2", i_item_desc="  texte avec espaces  "),          # trim
            ligne("item", i_item_sk="3", i_current_price="0.00"),                        # prix invalide : signalé, conservé
            ligne("item", i_item_sk="4", i_item_id="X1"), ligne("item", i_item_sk="4", i_item_id="X2"),   # clé sk dupliquée
        ]
        self.bronze("item", L)
        controle, _ = silver.traiter(self.spark, "item")
        self.assertEqual(controle["lignes_bronze"], 5)
        self.assertEqual(controle["lignes_quarantaine"], 2, "clé de dimension dupliquée : les deux lignes à l'écart, aucun choix arbitraire")
        self.assertEqual(controle["bilan_conservation"], "OK")
        s = self.spark.read.parquet(config.chemin("silver", "item"))
        self.assertEqual(s.filter("i_item_sk = 1").first()["i_brand"], "Non renseigné")
        self.assertTrue(s.filter("i_item_sk = 1").first()["qa_marque_imputee"])
        self.assertEqual(s.filter("i_item_sk = 2").first()["i_item_desc"], "texte avec espaces")
        self.assertTrue(s.filter("i_item_sk = 3").first()["qa_prix_invalide"])
        self.assertTrue(s.filter("i_item_sk = 1").first()["est_version_courante"])
        q = self.spark.read.parquet(config.chemin("quarantaine", "item")).collect()
        self.assertTrue(all(r["_motifs_rejet"] == "R05" for r in q))


if __name__ == "__main__":
    unittest.main(verbosity=2)
