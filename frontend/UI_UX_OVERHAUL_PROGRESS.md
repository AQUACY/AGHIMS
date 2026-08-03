# UI/UX Overhaul Progress

> Complete frontend redesign of AGHIMS into an Apple-inspired, enterprise healthcare SaaS experience.  
> Backend APIs, auth, schemas, and business logic remain untouched.

**Started:** 2026-08-03  
**Status:** In progress — Companion module done; next remaining modules

---

## Migration Order

| # | Module | Status | Notes |
|---|--------|--------|-------|
| 1 | Design System | ✅ Done | Tokens, Tailwind, core UI + HmsDataTable |
| 2 | Authentication | ✅ Done | Login — polished |
| 3 | Main Layout | ✅ Done | Sleek ghost header actions |
| 4 | Sidebar | ✅ Done | Floating glass, groups, favorites, recents |
| 5 | Header | ✅ Done | Quiet chrome, chips, Ctrl+K |
| 6 | Dashboard | ✅ Done | Dense enterprise stats + action rows |
| 7 | Patient Registration | ✅ Done | Header + section hints + banner polish |
| 8 | Patient Search | ✅ Done | Premium HmsDataTable, badges, Open CTA |
| 9 | Patient Profile | ✅ Done | Sticky hero, demography/bill/IPD panels, DS actions |
| — | Choose Mode | ✅ Done | Full DS redesign (was legacy) |
| — | License banner | ✅ Done | Soft DS styling; logic preserved |
| 10 | OPD | ✅ Done | Consultation workspace + Vitals dialog (no separate OPD hub) |
| 11 | IPD | ✅ Done | Hub + all IPD sub-pages (station, manager, clinical tools, transfers, beds, registers) |
| 12 | Emergency | ✅ Done | Department filter/label in OPD flow; no separate Emergency board |
| 13 | Appointments | ✅ Done | Zendenta day/week calendar grid |
| 14 | Consultation | ✅ Done | Picker + sticky patient hero; clinical panels restyled |
| 15 | Vital Signs | ✅ Done | Premium encounter table + dialog chrome |
| 16 | Nursing | ⏳ Pending | |
| 17 | Laboratory | ✅ Done | Board + result entry (hero, templates, sample ID) |
| 18 | Radiology | ✅ Done | Scan/X-ray boards + result entry pages |
| 19 | Pharmacy | ✅ Done | Main pharmacy board (confirm/dispense); requisitions chrome done with inventory ops |
| 20 | Prescriptions | ✅ Done | Covered by Pharmacy.vue (no separate page) |
| 21 | Billing | ✅ Done | Main OPD/IPD billing chrome; companion billing chrome done |
| 22 | NHIS Claims | ✅ Done | All Claims routes: hub, list, dashboard, reports, editors, import, ClaimIT, CFX, templates, price list, ICD |
| 23 | Inventory | ✅ Done | Hub, stock, requisitions, ward stock, debits, reports, store/ward admin; layout header polished |
| 24 | Theatre | ⏳ Pending | |
| 25 | Maternity | ⏳ Pending | |
| 26 | Reports | ⏳ Pending | |
| 27 | Staff Management | ⏳ Pending | |
| 28 | Settings | ⏳ Pending | |
| 29 | User Profile | ⏳ Pending | |
| 30 | Notifications | ⏳ Pending | Panel chrome polished; content TBD |
| 31 | Remaining Modules | 🔄 Partial | Companion done; Theatre, Maternity, Staff, Settings, Nursing, Reports TBD |

**Legend:** ✅ Done · 🔄 In progress / partial · ⏳ Pending · ⚠️ Blocked

---

## Change Log

