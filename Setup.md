# Setup Instructions

## 1. Clone the repository

```powershell
git clone https://github.com/codewithsach/cloudvault-web.git
cd cloudvault-web
```

## 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 4. Run the application

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## 5. Default admin login

```text
username: admin
password: admin123
```

## Optional environment variables

```powershell
$env:SECRET_KEY="replace-with-a-long-random-secret"
$env:FLASK_DEBUG="1"
```

`FLASK_DEBUG=1` enables debug mode. Leave it unset for normal local runs.
