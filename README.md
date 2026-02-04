# Project Aegis — Audit Report MVP

Generate a simple two-page PDF audit snapshot with radar charts for Operations, Users, and Devices. Client-specific data is loaded from a JSON file and outputs are written to a client-scoped folder that is ignored by git.

## Features
- PDF report with header/footer and Executive Summary via ReportLab
- Three radar charts (Operations / Users / Devices) via Matplotlib
- Client data loaded from JSON: name, assessment scores, findings
- Client-scoped outputs under `output/<client-slug>/` (ignored by git)
- Safe defaults when no client JSON is present

## Prerequisites
- Python 3.10+ (tested with Python 3.12)
- Linux/macOS recommended (Windows works with minor path adjustments)

## Setup
From the project root:

```bash
# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Provide Client Data
Copy the sample, then edit values:

```bash
cp data/client_data.sample.json data/client_data.json
```

Expected structure:

```json
{
  "client_name": "Client Name",
  "assessment": {
    "Operations": {
      "Backups & Recovery": 2,
      "Patch Management": 3,
      "Monitoring & Alerting": 2,
      "Change Management": 1,
      "Documentation": 3,
      "Vendor Management": 2
    },
    "Users": {
      "MFA Adoption": 3,
      "Access Reviews": 1,
      "Security Training": 2,
      "Password Hygiene": 3,
      "On/Offboarding": 2,
      "Privileged Access": 1
    },
    "Devices": {
      "Endpoint Protection": 3,
      "Disk Encryption": 2,
      "OS Compliance": 2,
      "MDM / Policy": 1,
      "Asset Inventory": 2,
      "Local Admin Control": 1
    }
  },
  "findings": [
    ["High Risk", "Description..."],
    ["Quick Win", "Description..."]
  ]
}
```

Notes:
- `client_name` is slugified to form the output folder name (lowercase, spaces/punctuation → `-`).
- Client data file `data/client_data.json` is ignored by git.

## Run
From the project root (with venv active):

```bash
python generate_report.py
```

Outputs will be written to:

```
output/<client-slug>/audit-report-mvp.pdf
output/<client-slug>/radar_operations.png
output/<client-slug>/radar_users.png
output/<client-slug>/radar_devices.png
```

Example for the sample client:

```
output/client-name-sample/
```

## VS Code
- Select the interpreter: Command Palette → "Python: Select Interpreter" → choose `.venv`.
- Workspace setting is pre-configured in `.vscode/settings.json` to use the venv.

## Git Hygiene
- The following paths are ignored via `.gitignore`:
  - `data/client_data.json` and any `data/*.secret.json`
  - `output/` (all generated reports and charts)
  - `.venv/` (local virtual environment)

If `.venv` or outputs were previously tracked, untrack them:

```bash
git rm -r --cached .venv output data/client_data.json
git add .gitignore
git commit -m "Ignore venv, outputs, and client data"
```

## Pinning Dependencies (optional)
After confirming it runs:

```bash
pip freeze > requirements.txt
```

## Files
- Main script: [generate_report.py](generate_report.py)
- Dependencies: [requirements.txt](requirements.txt)
- Client data sample: [data/client_data.sample.json](data/client_data.sample.json)
- Git ignore rules: [.gitignore](.gitignore)
- License: [LICENSE](LICENSE)
