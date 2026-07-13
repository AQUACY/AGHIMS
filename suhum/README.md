# Suhum

Standalone portal for **price list management** and **GHIMS XML claim import/editing**. Own database, own users — price list data can be synced from the main HMS.

## Structure

```
suhum/
  backend/     FastAPI on port 8110
  frontend/    Quasar SPA on port 9002
```

## Quick start (development)

### Backend

```bash
cd suhum/backend
cp env.example .env
# Edit .env — set NHIA credentials for Get CCC, MAIN_DATABASE_URL for sync script
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8110
```

Default login (first run only): `admin` / `suhum123` — change in `.env` via `SUHUM_ADMIN_USERNAME` / `SUHUM_ADMIN_PASSWORD`.

### Frontend

```bash
cd suhum/frontend
npm install
npm run dev
```

Open http://localhost:9002

### Sync price list from main HMS

After setting `MAIN_DATABASE_URL` in `suhum/backend/.env`:

```bash
cd suhum/backend
python scripts/sync_price_list_from_main.py
python scripts/sync_price_list_from_main.py --dry-run   # preview counts only
```

Copies: `procedure_prices`, `surgery_prices`, `product_prices`, `unmapped_drg_prices`, `icd10_drg_mappings`.

## Production

- Build frontend: `API_BASE_URL=https://your-suhum-api.example.com/api npm run build`
- Deploy `frontend/dist/spa` to your subdomain
- Run backend with gunicorn/uvicorn on port 8100 (or behind reverse proxy)
- Add frontend origin to `CORS_ORIGINS` in backend `.env`

## Modules

| Route | Purpose |
|-------|---------|
| `/home` | Module home |
| `/price-list` | Price list upload, search, ICD-10 mappings |
| `/icd10-drg-mapping` | ICD-10 DRG mapping management (list, add, edit, upload, export) |
| `/ghims-import` | GHIMS XML import batches |
| `/ghims-import/item/:id` | Edit imported claim (same UX as main HMS) |
| `/users` | User management (admins only) |

Main HMS keeps its own price list module; both can coexist.
