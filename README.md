# CxSAST Branched Projects Tree Manager

A web tool for managing CxSAST projects — view branched projects as a tree, select with cascade, and safely bulk-delete (only leaf nodes are deleted, so your tree structure is never broken).

- [For End Users (Deployment)](#deployment)
- [For Developers](#development)

---

## Deployment

The application is distributed as a single `.exe` file. No Python or other dependencies are required on the target server.

### Step 1: Download

Download the latest `CxSAST-TreeManager.exe` from the [Releases page](https://github.com/cx-happy-yang/cxsast-branched-projects-tree/releases).

### Step 2: Place on Server

Copy `CxSAST-TreeManager.exe` to the server where CxSAST is installed (or any Windows machine that can reach the CxSAST server over the network). For example:

```
C:\Tools\CxSAST-TreeManager\CxSAST-TreeManager.exe
```

### Step 3: Configure

Set the following **system environment variables** (System Properties → Advanced → Environment Variables → System variables):

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `CXSAST_BASE_URL` | Yes | `https://cxserver.company.local` | Your CxSAST server URL |
| `CXSAST_USERNAME` | Yes | `Admin` | CxSAST username with manage-project permissions |
| `CXSAST_PASSWORD` | Yes | `••••` | CxSAST password |
| `CXSAST_VERIFY` | No | `False` | Set to `False` if using self-signed certificate; or path to a CA cert file |
| `APP_API_KEY` | Recommended | `my-secret-key-123` | Protects the API; set this and share with users |
| `APP_PORT` | No | `5000` | HTTP port (default: 5000) |
| `APP_HOST` | No | `127.0.0.1` | Bind address (default: `0.0.0.0`; use `127.0.0.1` for IIS proxy) |

> **Note:** After setting environment variables, you may need to restart the Command Prompt or the machine for them to take effect.

### Step 4: Run

Open a **Command Prompt (as Administrator)** and run:

```cmd
C:\Tools\CxSAST-TreeManager\CxSAST-TreeManager.exe
```

You should see:
```
Starting production server on 0.0.0.0:5000
```

Open a browser and go to `http://localhost:5000`. You should see the project tree.

### Step 5: Access the UI

If you set `APP_API_KEY`, users must include it in the URL:

```
http://<server>:5000/?api_key=my-secret-key-123
```

Or bookmark it with the key included.

---

## Run as a Windows Service

To make the application start automatically with the server and survive reboots:

### Install NSSM

Download [NSSM](https://nssm.cc/download) (Non-Sucking Service Manager) and extract `nssm.exe` to a known location, e.g., `C:\Tools\`.

### Create the Service

Open **Command Prompt as Administrator** and run:

```cmd
C:\Tools\nssm.exe install CxSAST-TreeManager "C:\Tools\CxSAST-TreeManager\CxSAST-TreeManager.exe"
```

A configuration window appears. Configure these tabs:

| Tab | Setting |
|-----|---------|
| **Application** | Path: `C:\Tools\CxSAST-TreeManager\CxSAST-TreeManager.exe` |
| **Application** | Startup directory: `C:\Tools\CxSAST-TreeManager` |
| **Details** | Display name: `CxSAST Tree Manager` |
| **Details** | Startup type: `Automatic` |

Click **Install service**.

### Start the Service

```cmd
C:\Tools\nssm.exe start CxSAST-TreeManager
```

Or start it from `services.msc` → find "CxSAST Tree Manager" → right-click → Start.

### Verify

Open `http://localhost:5000` in a browser. The service will now auto-start on every reboot.

### Other NSSM Commands

```cmd
C:\Tools\nssm.exe stop CxSAST-TreeManager     # stop the service
C:\Tools\nssm.exe restart CxSAST-TreeManager  # restart the service
C:\Tools\nssm.exe remove CxSAST-TreeManager   # uninstall the service (stop first)
```

---

## (Optional) Proxy Behind IIS

If your CxSAST is already running on IIS (port 443), you can proxy the tree manager through IIS so users access it at `https://cxserver.company.local/tree-manager/` without needing to open an additional port.

### Prerequisites

Install these IIS modules on the CxSAST server:
- [URL Rewrite](https://www.iis.net/downloads/microsoft/url-rewrite)
- [Application Request Routing (ARR)](https://www.iis.net/downloads/microsoft/application-request-routing)

### Configure

1. In IIS Manager, select the **CxSAST site** (or Default Web Site)
2. Open **URL Rewrite** → **Add Rule(s)...** → **Reverse Proxy**
3. Enter: `localhost:5000` (or the port you configured)
4. Check **Enable SSL Offloading**
5. Set the inbound rule pattern to: `^tree-manager/(.*)`
6. Apply

### Update Config

Set the environment variable so the app only listens locally:

```
APP_HOST=127.0.0.1
```

### Access

```
https://cxserver.company.local/tree-manager/?api_key=my-secret-key-123
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to CxSAST" | Check `CXSAST_BASE_URL`, `CXSAST_USERNAME`, `CXSAST_PASSWORD` are correct. Try the URL in a browser first. |
| SSL certificate error | Set `CXSAST_VERIFY=False` if using a self-signed certificate. |
| Port already in use | Change `APP_PORT` to a different port (e.g., `5001`). |
| Service won't start | Check Windows Event Viewer → Windows Logs → Application for error messages. |
| Tree shows "No projects" | Verify the CxSAST user has `sast_rest_api` permissions and can view projects. |

---

## Development

### Setup

```bash
git clone git@github.com:cx-happy-yang/cxsast-branched-projects-tree.git
cd cxsast-branched-projects-tree/backend
pip install -r requirements.txt
cp .env.example .env          # edit .env with your dev CxSAST credentials
python app.py                 # starts on http://localhost:5000
```

### Build a Release

```bash
cd backend
pip install pyinstaller
python -m PyInstaller --clean --noconfirm cxsast-tree-manager.spec
# output: dist/CxSAST-TreeManager.exe
```

### Create a Versioned Release

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will build the `.exe`, create a release, and attach the binary automatically.
