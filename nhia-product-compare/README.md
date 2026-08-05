# NHIA ↔ Product list tools

## Files
- `NHIA List (1).xlsx` — official NHIA medication list (CODE column)
- `compare_nhia_vs_products.py` — find NHIA codes missing from an exported CSV
- `sync_products_to_nhia_list.py` — activate only NHIA pharmacy products in the live DB
- `missing_nhia_drugs_for_upload.csv` — ready-to-upload rows for codes that were missing

## Recommended facility cutover

1. **Upload** any missing NHIA drugs (`missing_nhia_drugs_for_upload.csv`) as file type `product`.
2. **Preview sync** (no DB writes) — always uses `backend/.env` (MySQL):

```bash
backend/venv/Scripts/python.exe nhia-product-compare/sync_products_to_nhia_list.py
```

You should see something like `Using database: mode=mysql → localhost:3306/hms...` and a non-zero product row count. If it says sqlite / 0 rows, the wrong DB was used.

3. **Apply sync** (Pharmacy only — consumables left alone):

```bash
backend/venv/Scripts/python.exe nhia-product-compare/sync_products_to_nhia_list.py --apply
```

That activates every Pharmacy product whose `medication_code` is in the NHIA list, and archives the rest of Pharmacy.

## Clear a whole category in the app

Price List Management → **Clear category…**

- Choose `product` (or another type)
- Optionally limit to sub-category `Pharmacy`
- Prefer **Archive** (recoverable via Status = Archived)
- Type the category name to confirm, then re-upload the new list