### 2026-08-03 — Companion
- [x] **CompanionLayout** — quiet header (mode chip, ghost actions); softened drawer nav
- [x] **Companion hub** — Claims-style workspace cards (Service list / Create / Billing) with motion
- [x] **Visit list / Create service** — HmsPageHeader + diag-panels; APIs untouched
- [x] **Visit detail** — sticky claim-hero, account summary panel, add-service HmsCards
- [x] **Billing** — search/export panels + sticky visit hero; dialog chrome only (payment APIs untouched)
- [x] **Inventory debit** — sticky visit hero + form/history panels
- [x] **Add* service pages** (Lab/Scan/Xray/Surgery/Dressing/Drugs/Oxygen) — batch DS chrome + compact visit hero
- [ ] Shared admin under companion (Staff / Audit / Facility / Transactions / Undertakings) — with those modules
- [ ] Full Companion AppSidebar parity — deferred (custom drawer kept)

### Next up
1. Remaining modules (Nursing, Reports, Staff, Settings, Theatre, Maternity)

### 2026-08-03 — Inventory
- [x] **InventoryLayout** — quiet header chrome (ghost actions, mode chip); nav active pill softened
- [x] **Inventory hub** — HmsPageHeader, filter/KPI/chart/activity panels, Lucide quick-link cards
- [x] **Store stock** — tabs + diag panels; approve/reject/edit dialogs preserved
- [x] **Requisitions / Create requisition** — boards + dialog chrome; workflows untouched
- [x] **Ward stock / Inventory debits / Reports** — DS headers + filter/KPI/table panels
- [x] **Store / Ward management** — admin chrome; APIs untouched
- [ ] Full Inventory AppSidebar parity — deferred (custom drawer kept)

### 2026-08-03 — Lab + Radiology boards
- [x] **Laboratory** — HmsPageHeader, diag toolbar (date range, lock), panel + HmsBadge; multi-select/bulk confirm kept
- [x] **Scan / Imaging** — same chrome; procedure filter + lock; Update/Add Service dialogs preserved
- [x] **X-ray** — same chrome (no lock); Add Service preserved
- [x] **Result pages** — LabResult / ScanResult / XrayResult: sticky patient hero, investigation meta panel, form panel + HmsButton save; templates/sample ID/attachments/payment gating preserved

### 2026-08-03 — NHIS Claims (premium polish)
- [x] Global Claims surfaces — softer white cards, table density, sticky claim heroes (Zendenta-inspired)
- [x] Claims hub — workspace groups with Dashboard-style action cards + motion
- [x] Claims dashboard — premium KPI cards with pastel icons
- [x] Edit / Generate / GHIMS import editors — sticky identity heroes (avatar, meta chips, status)
- [x] Claims list — pill filters/segments; shared panel elevation

### 2026-08-03 — NHIS Claims (full module)
- [x] **Claims hub** — grouped Daily work / Import & fix / References cards with motion + Lucide
- [x] **Claims list** — HmsPageHeader, export-by-date panel, finalized encounters panel (lock + OPD/IPD/Other/All), HmsBadge status, HmsButton actions; q-table / export APIs untouched
- [x] **Claims dashboard** — DS header + filter panel, KPI row, chart/advice panels; analytics APIs untouched
- [x] **Import GHIMS XML** — DS header, upload + recent-import panels, batch view in diag panels; import/export/vet APIs untouched
- [x] **Claims reports** — stub with DS header + empty panel
- [x] **EditClaim / GhimsImportedClaimEdit** — HmsPageHeader with status badges + prev/next nav; form sections / APIs untouched
- [x] **GenerateClaim** — DS header + diag-panel section cards; generate API untouched
- [x] **ClaimIT Correct Errors** — upload + batch list panels; batch detail banners/actions preserved
- [x] **CFX Convert & Diff** — segment tabs, convert/diff panels, result tables; dialog chrome polished
- [x] **Diagnosis templates** — filters + table panels; create/edit dialog polished
- [x] **Price list / ICD-10 DRG mapping** — DS headers + upload/filter/table panels (shared admin routes benefit too)

### Next up
1. Remaining modules (Nursing, Reports, Staff, Settings, Theatre, Maternity)

### 2026-08-03 — OPD / Emergency
- [x] **OPD clinical flow** — Consultation workspace: vitals/complaints/diagnoses/Rx/investigations/notes/follow-up/outcome as `diag-panel`s; HmsButton actions + HmsBadge statuses; finalize/draft action bar
- [x] **Vitals dialog** — HmsButton save/cancel; inventory debit banners restyled (APIs untouched)
- [x] **Emergency** — covered as department within OPD calendar/consultation (no dedicated A&E board; deferred unless product wants one)

