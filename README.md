# CxSAST Branched Projects Tree Manager

A web application for managing CxSAST projects with a tree view and safe bulk deletion.

## Quick Start (Development)

```bash
cd backend
pip install -r requirements.txt
# Copy backend/.env.example to backend/.env and edit with your CxSAST credentials
python app.py
# Open http://localhost:5000
```

## Production Deployment (no Python required for end user)

### 1. Build the .exe

On a dev machine with Python:
```cmd
cd backend
pip install -r requirements.txt
pip install pyinstaller waitress
build.bat
```

This produces `dist\CxSAST-TreeManager\CxSAST-TreeManager.exe`.

### 2. Deploy to customer

Copy the entire `dist\CxSAST-TreeManager\` folder to the customer's server.

### 3. Configure (via environment variables)

```cmd
set CXSAST_BASE_URL=https://cxserver.customer.local
set CXSAST_USERNAME=admin
set CXSAST_PASSWORD=their-password
set CXSAST_VERIFY=False
set APP_API_KEY=choose-a-secret-key    # optional but recommended
set APP_PORT=5000                       # optional, default 5000
set APP_HOST=0.0.0.0                    # optional, default 0.0.0.0
```

### 4. Run

```cmd
CxSAST-TreeManager.exe
# Open http://localhost:5000
```

### 5. (Optional) Windows Service

To run as a Windows service that auto-starts:
```powershell
nssm install CxSAST-TreeManager "C:\path\to\CxSAST-TreeManager.exe"
nssm start CxSAST-TreeManager
```

### 6. (Optional) IIS Reverse Proxy

If IIS is already running CxSAST on port 443, proxy this app through IIS:
- Install URL Rewrite + ARR modules
- Add reverse proxy rule: `/tree-manager/*` → `http://localhost:5000/*`
- Access at `https://cxserver.customer.local/tree-manager/`

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CXSAST_BASE_URL` | Yes | `https://desktop-rmvpboc` | CxSAST server URL |
| `CXSAST_USERNAME` | Yes | — | CxSAST username |
| `CXSAST_PASSWORD` | Yes | — | CxSAST password |
| `CXSAST_VERIFY` | No | `True` | `False` for self-signed certs, or path to CA cert |
| `CXSAST_SCOPE` | No | `sast_rest_api` | OAuth scope |
| `APP_API_KEY` | No | — | If set, API requests must include `X-API-Key` header |
| `APP_PORT` | No | `5000` | HTTP port |
| `APP_HOST` | No | `0.0.0.0` | Bind address |

## Features

- Tree view of all CxSAST projects with parent-child branch relationships
- Cascade selection: checking a parent automatically selects all descendants
- Safe deletion: only leaf projects (no children) can be deleted
- Bulk delete with confirmation dialog
- Filter by name, show branched projects only
- Single-click expand/collapse all
