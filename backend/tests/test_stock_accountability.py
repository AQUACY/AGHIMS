"""Name matching and the GHIMS dispense-report parser."""
from pathlib import Path

from app.services.dispense_report_parser import parse_dispense_report
from app.services.stock_names import match_drug, names_compatible


SAMPLE = """
<html><body>
<div class="topic">Dispense Statistics By Drug</div>
<div>From 26 Oct 2026 to 30 Oct 2026</div>
<b>ASESEWA GOVERNMENT HOSPITAL</b>
<div class="insuranceGroup">SELF</div>
<div class="insuranceScheme">SELF PAY / UNINSURED - GH</div>
<table class="tablePage"><tr class="billRow">
<th>Drug ID</th><th>Drug Name</th><th>Quantity Sold</th><th>Amount (GHC)</th>
</tr>
<tr class="billRow"><td>DRG1</td><td>Paracetamol Tablet 500mg</td><td>10</td><td>1.5</td></tr>
<tr class="billRow"><td></td><td>TOTAL</td><td>10</td><td>1.5</td></tr>
</table>
<div class="insuranceGroup">NHIS</div>
<div class="insuranceScheme">NATIONAL HEALTH INSURANCE SCHEME</div>
<table class="tablePage">
<tr class="billRow"><td>DRG1</td><td>Paracetamol Tablet 500mg</td><td>5</td><td>0</td></tr>
</table>
</body></html>
"""


def test_parser_sums_across_payers_and_reads_dates():
    parsed = parse_dispense_report(SAMPLE)
    assert parsed["facility_name"] == "ASESEWA GOVERNMENT HOSPITAL"
    assert parsed["period_from"].isoformat() == "2026-10-26"
    assert parsed["period_to"].isoformat() == "2026-10-30"
    assert len(parsed["lines"]) == 2
    assert parsed["lines"][0]["payer_group"] == "SELF"
    assert parsed["lines"][1]["payer_group"] == "NHIS"
    assert parsed["lines"][1]["quantity_sold"] == 5


def test_sheet_names_match_ghims_names():
    pairs = [
        ("TAB. GLIMEPIRIDE 2MG", "Glimepiride Tablet 2mg"),
        ("TAB. LOSARTAN 50MG", "Losartan Tablet 50mg"),
        ("TAB. PARACETAMOL", "Paracetamol Tablet 500mg"),
        ("TAB. IBUPROFEN 400MG", "Ibuprofen Tablet 400mg"),
        ("TAB. NIFEDIPINE (XL) 30MG", "Nifedipine Tablet 30mg"),
        ("TOP. DICLOFENAC GEL", "Diclofenac Gel"),
        ("TAB. VITAMIN B1 B6 B12 (B DENK)", "Vitamin B-Denk Tablet"),
        ("EXAMINATION GLOVES 20'S", "Pharmacy Examination Gloves"),
        ("TAB. LISINOPRIL+HTZ 20/12.5MG", "Lisinopril + Hydrochlorthiazide Tablet (20 Mg + 12.5 Mg)"),
        ("TAB. METRONIDAZOLE 400MG", "Metronidazole Tablet 400mg"),
        ("TAB. OMEPRAZOLE 20MG 14S", "Omeprazole Capsules 20mg"),
    ]
    for sheet_name, ghims_name in pairs:
        assert names_compatible(sheet_name, ghims_name), (sheet_name, ghims_name)


def test_different_strengths_and_forms_do_not_match():
    assert not names_compatible(
        "TAB. LISINOPRIL+HTZ 10/12.5MG",
        "Lisinopril + Hydrochlorthiazide Tablet (20 Mg + 12.5 Mg)",
    )
    assert not names_compatible("TAB. LISINOPRIL 10MG", "Lisinopril Tablet 5mg")
    assert not names_compatible("TAB. METRONIDAZOLE 200MG", "Metronidazole Tablet 400mg")
    assert not names_compatible("TAB. PARACETAMOL", "Paracetamol Syrup")
    assert not names_compatible("TAB. IBUPROFEN 400MG", "Ibuprofen Suspension")


def test_ambiguous_paracetamol_strengths_are_not_forced():
    result = match_drug(
        "TAB. PARACETAMOL",
        [
            {"drug_id": "A", "drug_name": "Paracetamol Tablet 500mg"},
            {"drug_id": "B", "drug_name": "Paracetamol Tablet 1000mg"},
        ],
    )
    assert result.ambiguous
    assert result.drug_id is None


def test_real_dispense_file_if_present():
    path = Path(r"c:\Users\Surface\Downloads\download.xls")
    if not path.exists():
        return
    parsed = parse_dispense_report(path.read_text(encoding="utf-8", errors="replace"))
    assert parsed["period_from"].isoformat() == "2026-10-26"
    sold = {}
    for line in parsed["lines"]:
        sold[line["drug_id"]] = sold.get(line["drug_id"], 0) + line["quantity_sold"]
    drugs = [{"drug_id": drug_id, "drug_name": name} for drug_id, name in {
        line["drug_id"]: line["drug_name"] for line in parsed["lines"]
    }.items()]
    glimepiride = match_drug("TAB. GLIMEPIRIDE 2MG", drugs)
    assert glimepiride.drug_name == "Glimepiride Tablet 2mg"
    assert sold[glimepiride.drug_id] == 120
