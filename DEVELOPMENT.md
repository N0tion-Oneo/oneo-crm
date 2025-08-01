# Oneo CRM Development Guide

## Quick Start Scripts

We've created convenient startup scripts to make development easier:

### 🚀 Full Development Environment
```bash
./start-dev.sh
```
Starts both backend and frontend simultaneously. This is the easiest way to get everything running.

### 🔧 Backend Only
```bash
./start-backend.sh
```
Starts only the Django backend server on port 8000.

### 🌐 Frontend Only
```bash
./start-frontend.sh
```
Starts only the Next.js frontend server on port 3000.

## Available Endpoints

Once started, you can access:

- **🔧 Backend API Documentation**: http://localhost:8000/api/v1/docs/
- **🔗 GraphQL Playground**: http://localhost:8000/graphql/
- **🌐 Frontend Application**: http://localhost:3000
- **🏢 Demo Tenant**: http://demo.localhost:3000
- **🧪 Test Tenant**: http://testorg.localhost:3000

## Prerequisites

The startup scripts will check for and start required services:

- **PostgreSQL 14+** (installed via Homebrew)
- **Redis** (installed via Homebrew)
- **Python 3.9+** with virtual environment
- **Node.js 18+** with npm

## Default Login Credentials

- **Email**: admin@demo.com
- **Password**: admin123

## Project Structure

```
Oneo CRM/
├── backend/          # Django backend
├── frontend/         # Next.js frontend
├── start-backend.sh  # Backend startup script
├── start-frontend.sh # Frontend startup script
├── start-dev.sh      # Full development environment
└── DEVELOPMENT.md    # This file
```

## Troubleshooting

### Port Already in Use
The scripts automatically kill existing processes on ports 3000 and 8000.

### Services Not Running
The backend script will attempt to start PostgreSQL and Redis automatically.

### CORS Issues
The backend is configured to allow requests from `*.localhost:3000` domains.

### Database Issues
Run migrations manually if needed:
```bash
cd backend
source venv/bin/activate
python manage.py migrate_schemas
```

## Stopping Everything

Press `Ctrl+C` in the terminal where you started the scripts. The cleanup function will stop all related processes.