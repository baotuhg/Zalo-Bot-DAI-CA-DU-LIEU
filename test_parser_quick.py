from core.report_parser import ConstructionReportParser

sample = '''Báo cáo thi công cuối ca đêm 26/9/2026:
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
+ Cọc M2-4-1 đang hạ lồng thép L4-L3'''

parser = ConstructionReportParser()
res = parser.parse(sample, sender_name='Ninh')

print(f"Date: {res['report_date']} | Shift: {res['shift_name']} | Contractor: {res['contractor']} | Reporter: {res['reporter_name']}")
print("\n=== ITEMS PARSED ===")
for it in res['items']:
    print(f"{it['category']} -> {it['sub_item']} | Ca này: {it['shift_qty']} | Lũy kế: {it['accumulated_qty']}/{it['design_qty']} ({it['completion_rate']}%) {it['unit']}")

print("\n=== PILES IN PROGRESS ===")
for p in res['piles']:
    print(f"[{p['location']}] {p['pile_id']}: {p['status']}")
