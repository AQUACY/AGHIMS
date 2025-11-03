# Setup Instructions

## Quick Start

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure API URL**
   - Edit `quasar.config.js` and update the `API_BASE_URL` in the `env` section to match your backend URL
   - Default is `http://localhost:8000/api`

3. **Start Development Server**
   ```bash
   npm run dev
   ```

4. **Access the Application**
   - Open your browser and navigate to `http://localhost:9000`
   - Login with your credentials

## Building for Production

```bash
npm run build
```

The production-ready files will be in the `dist/spa` directory.

## Development Workflow

1. Start the backend API server first (on port 8000)
2. Start the frontend dev server (on port 9000)
3. The frontend will proxy API requests to the backend

## Key Features

- **Role-Based Access**: Different pages are accessible based on user roles
- **JWT Authentication**: Secure token-based authentication
- **Responsive Design**: Works on tablets and desktops
- **Real-time Feedback**: Toast notifications for all actions
- **State Management**: Centralized state using Pinia

## Troubleshooting

### CORS Errors
If you encounter CORS errors, ensure your backend has CORS middleware configured correctly.

### Authentication Issues
- Check that the backend is running
- Verify the API_BASE_URL in quasar.config.js
- Clear localStorage and try logging in again

### Build Errors
- Ensure Node.js version is >= 18.0.0
- Delete `node_modules` and `.quasar` folders, then run `npm install` again

