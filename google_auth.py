# google_auth.py
import os
import gspread
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from config import SCOPES_DRIVE, SERVICE_ACCOUNT_FILE, CLIENT_SECRET_FILE

TOKEN_DRIVE_FILE = "token_drive.json"


def get_sheets_client() -> gspread.Client:
    """Devuelve el cliente de Google Sheets (cuenta de servicio)."""
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        print("✅ Autenticación con Google Sheets exitosa.")
        return gc
    except FileNotFoundError as e:
        print(f"❌ Error: Archivo de cuenta de servicio no encontrado: {e}")
        raise
    except Exception as e:
        print(f"❌ Error durante la autenticación de Google Sheets: {e}")
        raise


def get_drive_client():
    """Devuelve el cliente de Google Drive usando token cacheado."""
    creds = None

    if os.path.exists(TOKEN_DRIVE_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_DRIVE_FILE, SCOPES_DRIVE)
        print("   ... Token de Drive encontrado localmente.")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("   ... Token de Drive expirado, refrescando automáticamente...")
            creds.refresh(Request())
        else:
            print("   ... No se encontró token de Drive válido. Iniciando flujo de autenticación.")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES_DRIVE
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_DRIVE_FILE, "w") as token_file:
            token_file.write(creds.to_json())
            print(f"   ... Token de Drive guardado en '{TOKEN_DRIVE_FILE}'.")

    drive_service = build("drive", "v3", credentials=creds)
    print("✅ Autenticación con Google Drive exitosa.")
    return drive_service


def authenticate_google_services():
    """Wrapper para obtener ambos clientes a la vez (compatibilidad con tu main)."""
    gc = get_sheets_client()
    drive_service = get_drive_client()
    return gc, drive_service
