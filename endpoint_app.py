# endpoint_app.py
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

# Importa tu monolito tal cual
import doe_monolith as m

app = FastAPI(title="DOE Monolith API (thin wrapper)", version="1.0")

# Seguridad simple opcional por header
RUN_TOKEN = os.getenv("RUN_TOKEN", "")

class RunRequest(BaseModel):
    row_to_process: int

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/run")
def run(req: RunRequest, x_run_token: Optional[str] = Header(default=None)):
    # token opcional (si no seteas RUN_TOKEN, no se valida nada)
    if RUN_TOKEN and (x_run_token or "") != RUN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid X-Run-Token")

    try:
        # Llama DIRECTO a tu main(row)
        m.main(req.row_to_process)
        return {"status": "ok", "row_processed": req.row_to_process}
    except Exception as e:
        # Si tu main imprime y maneja, igual capturamos cualquier excepción burda
        raise HTTPException(status_code=500, detail=str(e))
