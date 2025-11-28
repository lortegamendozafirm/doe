import os
import shutil
import time

from vertexai.preview.generative_models import GenerativeModel

from prompt import (
    PROMPT_PASO_3_ABUSE_IMG,
    PROMPT_PASO_4_GMC_IMG,
    PROMPT_WS_RL_TEMPLATE,
    PROMPT_PB_TEMPLATE,
    PROMPT_PASO_5_FINAL_DELIVERABLE,
    PROMPT_INSTRUCCIONES_SISTEMA,
)
from utils import get_folder_id_from_url

from config import SHEET_URL, SHEET_NAME
from google_auth import authenticate_google_services
from sheets_utils import (
    get_row_data,
    update_progress_in_sheet,
    write_links_to_sheet,
)
from drive_utils import (
    find_item_in_drive,
    list_and_download_images,
    find_multiple_files_with_keywords,
)
from ai_client import model_pro, send_message_to_chat, process_file_with_prompt
from docx_builder import save_final_deliverable


def main(row_to_process: int = 117) -> None:
    """
    Orquesta el flujo completo de generación del DOE:
      - Lee datos de la fila en Google Sheets
      - Localiza y descarga PDFs/imagenes en Drive
      - Procesa con Gemini (Vertex AI)
      - Construye .txt y .docx
      - Sube a Drive y escribe links en la hoja
    """
    temp_dir = "temp_processing_doe"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    print(
        "🚀 Iniciando el proceso de generación de documentos para "
        "DOE RAR/GMC (v2.2 - Tabla corregida)..."
    )

    worksheet = None
    gc = None

    try:
        # 1. AUTENTICACIÓN Y DATOS BASE
        gc, drive_service = authenticate_google_services()
        client_name, client_folder_url = get_row_data(
            SHEET_URL, SHEET_NAME, row_to_process
        )

        if not all([client_name, client_folder_url]):
            print("❌ No se pudieron obtener todos los datos necesarios.")
            return

        # Obtener worksheet para ir marcando progreso
        try:
            sh = gc.open_by_url(SHEET_URL)
            worksheet = sh.worksheet(SHEET_NAME)
            update_progress_in_sheet(worksheet, row_to_process, 0.05)
        except Exception as e:
            print(
                f"⚠️ Advertencia: No se pudo abrir la hoja '{SHEET_NAME}' "
                f"para actualizar el progreso: {e}"
            )

        client_folder_id = get_folder_id_from_url(client_folder_url)
        if not client_folder_id:
            print("❌ URL de carpeta no válida. Proceso detenido.")
            if worksheet:
                update_progress_in_sheet(
                    worksheet,
                    row_to_process,
                    0,
                    status_text="ERROR: URL Carpeta",
                )
            return

        print(
            f"✅ Usando ID de carpeta: {client_folder_id} "
            f"para el cliente '{client_name}'."
        )

        # 2. LOCALIZAR CARPETAS BASE
        print("\nBuscando carpetas 'AUDIO' y 'EVIDENCIA'...")
        audio_folder_id = find_item_in_drive(
            drive_service,
            client_folder_id,
            "audio",
            "application/vnd.google-apps.folder",
        )
        evidence_folder_id = find_item_in_drive(
            drive_service,
            client_folder_id,
            "evidencia",
            "application/vnd.google-apps.folder",
        )
        if not all([audio_folder_id, evidence_folder_id]):
            if worksheet:
                update_progress_in_sheet(
                    worksheet,
                    row_to_process,
                    0,
                    status_text="ERROR: Falta AUDIO o EVIDENCIA",
                )
            return

        evidence_abuse_folder_id = find_item_in_drive(
            drive_service,
            evidence_folder_id,
            "abuse",
            "application/vnd.google-apps.folder",
        )
        evidence_gmc_folder_id = find_item_in_drive(
            drive_service,
            evidence_folder_id,
            "gmc",
            "application/vnd.google-apps.folder",
        )
        if not all([evidence_abuse_folder_id, evidence_gmc_folder_id]):
            if worksheet:
                update_progress_in_sheet(
                    worksheet,
                    row_to_process,
                    0,
                    status_text="ERROR: Falta EVIDENCIA/ABUSE o GMC",
                )
            return

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.10)

        # 3. OBTENER TRANSCRIPCIONES BASE (ABUSE y GMC)
        print("\n📄 Buscando transcripciones PDF base en 'AUDIO'...")
        abuse_pdf_files = find_multiple_files_with_keywords(
            drive_service,
            audio_folder_id,
            ["abuse"],
            ["application/pdf"],
            temp_dir,
        )
        gmc_pdf_files = find_multiple_files_with_keywords(
            drive_service,
            audio_folder_id,
            ["gmc"],
            ["application/pdf"],
            temp_dir,
        )

        if not abuse_pdf_files or not gmc_pdf_files:
            print(
                "❌ No se encontró el PDF base 'ABUSE' o 'GMC'. Proceso detenido."
            )
            if worksheet:
                update_progress_in_sheet(
                    worksheet,
                    row_to_process,
                    0,
                    status_text="ERROR: Falta PDF ABUSE o GMC",
                )
            return

        abuse_pdf_info = abuse_pdf_files[0]
        gmc_pdf_info = gmc_pdf_files[0]

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.20)

        # 4. OBTENER TRANSCRIPCIONES WS/WSS (TESTIMONIOS)
        print("\n🎧 Buscando transcripciones 'WS' o 'WSS' en 'AUDIO'...")
        ws_files_list = find_multiple_files_with_keywords(
            drive_service,
            audio_folder_id,
            ["ws", "wss"],
            ["application/pdf"],
            os.path.join(temp_dir, "ws_rl_pdfs"),
        )

        # 5. OBTENER ARCHIVOS RL (REFERENCE LETTERS)
        print("\n🗂️ Buscando archivos 'RL' (Reference Letters) en 'EVIDENCIA/GMC'...")
        rl_files_list = find_multiple_files_with_keywords(
            drive_service,
            evidence_gmc_folder_id,
            ["rl"],
            [
                "application/pdf",
                "image/jpeg",
                "image/png",
                "image/tiff",
            ],
            os.path.join(temp_dir, "rl_files"),
        )
        rl_file_names = "\n".join([f"- {file['name']}" for file in rl_files_list])

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.30)

        # 6. OBTENER IMÁGENES DE EVIDENCIA (ABUSE y GMC)
        print(
            "\n🖼️ Descargando imágenes de 'EVIDENCIA/ABUSE' y 'EVIDENCIA/GMC'..."
        )
        abuse_images_list = list_and_download_images(
            drive_service,
            evidence_abuse_folder_id,
            os.path.join(temp_dir, "abuse_images"),
        )
        gmc_all_images_list = list_and_download_images(
            drive_service,
            evidence_gmc_folder_id,
            os.path.join(temp_dir, "gmc_images"),
        )

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.40)

        # ------------------------------------------------------------------
        # PROCESAMIENTO INTERMEDIO DE IA
        # ------------------------------------------------------------------

        # 7. PROCESAR WS/WSS (TESTIMONIOS)
        witness_texts = [
            process_file_with_prompt(
                file, PROMPT_WS_RL_TEMPLATE, model_pro, client_name
            )
            for file in ws_files_list
        ]
        witness_final_content = "\n\n---\n\n".join(witness_texts)

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.60)
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15)

        # 8. PROCESAR GMC (PERMANENT BAR)
        pb_content = process_file_with_prompt(
            gmc_pdf_info,
            PROMPT_PB_TEMPLATE,
            model_pro,
            client_name,
        )

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.75)
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15)

        # 9. GENERAR ENTREGABLE FINAL (PASO 5)
        print("\n--- PASO FINAL: Ensamblando el Entregable ---")

        final_prompt_text = (
            PROMPT_PASO_5_FINAL_DELIVERABLE.replace(
                "{witness_content}", witness_final_content
            )
            .replace("{pb_content}", str(pb_content))
            .replace("{rl_file_names}", rl_file_names)
        )

        # Modelo de chat final con system_instruction
        try:
            chat_model_final = GenerativeModel(
                model_pro._model_name,
                generation_config=model_pro._generation_config,
                system_instruction=PROMPT_INSTRUCCIONES_SISTEMA,
            )
        except Exception as e:
            chat_model_final = model_pro
            print(
                "⚠️ Se usó el modelo base para el ensamblaje final "
                f"por excepción al crear GenerativeModel: {e}"
            )

        chat = chat_model_final.start_chat()

        # 9.1. Cargar contexto de ABUSO + imágenes
        abuse_names_list = "\n".join(
            [f"- {img['name']}" for img in abuse_images_list]
        )
        prompt_step_3_with_names = PROMPT_PASO_3_ABUSE_IMG.replace(
            "[LISTA_DE_NOMBRES_DE_ARCHIVO_ADJUNTOS]", abuse_names_list
        )
        send_message_to_chat(
            chat,
            prompt_step_3_with_names,
            files_to_upload=[abuse_pdf_info] + abuse_images_list,
            expect_response=False,
        )

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.80)
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15)

        # 9.2. Cargar contexto de GMC + imágenes
        gmc_names_list = "\n".join(
            [f"- {img['name']}" for img in gmc_all_images_list]
        )
        prompt_step_4_with_names = PROMPT_PASO_4_GMC_IMG.replace(
            "[LISTA_DE_NOMBRES_DE_ARCHIVO_ADJUNTOS]", gmc_names_list
        )
        send_message_to_chat(
            chat,
            prompt_step_4_with_names,
            files_to_upload=[gmc_pdf_info] + gmc_all_images_list,
            expect_response=False,
        )

        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.85)
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15)

        # 9.3. Prompt final
        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.90)

        final_deliverable_text = send_message_to_chat(
            chat,
            final_prompt_text.replace(
                "[NOMBRE CLIENTE]", str(client_name)
            ),
            files_to_upload=[],
            expect_response=True,
        )

        if "ERROR:" in str(final_deliverable_text):
            print(
                f"❌ No se pudo generar el entregable final: "
                f"{final_deliverable_text}"
            )
            if worksheet:
                update_progress_in_sheet(
                    worksheet,
                    row_to_process,
                    0,
                    status_text="ERROR: IA Ensamblaje",
                )
            return

        print("🎉 ¡Entregable final generado por la IA!")
        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.95)

        # 10. GUARDAR Y SUBIR ENTREGABLE
        uploaded_files = save_final_deliverable(
            drive_service,
            final_deliverable_text,
            client_name,
            client_folder_id,
            temp_dir,
            abuse_images_list,
            gmc_all_images_list,
        )

        # 11. ESCRIBIR ENLACES EN LA HOJA
        if uploaded_files:
            write_links_to_sheet(
                gc,
                SHEET_URL,
                SHEET_NAME,
                row_to_process,
                uploaded_files,
            )
            if worksheet:
                update_progress_in_sheet(worksheet, row_to_process, 1.0)
        else:
            print(
                "⚠️ No se recibieron enlaces de archivos subidos, "
                "no se puede actualizar la hoja."
            )
            if worksheet:
                update_progress_in_sheet(
                    worksheet,
                    row_to_process,
                    0,
                    status_text="ERROR: Subida Drive",
                )

    except Exception as e:
        print(f"❌ Un error general ha ocurrido: {e}")
        if worksheet:
            update_progress_in_sheet(
                worksheet,
                row_to_process,
                0,
                status_text="ERROR: Script falló",
            )

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n✅ Directorio temporal '{temp_dir}' eliminado.")


if __name__ == "__main__":
    row = int(os.getenv("ROW_TO_PROCESS", "117"))
    main(row)
