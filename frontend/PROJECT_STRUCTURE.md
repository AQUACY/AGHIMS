# Project Structure

## Frontend Application Structure

```
frontend/
├── src/
│   ├── pages/                    # Page components
│   │   ├── Login.vue            # Login page
│   │   ├── Dashboard.vue        # Dashboard with statistics
│   │   ├── PatientRegistration.vue  # Patient registration form
│   │   ├── Vitals.vue           # Vitals recording page
│   │   ├── Consultation.vue     # Consultation workflow
│   │   ├── Billing.vue          # Billing and price list management
│   │   ├── Pharmacy.vue         # Pharmacy service page
│   │   ├── Lab.vue              # Lab service page
│   │   ├── Scan.vue             # Scan/imaging service page
│   │   └── Claims.vue           # Claims management
│   │
│   ├── layouts/
│   │   └── MainLayout.vue        # Main layout with navigation drawer
│   │
│   ├── stores/                   # Pinia stores (state management)
│   │   ├── auth.js              # Authentication store
│   │   ├── patients.js          # Patient management store
│   │   ├── encounters.js        # Encounter management store
│   │   ├── dashboard.js         # Dashboard statistics store
│   │   ├── billing.js           # Billing store
│   │   └── claims.js            # Claims store
│   │
│   ├── services/
│   │   └── api.js               # Axios API service layer
│   │
│   ├── router/
│   │   └── index.js             # Vue Router with route guards
│   │
│   ├── boot/
│   │   └── axios.js             # Axios boot file
│   │
│   ├── App.vue                  # Root component
│   └── main.js                  # Application entry point
│
├── index.html                    # HTML template
├── package.json                  # Dependencies and scripts
├── quasar.config.js             # Quasar framework configuration
├── .postcssrc.js                # PostCSS configuration
├── README.md                     # Project documentation
├── SETUP.md                      # Setup instructions
└── .gitignore                   # Git ignore file
```

## Key Features

### Authentication
- JWT token-based authentication
- Automatic token refresh and logout on 401 errors
- Role-based access control

### State Management (Pinia Stores)
- **auth**: User authentication and authorization
- **patients**: Patient CRUD operations
- **encounters**: Encounter management and data loading
- **dashboard**: Dashboard statistics
- **billing**: Price list and billing operations
- **claims**: Claims generation and export

### Pages Overview

1. **Login**: Simple login form with username/password
2. **Dashboard**: 
   - Statistics cards (today's patients, pending encounters, unpaid bills)
   - Quick action buttons

3. **Patient Registration**:
   - Search existing patients by card number
   - Register new patients
   - Automatic encounter creation

4. **Vitals**:
   - Load encounter by ID
   - Record/update vitals (BP, temperature, pulse, weight, height)
   - Save as draft

5. **Consultation**:
   - Display patient info and vitals
   - Add diagnoses (provisional/final, chief complaint)
   - Add prescriptions
   - Add investigations (lab, scan, xray)
   - Finalize consultation with confirmation

6. **Billing**:
   - Upload price list files (Excel)
   - Search price items
   - Create bills with auto-pricing based on insurance status
   - Add miscellaneous items
   - Issue receipts

7. **Pharmacy/Lab/Scan**:
   - View pending service requests
   - Confirm investigations
   - Mark services as billed

8. **Claims**:
   - Export claims by date range
   - Generate claims from finalized encounters
   - Finalize/reopen claims
   - Export XML files

## API Integration

All API calls are centralized in `src/services/api.js`:
- Automatic JWT token injection
- Error handling and auto-logout on 401
- FormData support for file uploads and OAuth2 login

## Routing & Navigation

- Protected routes with authentication guards
- Role-based route access
- Navigation drawer with role-based menu items
- Automatic redirect to login for unauthenticated users

## UI Components

Using Quasar Framework components:
- q-card, q-table, q-form, q-input, q-btn
- q-dialog for modals
- q-badge for status indicators
- q-select for dropdowns
- Toast notifications (Notify plugin)
- Loading indicators

## Responsive Design

- Mobile-first approach
- Responsive grid system
- Tablet-optimized layout for hospital tablets
- Clean, professional UI with blue/white/gray color scheme

