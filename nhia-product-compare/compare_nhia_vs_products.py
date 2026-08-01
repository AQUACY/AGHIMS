"""
Compare NHIA medication list vs exported product_price_list.
Writes an Excel workbook with the original product list plus a sheet of
missing NHIA drugs in the same product_list column template.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
NHIA_FILE = BASE / "NHIA List (1).xlsx"
PRODUCT_FILE = BASE / "product_price_list.csv"
OUTPUT_XLSX = BASE / "product_price_list_with_missing_nhia.xlsx"
OUTPUT_CSV = BASE / "missing_nhia_drugs_for_upload.csv"

PROD_COLS = [
    "Product N",
    "Medication Code",
    "Product Name",
    "Sub Category 1",
    "Sub Category 2",
    "Product ID",
    "Formulation",
    "Strength",
    "Base Rate",
    "NHIA App",
    "NHIA Claim Co-Payment",
    "Claim Amount",
    "NHIA Claim",
    "Bill Effective",
    "Insurance Covered",
    "Is Active",
]

FORMULATION_KEYWORDS = [
    ("dispersible tablet", "Tablet"),
    ("dispersible tablets", "Tablet"),
    ("eye ointment", "Ointment"),
    ("eye drops", "Drops"),
    ("oral suspension", "Suspension"),
    ("oral solution", "Solution"),
    ("injection", "Injection"),
    ("infusion", "Infusion"),
    ("suspension", "Suspension"),
    ("solution", "Solution"),
    ("syrup", "Syrup"),
    ("mixture", "Mixture"),
    ("elixir", "Elixir"),
    ("capsule", "Capsule"),
    ("tablets", "Tablet"),
    ("tablet", "Tablet"),
    ("pessary", "Pessary"),
    ("suppository", "Suppository"),
    ("ointment", "Ointment"),
    ("cream", "Cream"),
    ("gel", "Gel"),
    ("lotion", "Lotion"),
    ("inhaler", "Inhaler"),
    ("nebules", "Nebules"),
    ("powder", "Powder"),
    ("drops", "Drops"),
]

UNIT_TO_FORMULATION = {
    "tablet": "Tablet",
    "capsule": "Capsule",
    "vial": "Injection",
    "ampoule": "Injection",
    "inhaler": "Inhaler",
    "supp": "Suppository",
    "supp.": "Suppository",
    "pessary": "Pessary",
    "sachet": "Powder",
    "dose": "Nebules",
    "tube": "Ointment",
    "bottle": "Solution",
}


def clean_text(val) -> str:
    if pd.isna(val):
        return ""
    text = str(val).replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_formulation_and_strength(generic: str, unit: str):
    name = clean_text(generic)
    unit_c = clean_text(unit)
    formulation = None
    strength = None

    lower = name.lower()
    for key, form in FORMULATION_KEYWORDS:
        if key in lower:
            formulation = form
            break

    if not formulation:
        unit_key = unit_c.lower()
        formulation = UNIT_TO_FORMULATION.get(unit_key)
        if not formulation:
            if re.search(r"pess", unit_key):
                formulation = "Pessary"
            elif re.search(r"supp", unit_key):
                formulation = "Suppository"

    patterns = [
        r"(\d+\s*:\s*\d[\d,]*)",
        r"(\(\s*\d+\s*\+\s*\d+\s*\)\s*mg)",
        r"(\(\s*\d+(?:\.\d+)?\s*mg\s*\+\s*\d+(?:\.\d+)?\s*mg\s*\))",
        r"(\d+(?:\.\d+)?\s*mg\s*\+\s*\d+(?:\.\d+)?\s*mg)",
        r"(\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|iu|mu|units?|%)(?:\s*/\s*\d+(?:\.\d+)?\s*(?:mL|ml|L))?)",
        r"(\d+(?:\.\d+)?\s*micrograms?(?:\s*/\s*\d+(?:\.\d+)?\s*(?:mL|ml))?)",
        r"(\d+(?:\.\d+)?\s*units?\s*/\s*mL(?:\s+in\s+\d+\s*mL)?)",
    ]
    for pat in patterns:
        m = re.search(pat, name, re.I)
        if m:
            strength = re.sub(r"\s+", " ", m.group(1)).strip()
            break

    if not strength and "," in name:
        after = name.split(",")[-1].strip()
        if re.search(r"\d", after):
            strength = after

    return formulation, strength, name


def to_product_name(generic_clean: str) -> str:
    # Drop separator commas ("Tablet, 10 mg") but keep thousands commas ("1:10,000")
    name = re.sub(r",\s+", " ", generic_clean)
    return re.sub(r"\s+", " ", name).strip()


def main() -> None:
    nhia = pd.read_excel(NHIA_FILE)
    prod = pd.read_csv(PRODUCT_FILE)

    pharmacy = prod[
        prod["Sub Category 2"].astype(str).str.strip().str.lower() == "pharmacy"
    ].copy()
    existing_codes = set(
        prod["Medication Code"].dropna().astype(str).str.strip().str.upper()
    )

    nhia = nhia.copy()
    nhia["code_norm"] = nhia["CODE"].astype(str).str.strip().str.upper()
    missing_nhia = nhia[~nhia["code_norm"].isin(existing_codes)].copy()
    missing_nhia = missing_nhia.sort_values("CODE").reset_index(drop=True)

    rows = []
    for _, r in missing_nhia.iterrows():
        code = clean_text(r["CODE"]).upper()
        formulation, strength, generic_clean = parse_formulation_and_strength(
            r["GENERIC NAME, DOSAGE FORM, STRENGTH"], r["UNIT OF PRICING"]
        )
        product_name = to_product_name(generic_clean)
        product_n = f"{product_name} ({code} | {product_name})"
        price = float(r["PRICE (GHC)"]) if pd.notna(r["PRICE (GHC)"]) else None

        rows.append(
            {
                "Product N": product_n,
                "Medication Code": code,
                "Product Name": product_name,
                "Sub Category 1": 4,
                "Sub Category 2": "Pharmacy",
                "Product ID": None,
                "Formulation": formulation,
                "Strength": strength,
                "Base Rate": 0.0,
                "NHIA App": None,
                "NHIA Claim Co-Payment": 0.0,
                "Claim Amount": price,
                "NHIA Claim": None,
                "Bill Effective": "01-03-2025",
                "Insurance Covered": "yes",
                "Is Active": True,
            }
        )

    missing_df = pd.DataFrame(rows, columns=PROD_COLS)

    prod_out = prod.copy()
    for c in PROD_COLS:
        if c not in prod_out.columns:
            prod_out[c] = None
    prod_out = prod_out[PROD_COLS]

    summary = pd.DataFrame(
        [
            {"Metric": "NHIA total drugs", "Count": len(nhia)},
            {"Metric": "Product list total rows", "Count": len(prod)},
            {"Metric": "Pharmacy rows in product list", "Count": len(pharmacy)},
            {
                "Metric": "NHIA codes already in product list",
                "Count": int(nhia["code_norm"].isin(existing_codes).sum()),
            },
            {"Metric": "NHIA codes missing (to add)", "Count": len(missing_df)},
        ]
    )

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        prod_out.to_excel(writer, sheet_name="product_list", index=False)
        missing_df.to_excel(writer, sheet_name="missing_nhia_drugs", index=False)
        summary.to_excel(writer, sheet_name="summary", index=False)
        missing_nhia.drop(columns=["code_norm"]).to_excel(
            writer, sheet_name="missing_nhia_source", index=False
        )

    missing_df.to_csv(OUTPUT_CSV, index=False)

    print(summary.to_string(index=False))
    print(f"\nWrote {OUTPUT_XLSX}")
    print(f"Wrote {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
