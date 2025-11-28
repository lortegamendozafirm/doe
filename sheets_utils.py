# sheets_utils.py
from typing import Tuple, List, Dict, Any
import gspread
from gspread.utils import rowcol_to_a1

from config import SERVICE_ACCOUNT_FILE  # o pon aquí el path directo al JSON


def get_row_data(sheet_url: str, sheet_name: str, row_number: int) -> Tuple[str, str]:
    """
    Obtiene de la fila:
      - nombre del cliente (columna B)
      - URL de la carpeta del cliente (columna D)
    """
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.worksheet(sheet_name)
        row_data = worksheet.row_values(row_number)

        if len(row_data) < 4:
            raise ValueError(
                f"La fila {row_number} no tiene suficientes columnas. "
                "Se esperaban al menos 4."
            )

        client_name = row_data[1]  # Columna B (índice 1)
        client_folder_url = row_data[3]  # Columna D (índice 3)

        if not client_name or not client_folder_url:
            raise ValueError(
                f"Datos incompletos en la fila {row_number}. "
                "Falta Nombre (Col B) o URL (Col D)."
            )

        print(f"✅ Datos de la fila {row_number} obtenidos para el cliente: {client_name}")
        return client_name, client_folder_url

    except Exception as e:
        print(
            f"❌ Error al acceder a Google Sheets o procesar la fila "
            f"{row_number}: {e}"
        )
        return None, None


def update_progress_in_sheet(
    worksheet: gspread.Worksheet,
    row_number: int,
    progress_value: float,
    status_text: str | None = None,
) -> None:
    """
    Actualiza la celda de progreso (Columna F, índice 6) con:
      - status_text (si se pasa), por ejemplo 'ERROR: ...'
      - o bien un valor numérico (0–1) que Google Sheets puede formatear como %
    """
    progress_col = 6  # Columna F (1-based)

    try:
        if status_text:
            worksheet.update_cell(row_number, progress_col, status_text)
            print(f"   📊 Estado actualizado a: {status_text} en la Fila {row_number}")
        else:
            worksheet.update_cell(row_number, progress_col, progress_value)
            print(
                f"   📊 Progreso actualizado a: {progress_value * 100:.0f}% "
                f"en la Fila {row_number}"
            )

    except Exception as e:
        # No queremos que un fallo en el progreso detenga todo el script
        print(f"   ⚠️ Advertencia: No se pudo actualizar el progreso en la hoja: {e}")


def write_links_to_sheet(
    gc: gspread.Client,
    sheet_url: str,
    sheet_name: str,
    row_number: int,
    uploaded_files_info: List[Dict[str, Any]],
) -> None:
    """
    Escribe los enlaces de los archivos generados de nuevo en la hoja de Google.

    Los enlaces empiezan en la columna 7 (G) y se van recorriendo hacia la derecha.
    """
    print(
        f"\n📝 Escribiendo enlaces de vuelta a la Fila {row_number} "
        f"de la hoja '{sheet_name}'..."
    )

    try:
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.worksheet(sheet_name)

        link_col_start = 7  # Columna G

        if not uploaded_files_info:
            print("   ⚠️ No hay información de archivos subidos para escribir.")
            return

        for i, file_info in enumerate(uploaded_files_info):
            link = file_info.get("link")
            col_to_write = link_col_start + i

            if link:
                cell_name = rowcol_to_a1(row_number, col_to_write)
                print(
                    f"   ... Escribiendo enlace en celda {cell_name} "
                    f"(Fila {row_number}, Col {col_to_write})..."
                )
                worksheet.update_cell(row_number, col_to_write, link)
            else:
                print(
                    f"   ⚠️ No se encontró enlace (link) para el archivo "
                    f"{file_info.get('name')}."
                )

        print("✅ Enlaces escritos exitosamente en la hoja.")

    except Exception as e:
        print(f"   ❌ Error al escribir enlaces en Google Sheets: {e}")
