# License Portal v2

Self-serve HMS license renewals: you create each hospital account with a custom GH₵ amount and duration. Their IT manager logs in, pays with Paystack, then HMS pulls the paid month automatically (or via **Renew from portal**). Invoice and receipt PDFs are for management. JSON download remains a backup.

**Monthly packages:** at hospital setup you set the **current license end** (renewal deadline), e.g. 31 Aug 2026 11:59 PM. Paying then buys the next month from that moment: 1 Sep 12:00 AM through 30 Sep 23:59:59. After payment the deadline moves forward, so next month they only sign in and pay again (Starlink / Netflix style).

The existing Python portal in `license-portal/` is unchanged. Point `LICENSE_VERIFY_URL` at this app when you cut over.

## What it does

- **Admin** creates a hospital (name, facility code, amount, months, IT login). Password is shown once so you can send it on WhatsApp or email.
- **IT manager** signs in, pays the amount on Paystack (card or mobile money), then:
  - HMS applies the paid month automatically when it starts, or Admin/Management clicks **Renew from portal**
  - Invoice PDF — amount due
  - Receipt PDF — proof Paystack succeeded
  - License JSON remains downloadable per paid month as a backup
- IT managers can change their own password under **Profile**.
- **Admin** can upload a portal logo (site + invoice/receipt letterhead) and can still issue a license without Paystack (bank transfer).
- HMS online check: `POST /api/verify/online` with header `X-License-Server-Key` (same contract as v1).

## Local run

```bash
cd license-portal-v2
cp env.example .env
# set PORTAL_ADMIN_PASSWORD, ISSUER_SLUG, VERIFY_SHARED_SECRET, RSA_PRIVATE_KEY_FILE
# optionally Paystack test keys
npm install
npm start
```

Open http://127.0.0.1:9500

Default database is SQLite (`./data/license_portal_v2.db`). RSA key:

```bash
openssl genrsa -out license_private.pem 3072
openssl rsa -in license_private.pem -pubout -out license_public.pem
```

Put the public key on each HMS server (`LICENSE_RSA_PUBLIC_KEY_FILE`). Keep the private key only on this portal.

Signing self-test:

```bash
npm run test:sign
```

## Hostinger (Business / Node.js)

### Auto-deploy from GitHub

This repo includes [`.github/workflows/deploy-hostinger.yml`](../.github/workflows/deploy-hostinger.yml). On push to `main` (or `license-portal-hosting`) it tests the portal, zips `license-portal-v2` (no `.env`, no private key, no `data/`), uploads it to Hostinger, and starts a Node.js build.

1. In hPanel create the **Node.js web app** for your domain (Express / Other, entry file `app.js`, Node 22).
2. Set production values under the app’s **Environment variables** (same keys as `.env`). Keep `license_private.pem` on the server, outside the public folder.
3. hPanel → **API** → create a token.
4. GitHub repo → **Settings** → **Secrets and variables** → **Actions**:
   - `HOSTINGER_API_TOKEN`
   - `HOSTINGER_DOMAIN` — exact domain from hPanel, no `https://` (example: `licenses.example.com`)
   - `HOSTINGER_USERNAME` — optional; FTP user like `u123456789` (not `u123456789.domain.com`)
5. Push, or **Actions** → **Deploy license portal to Hostinger** → **Run workflow**.

You can instead skip the workflow and use Hostinger’s GitHub button: connect repo `AGHIMS`, **root directory** `license-portal-v2`, entry file `app.js`. Then every push to the connected branch deploys without Actions.

### Manual Hostinger setup

1. Create a MySQL database in hPanel. Put the credentials in environment variables with `DATABASE_MODE=mysql`. Set `MYSQL_HOST=127.0.0.1` (not `localhost` — Node would connect as IPv6 `::1` and Hostinger denies that user). Do not wrap the password in quotes. The MySQL user must be **assigned** to the database with ALL PRIVILEGES.
2. Create a Node.js application (Node 18+). Application root = this folder. Startup file:
   - `src/server.js`, or
   - `app.js` (loads the same server — some hPanel layouts expect `app.js` in the app root)
3. Set `PORT` from Hostinger (do not hard-code). The app already listens on `process.env.PORT`.
4. Store `license_private.pem` **outside** `public_html` / the public folder, e.g. `/home/USER/license_private.pem`, and set `RSA_PRIVATE_KEY_FILE` to that path.
5. `PUBLIC_BASE_URL=https://your-domain.tld` (no trailing slash).
6. Paystack dashboard:
   - Callback is `${PUBLIC_BASE_URL}/pay/return`
   - Webhook `https://your-domain.tld/api/paystack/webhook` (event `charge.success`)
7. SSL must be on. Set `COOKIE_SECURE=true`.
8. `npm install --omit=dev` then start. Tables are created on boot.

### Environment (production)

See `env.example`. Required on Hostinger:

- `DATABASE_MODE=mysql` and MySQL host/user/password/database
- `ISSUER_SLUG` (same as HMS `LICENSE_ISSUER_SLUG`)
- `RSA_PRIVATE_KEY_FILE`
- `VERIFY_SHARED_SECRET` (HMS sends this as `LICENSE_VERIFY_API_KEY` / `X-License-Server-Key`)
- `PORTAL_ADMIN_EMAIL` / `PORTAL_ADMIN_PASSWORD` (admin is seeded only if no admin user exists)
- `PORTAL_JWT_SECRET`
- `PUBLIC_BASE_URL`
- `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY`
- Company letterhead: `COMPANY_NAME`, `COMPANY_ADDRESS`, `COMPANY_PHONE`, `COMPANY_EMAIL`, `COMPANY_TIN`

### HMS cutover

On each hospital server, set:

```
LICENSE_VERIFY_URL=https://your-domain.tld/api
LICENSE_VERIFY_API_KEY=<VERIFY_SHARED_SECRET>
```

Re-create each live hospital in v2 admin (or import v1 `license_registry` rows yourself). Same `license_id` keeps online verify matching if you copy it into the v2 `licenses` table.

## API (short)

| Method | Path | Who |
|--------|------|-----|
| POST | `/api/auth/login` | public |
| GET | `/api/me` | signed in |
| POST | `/api/me/password` | signed in |
| POST | `/api/pay/initialize` | customer |
| GET | `/api/pay/status?reference=` | owner / admin |
| GET | `/api/license/signed.json` | customer |
| POST | `/api/license/current` | HMS (`X-License-Server-Key`) |
| GET | `/api/documents/:id.pdf` | owner / admin |
| POST | `/api/admin/branding/logo` | admin |
| POST | `/api/admin/customers` | admin |
| PATCH | `/api/admin/customers/:id` | admin |
| POST | `/api/admin/customers/:id/issue-manual` | admin |
| POST | `/api/verify/online` | HMS |
| POST | `/api/paystack/webhook` | Paystack |

License JSON shape is unchanged from v1: `{ claims, signature_b64 }` with RSA-SHA256 PKCS#1 v1.5.
