# DOE Monolith API (FastAPI + GCP)

Este README te guía para correr **tu monolito** (`doe_monolith.py`) envuelto en una **API FastAPI** (`endpoint_app.py`) con **un solo parámetro de entrada (fila)**. Mantiene tu autenticación **mixta** (OAuth + Service Account) sin cambiar la lógica de autenticación del monolito.

> **Resumen:**
>
> * La API expone `POST /run` y llama **directamente** a `main(row_to_process)` dentro de tu monolito.
> * En local, **Drive** pedirá **OAuth** (abre navegador) y **Sheets** usa **Service Account** (gspread).
> * Para contenedor/Cloud Run, usa **Service Account** (OAuth no funciona sin navegador).

---

## 1) Estructura mínima del proyecto

```
.
├─ doe_monolith.py          # Tu script tal cual (solo se cambia la firma de main)
├─ endpoint_app.py          # Wrapper FastAPI: POST /run → main(row)
├─ requirements.txt         # Dependencias
├─ Dockerfile               # Imagen para despliegue
├─ service_account.json     # (rápido) credenciales SA para Sheets/Drive
└─ client_secret_*.json     # (local) credenciales OAuth para Drive
```

### Cambio mínimo en `doe_monolith.py`

```python
# antes
# def main():
#     row_to_process = 117

# después (único cambio)
def main(row_to_process: int = 117):
    ...

if __name__ == "__main__":
    import os
    row = int(os.getenv("ROW_TO_PROCESS", "117"))
    main(row)
```

> No se toca `authenticate_google_services()`.

---

## 2) Requisitos

* Python **3.11**
* Acceso a la Sheet y a la carpeta de Drive (comparte con la cuenta que autentiques)
* Archivos de credenciales en la raíz:

  * `service_account.json` (SA con permisos)
  * `client_secret_....json` (OAuth Installed App)

Instala dependencias:

```bash
pip install -r requirements.txt
```

---

## 3) Correr la API en local

Levanta FastAPI:

```bash
uvicorn endpoint_app:app --reload --port 8080
```

### Endpoint

* **Salud:** `GET /healthz`
* **Ejecutar:** `POST /run`
  **Body (JSON):**

  ```json
  { "row_to_process": 117 }
  ```

  **Headers opcionales:** `X-Run-Token: <tu-token>`

Ejemplo con `curl`:

```bash
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"row_to_process":117}'
```

> Si configuraste `RUN_TOKEN`, agrega: `-H "X-Run-Token: <tu-token>"`.

⚠️ En el primer uso, Google abrirá el navegador para **OAuth** (Drive). Acepta los **scopes**. Para **Sheets**, se usará el **Service Account**.

---

## 4) Ejecutar el monolito sin API (opcional)

```bash
# por variable de entorno
set ROW_TO_PROCESS=117    # Windows (CMD)
export ROW_TO_PROCESS=117 # bash/zsh
python doe_monolith.py
```

---

## 5) Apps Script (invocar la API)

```javascript
function runDoe() {
  const url = 'https://<tu-cloud-run-o-local>/run';
  const payload = { row_to_process: 117 };

  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    // headers: { 'X-Run-Token': 'tu-token-opcional' },
    muteHttpExceptions: true
  });

  Logger.log(res.getResponseCode());
  Logger.log(res.getContentText());
}
```

---

## 6) Docker (para pruebas rápidas)

> **Aviso:** OAuth (Installed App) no funciona sin navegador. Dentro del contenedor, usa **Service Account**.

Build & run:

```bash
docker build -t doe-monolith:local .
docker run --rm -p 8080:8080 \
  -e RUN_TOKEN=token-opcional \
  doe-monolith:local
```

> Para que el contenedor vea Drive/Sheets, **comparte** la carpeta/Sheet con el **correo del Service Account** usado por `service_account.json`.

---

## 7) Cloud Run (nota rápida)

* En Cloud Run **no** habrá navegador → **no** use OAuth (InstalledAppFlow).
* Migra `authenticate_google_services()` a **ADC/Service Account** o **impersonación de dominio** antes del deploy real.
* Env vars típicas: `RUN_TOKEN`, `GOOGLE_CLOUD_PROJECT`, `GDRIVE_IMPERSONATE_SUBJECT` (si aplicas impersonación).

Comandos de ejemplo (Artifact Registry):

```bash
gcloud config set project $PROJECT_ID

gcloud artifacts repositories create containers \
  --repository-format=docker --location=us-central1

gcloud builds submit \
  --tag us-central1-docker.pkg.dev/$PROJECT_ID/containers/doe-monolith:v1

gcloud run deploy doe-monolith \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/containers/doe-monolith:v1 \
  --region us-central1 --allow-unauthenticated \
  --cpu=2 --memory=2Gi --timeout=3600 \
  --set-env-vars RUN_TOKEN=pon-un-token,GOOGLE_CLOUD_PROJECT=$PROJECT_ID
  # --service-account SA_CON_PERMISOS@$PROJECT_ID.iam.gserviceaccount.com
  # --set-env-vars GDRIVE_IMPERSONATE_SUBJECT=usuario@tudominio.com
```

Permisos mínimos del SA (orientativos):

* Drive/Sheets según acceso: `roles/drive.file`, `roles/drive.reader`, `roles/drive.metadata.readonly`, `roles/iam.serviceAccountTokenCreator` (si impersonas), `roles/aiplatform.user`.
* Comparte la carpeta/Sheet con el SA o usa impersonación con delegación a nivel de dominio.

---

## 8) Solución de problemas (FAQ)

### 403 `insufficientPermissions` (Drive)

* **OAuth en local:** borra `token.pickle` para forzar el login con scopes completos.
* **Service Account:** comparte la carpeta de Drive y la Sheet con el **correo del SA** o usa **impersonación** (`GDRIVE_IMPERSONATE_SUBJECT`).
* Verifica que estás llamando **POST /run** (no `GET`) y **sin barra final** (`/run`, no `/run/`).

### Scopes ADC/OAuth

* Si usaste `gcloud auth application-default login` y sigues con 403, recuerda que el monolito usa **InstalledAppFlow** para Drive (no ADC) y **Service Account** para Sheets. Forzar nuevos scopes: borra `token.pickle`.

### Warning deprecación Vertex AI

* El warning de deprecación del SDK **no bloquea** la ejecución. Solo informativo.

---

## 9) Seguridad

* Usa `RUN_TOKEN` para proteger el endpoint básico.
* No publiques `service_account.json` ni `client_secret.json` en repos públicos.
* Considera rotar credenciales y limitar permisos al mínimo necesario.

---

## 10) Referencia rápida

### Request JSON mínimo

```json
{ "row_to_process": 117 }
```

### Health check

```bash
curl http://localhost:8080/healthz
```

### cURL POST

```bash
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"row_to_process":117}'
```

---

**Hecho para pruebas rápidas en local manteniendo OAuth + SA sin tocar tu autenticación actual.**