### 2026-08-03 — Pharmacy / Prescriptions
- [x] **Pharmacy** — HmsPageHeader + Direct prescription CTA; search panel; sticky patient hero with balance pill; OPD/IPD service cards; diagnoses/vitals/payment panels; prescriptions toolbar (All/New segment, print/add actions); status HmsBadges; itemized confirm panel; dispense dialog header polish; confirm/dispense/return/print APIs untouched
- [x] Pharmacy requisitions / ward stock / inventory debits — DS chrome with Inventory wave

### 2026-08-03 — Billing
- [x] **Billing** — HmsPageHeader + OPD/IPD segment; sticky patient hero; search / encounter / diagnoses / bill items / existing bills as diag panels; HmsBadge paid status + HmsButton row actions; key dialog headers polished; receipt/payment/recalc APIs untouched
- [x] Companion billing — DS chrome with Companion wave (see Companion billing + debit chrome)

### 2026-08-03 — OT calendar + Admission Manager workspace
- [x] **Operation theatre calendar** — day/week grid like Reservations (ward columns, time axis, now line, status tones); edit/anaesthetist dialogs preserved
- [x] **Admission manager** — compact emergency strip; activities + sticky grouped quick actions (Patient / Clinical / Docs / Discharge)
- [x] **AM activity board** — replaced Quasar notes table with segmented Diagnoses / Notes / Surgeries / Reviews / Services panes, premium list rows, HmsBadge/HmsButton actions
- [x] **Treatment sheet** — day calendar strip + per-med dose slot tickers (no long multi-day expansion lists)
- [x] **Nurse note dialog** — polished composer, draft banner, previous-notes cards
- [x] **AM destinations** — Clinical Review, Treatment Sheet, Nurse Mid Docs, Inventory Debit, Blood Request → `am-panel` sections + HmsButton primaries; sticky patient heroes on debit/blood

### 2026-08-03 — IPD sub-pages
- [x] **Doctor / Nursing station** — ward toolbar, transfer rows, motion patient grid, empty states
- [x] **Admission manager** — sticky patient hero + balance pill; activity panels keep logic
- [x] **Clinical review / Treatment sheet / Nurse mid docs** — page header + sticky patient hero
- [x] **Admit / Recommendations / Transfer / Acceptance / Beds / Registers / Daily ward / OT calendar** — HmsPageHeader chrome + glass panel polish
- [x] **Inventory debit / Blood transfusion request** — DS headers; forms preserved
- [ ] Ward / Store management — inventory-mode shared; deferred with Inventory wave

### 2026-08-03 — Clinical modules wave
- [x] **IPD hub** — grouped Patient flow / Ward / Theatre cards with hover motion
- [x] **Vitals** — HmsDataTable encounter board, date nav, status badges, dialog header polish
- [x] **Consultation** — encounter picker board + sticky patient hero (balance pill, change encounter); workspace glass cards restyled
- [x] Appointments calendar already shipped prior

### 2026-08-03 — Sidebar brand + Reservations calendar
- [x] Sidebar brand slot = facility name (not AGHIMS)
- [x] Meta card chips: facility code · mode · license
- [x] Header de-duplicated (facility/mode/license live in sidebar)
- [x] Appointment Calendar → Zendenta-style day grid (dept columns, time axis, now line, pastel cards) + week view

### 2026-08-03 — Sidebar remodel (Zendenta layout)
- [x] Flush panel sidebar (not floating glass inset)
- [x] Brand row (logo + AGHIMS) + collapse
- [x] Facility card (name + code/mode) like clinic switcher
- [x] Soft blue active pill + left accent bar
- [x] Favorites + Recently used retained above module groups
- [x] Patient search kept under facility card

