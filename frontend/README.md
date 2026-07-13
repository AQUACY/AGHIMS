# Hospital Management System - Frontend

Vue.js/Quasar frontend application for the OPD Hospital Management System.

## Features

- **Authentication**: JWT-based login system
- **Dashboard**: Quick overview of key metrics
- **Patient Registration**: Register new and returning patients with automatic encounter creation
- **Vitals**: Record and manage patient vital signs
- **Consultation**: Comprehensive consultation workflow with diagnoses, prescriptions, and investigations
- **Billing**: Price list management, bill creation, and receipt issuance
- **Service Pages**: Pharmacy, Lab, and Scan service confirmation
- **Claims Management**: Generate, finalize, and export NHIS claims as XML

## Prerequisites

- Node.js >= 18.0.0
- npm >= 8.0.0

## Installation

1. Install dependencies:
```bash
npm install
```

## Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:9000`

## Build for Production

Build the application for production:
```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
frontend/
├── src/
│   ├── pages/          # Page components
│   ├── layouts/        # Layout components
│   ├── stores/         # Pinia stores for state management
│   ├── services/       # API service layer
│   ├── router/         # Vue Router configuration
│   └── main.js         # Application entry point
├── package.json
├── quasar.config.js   # Quasar configuration
└── README.md
```

## Configuration

### API Base URL

Update the API base URL in `quasar.config.js`:

```javascript
env: {
  API_BASE_URL: ctx.dev
    ? 'http://localhost:8000/api'
    : 'http://your-production-api-url/api'
}
```

## Features by Role

### Records Staff
- Patient Registration
- Create Encounters

### Nurses
- Record Vitals

### Doctors
- Consultation
- Add Diagnoses, Prescriptions, Investigations
- Finalize Consultations

### Billing Staff
- Upload Price Lists
- Create Bills
- Issue Receipts

### Pharmacy/Lab/Scan Staff
- Confirm Service Requests
- Mark Services as Billed

### Claims Staff
- Generate Claims
- Finalize Claims
- Export XML Files

## Notes

- All API calls are authenticated using JWT tokens
- The application automatically redirects to login on authentication errors
- Role-based access control is implemented at the route level
- Toast notifications provide user feedback for all actions

