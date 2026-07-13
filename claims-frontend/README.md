# Claims vetting portal (minified frontend)

Standalone Quasar SPA for remote claims vetting. Uses the **same backend** as the main HMS app. Only users with the **Claims** role (primary or additional) can use this portal.

## Development

```bash
cd claims-frontend
npm install
npm run dev
```

Opens on http://localhost:9001 (main HMS frontend uses 9000).

Ensure the backend API is running on port 8000, or set `API_BASE_URL`:

```bash
API_BASE_URL=http://your-server:8000/api npm run dev
```

## Production build (subdomain)

Deploy the `dist/spa` folder to your subdomain root (e.g. `claims.mycompany.com` or `vet.mycompany.com`).

```bash
API_BASE_URL=https://app.mycompany.com/api npm run build
```

Copy `public/logos/` from the main `frontend/public/logos/` folder if logos are not already on the server.

### Apache

Use `public/.htaccess` (copied into `dist/spa` on build). Point the subdomain document root at `dist/spa`.

### Backend CORS

Add your claims subdomain to the API server `CORS_ORIGINS` environment variable, for example:

```
CORS_ORIGINS=https://claims.mycompany.com,https://app.mycompany.com
```

Local dev on port 9001 is already allowed in the backend defaults.

## Access rules

- Login uses the same credentials as the main app.
- User must have the **Claims** role; otherwise they see a message to use the main app on hospital premises.
- No license banner, companion mode, or other HMS modules.

## Routes

| Path | Purpose |
|------|---------|
| `/login` | Sign in |
| `/no-access` | Shown when account lacks Claims role |
| `/claims` | Module home (three cards) |
| `/claims/list` | Claims list |
| `/claims/correct-errors` | ClaimIT error correction |
| `/claims/ghims-import` | GHIMS XML import |