### 2026-08-03 — Enterprise polish (Zendenta-aligned)
- [x] Light tokens → soft clinical canvas (`#f5f7fb`), quieter shadows
- [x] Sidebar active state with accent bar; cleaner shell
- [x] Header search pill (Ctrl+K); mobile icon-only
- [x] Dashboard workspace panel + hover/press motion on stats/actions
- [x] Patient Search — count meta, circular avatars, pill filter, Add patient CTA
- [x] Patient Profile — name as hero, section titles subordinate, mobile action stack
- [x] Registration — DS search row + found-patient panel
- [x] Choose Mode — hover/press gestures
- [x] HmsDataTable / PageHeader mobile refinements

### 2026-08-03 — Full redesign pass (screenshot-driven)
- [x] **Design system** — scoped Button/Card/Badge styles (no thin black outlines in light mode)
- [x] **Dashboard** — denser enterprise layout; Refresh via HmsButton; motion stats/actions
- [x] **Patient Search** — HmsDataTable + badges; Open CTA; Register/Back owned by DS
- [x] **Patient Profile** — sticky hero (title case, badges); demographics/insurance grid; bill summary pills/rows; IPD rows; encounters panel with HmsButton actions; empty state

### 2026-08-03 — Polish pass on all built screens
- [x] **Choose Mode** — full redesign (Lucide icons, glass cards, motion, theme/sign-out)
- [x] **Header** — removed noisy filled glass buttons; ghost actions, mode/facility chips, session chip
- [x] **LicenseTitleLink** — matches header ghost style
- [x] **LicenseStatusBanner** — DS surfaces; original status/expiry/fallback logic kept
- [x] **Login** — public logo path fix (`/logos/...`)
- [x] **Dashboard** — keyboard-accessible actions, empty state, tabular nums
- [x] **Patient Registration** — section hints; GHIMS banner uses DS tone
- [x] **Patient Search** — monospace card numbers; quieter View CTA
- [x] **Patient Profile** — sticky hero retained; responsive top offset
- [x] **Notifications dialog** — cleaner card sizing
- [x] Removed obsolete MainLayout nav CSS (sidebar owns nav now)

### Earlier
- Design system, Login, Dashboard, sidebar, command palette (live patients), patient flow, HmsDataTable

### Next up
1. Remaining modules (Nursing, Reports, Staff, Settings, Theatre, Maternity)

---

## Build Verification

| Stage | Command | Result | Date |
|-------|---------|--------|------|
| Foundations | `npm run build` | ✅ Pass | 2026-08-03 |
| Sidebar + Patient flow | `npm run build` | ✅ Pass | 2026-08-03 |
| Polish pass (all built pages) | `npm run build` | ✅ Pass | 2026-08-03 |
| Full redesign (Dash/Search/Profile) | `npm run build` | ✅ Pass | 2026-08-03 |
| Zendenta polish pass | `npm run build` | ✅ Pass | 2026-08-03 |
| NHIS Claims primary boards | `npm run build` | ✅ Pass | 2026-08-03 |
| NHIS Claims full module | `npm run build` | ✅ Pass | 2026-08-03 |
| Inventory module | `npm run build` | ✅ Pass | 2026-08-03 |
| Companion module | `npm run build` | ✅ Pass | 2026-08-03 |

---

## Audit checklist (built screens)

| Screen | Sleek? | Notes |
|--------|--------|-------|
| Login | ✅ | Brand-forward, calm form |
| Choose Mode | ✅ | Was the biggest gap — redesigned |
| Header | ✅ | Quiet professional chrome |
| Sidebar | ✅ | Floating glass + groups |
| Command palette | ✅ | Modules + live patients |
| Dashboard | ✅ | Dense stats + action rows |
| Patient Registration | ✅ | Forms still Quasar; chrome matches DS |
| Patient Search | ✅ | Premium table + DS CTAs |
| Patient Profile | ✅ | Hero + demography + bills + IPD + encounter actions |
| License banner | ✅ | Soft status tones |

---

## Notes
- Prefer remapping `glass-*` so unmigrated pages stay coherent.
- Do not barrel-export `.vue` SFCs on Vite 2.9.
- Motion: `motion-v` only; respect reduced motion.
