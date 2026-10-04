import unittest
import os
import gc
import tempfile
from pathlib import Path
from core.report_parser import ConstructionReportParser
from database.construction_db import ConstructionDB
from core.excel_syncer import ConstructionExcelSyncer
from core.data_boss_brain import DataBossBrain

SAMPLE_REPORT = """Báo cáo thi công cuối ca đêm 26/9/2026:
* Nhà thầu SGC Cầu 5B:
1. Thi công ép cừ mố M2:
- Mố M2-1 & M2-2: 00/246/280
- Mố M2-3 & M2-4: 00/138/248
2. Gia công lồng thép điển hình
3. Thi công sàn đạo
- Cọc Casing : 02/20/132
- Tấm sàn: 00/18/155
4. Thi công cọc khoan nhồi :
00/14/106
- Mố M2-1: 0/3/7
+ Cọc M2-1-4: đang khoan
- Mố M2-2: 0/4/10
- Mố M2-3: 0/4/10
+ Cọc M2-3-6: Hạ ống thổi rửa chuẩn bị đổ bê tông
- Mố M2-4: 0/3/7
+ Cọc M2-4-1 đang hạ lồng thép L4-L3"""

class TestDataBoss(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_data.db"
        self.excel_path = Path(self.tmp_dir.name) / "test_report.xlsx"
        self.db = ConstructionDB(db_path=self.db_path)
        self.parser = ConstructionReportParser()
        self.syncer = ConstructionExcelSyncer(excel_path=self.excel_path)
        self.brain = DataBossBrain(self.db, self.syncer, self.parser)

    def tearDown(self):
        del self.brain
        del self.db
        del self.syncer
        del self.parser
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_parser(self):
        self.assertTrue(self.parser.is_construction_report(SAMPLE_REPORT))
        res = self.parser.parse(SAMPLE_REPORT, sender_name="Ninh")
        
        self.assertEqual(res["report_date"], "2026-09-26")
        self.assertIn("Đêm", res["shift_name"])
        self.assertIn("SGC Cầu 5B", res["contractor"])
        self.assertEqual(res["reporter_name"], "Ninh")
        
        # Check items count
        self.assertGreaterEqual(len(res["items"]), 8)
        
        # Check specific items
        casing = next(it for it in res["items"] if "Casing" in it["sub_item"])
        self.assertEqual(casing["shift_qty"], 2.0)
        self.assertEqual(casing["accumulated_qty"], 20.0)
        self.assertEqual(casing["design_qty"], 132.0)
        self.assertEqual(casing["completion_rate"], 15.2)

        # Check active piles
        self.assertEqual(len(res["piles"]), 3)
        piles_ids = [p["pile_id"] for p in res["piles"]]
        self.assertIn("Cọc M2-1-4", piles_ids)
        self.assertIn("Cọc M2-3-6", piles_ids)
        self.assertIn("Cọc M2-4-1", piles_ids)

    def test_database_and_excel_flow(self):
        # Process report
        out = self.brain.process_incoming_report(
            SAMPLE_REPORT,
            sender_name="Ninh",
            project_name="PMU BĂNG HẠ TẦNG OLP"
        )
        self.assertGreater(out["report_id"], 0)
        self.assertTrue(os.path.exists(self.excel_path))
        self.assertIn("ĐÃ NẠP DATA", out["reply_text"])
        self.assertIn("246/280", out["reply_text"])

        # Check summaries
        summary = self.db.get_latest_project_summary()
        self.assertGreater(len(summary), 0)

        active_piles = self.db.get_active_piles()
        self.assertEqual(len(active_piles), 3)

        overview_text = self.brain.get_progress_overview()
        self.assertIn("TIẾN ĐỘ DỰ ÁN", overview_text)

        alert_text = self.brain.get_risk_and_alerts()
        self.assertIn("CẢNH BÁO TIẾN ĐỘ", alert_text)

    def test_html_dashboard_syncer(self):
        from core.html_dashboard_syncer import HtmlDashboardSyncer
        html_syncer = HtmlDashboardSyncer()
        if html_syncer.html_path.exists():
            store = html_syncer.read_store()
            self.assertIn("data", store)
            self.assertIn("items", store["data"])
            self.assertIn("daily", store["data"])

            res = self.parser.parse(SAMPLE_REPORT, sender_name="Ninh")
            sync_res = html_syncer.update_from_report(res)
            self.assertGreater(sync_res["updated_count"], 0)

if __name__ == "__main__":
    unittest.main()
