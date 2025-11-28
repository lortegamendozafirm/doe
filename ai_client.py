# ai_client.py
from __future__ import annotations

import os
import mimetypes
from typing import List, Dict, Any

from PIL import Image
from vertexai.preview.generative_models import GenerativeModel, Part
from google.cloud import aiplatform

from prompt import PROMPT_INSTRUCCIONES_SISTEMA

# -------------------------------------------------
# Inicialización de Vertex AI y modelos Gemini
# -------------------------------------------------

try:
    aiplatform.init(project="supportccc")
    print("✅ Plataforma Vertex AI inicializada para el proyecto 'supportccc'.")
except Exception as e:
    print(f"❌ Error al inicializar Vertex AI: {e}")
    raise

model_pro = GenerativeModel(
    "gemini-2.5-pro",
    generation_config={"temperature": 0, "max_output_tokens": 65535},
)

model_flash = GenerativeModel(
    "gemini-2.5-flash",
    generation_config={"temperature": 0, "max_output_tokens": 65535},
)

print("✅ Modelos Gemini 2.5 Pro y 2.5 Flash cargados desde Vertex AI.")


# -------------------------------------------------
# Funciones de comunicación con la IA
# -------------------------------------------------

def send_message_to_chat(
    chat_session,
    prompt_text: str,
    files_to_upload: List[Dict[str, Any]] | None = None,
    expect_response: bool = False,
) -> str | None:
    """
    Envía un mensaje (y opcionalmente archivos) a una sesión de chat de Gemini.
    Hace un intento con Pro y un fallback con Flash si se espera respuesta.
    """
    if files_to_upload is None:
        files_to_upload = []

    message_parts: List[Any] = [prompt_text]

    for file_info in files_to_upload:
        file_path = file_info["path"]

        if not os.path.exists(file_path):
            print(f"   ⚠️ Advertencia: El archivo {file_path} no existe. Omitiendo.")
            continue

        mime_type = file_info.get("mimeType")
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(file_path)

        # Soporte HEIC/HEIF → JPEG
        if mime_type is None and any(
            file_path.lower().endswith(ext) for ext in [".heic", ".heif"]
        ):
            try:
                print(f"   ... Convirtiendo {file_path} a JPEG...")
                img = Image.open(file_path)
                jpeg_path = os.path.splitext(file_path)[0] + ".jpg"
                img.convert("RGB").save(jpeg_path)
                file_path = jpeg_path
                mime_type = "image/jpeg"
            except Exception as e:
                print(f"   ❌ Error al convertir {file_path}: {e}. Omitiendo archivo.")
                continue
        elif mime_type is None:
            print(
                f"   ⚠️ No se pudo determinar el MIME type de {file_path}. "
                "Omitiendo."
            )
            continue

        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            message_parts.append(Part.from_data(file_data, mime_type))
        except Exception as e:
            print(f"   ❌ Error al leer el archivo {file_path}: {e}. Omitiendo.")
            continue

    # Intento 1 (Pro)
    try:
        print(
            f"   🧠 Intento 1 (Pro): Enviando prompt "
            f"(expect_response={expect_response}) con {len(files_to_upload)} archivos..."
        )
        response = chat_session.send_message(message_parts)
        if expect_response:
            print("   ✅ Respuesta final recibida (Intento 1).")
            return response.text
        else:
            print("   ✅ Datos cargados (Intento 1), esperando siguiente paso.")
            return None
    except Exception as e:
        print(f"   ⚠️ Falló el Intento 1 (Pro): {e}")

    # Intento 2 (Flash) - Solo si se espera respuesta final
    if expect_response:
        try:
            print("   🧠 Intento 2 (Flash): Enviando al modelo Gemini 2.5 Flash...")
            model_flash_with_system = GenerativeModel(
                model_flash._model_name,
                generation_config=model_flash._generation_config,
                system_instruction=PROMPT_INSTRUCCIONES_SISTEMA,
            )
            chat_flash = model_flash_with_system.start_chat()
            response = chat_flash.send_message(message_parts)
            print("   ✅ Intento 2 exitoso.")
            return response.text
        except Exception as e:
            print(
                f"   ⚠️ Falló el Intento 2 (Flash): {e}"
            )
            return (
                "ERROR: No se pudo generar la respuesta después de 2 intentos. "
                f"Error: {e}"
            )
    else:
        print("   ❌ Error crítico en la carga de datos. Deteniendo el flujo.")
        raise Exception("No se pudo cargar el contexto en la IA.")


def process_file_with_prompt(
    file_info: Dict[str, Any],
    prompt_template: str,
    model_to_use: GenerativeModel,
    client_name: str,
) -> str:
    """
    Ejecuta un prompt en un archivo específico usando un modelo de IA y devuelve
    el texto procesado.
    """
    print(f"\n🧠 Procesando '{file_info['name']}' con prompt intermedio...")

    prompt_final = prompt_template.replace(
        "{transcription_content}",
        f"Contenido adjunto en el archivo '{file_info['name']}'. "
        f"Nombre del Cliente: {client_name}",
    )

    try:
        model_with_system = GenerativeModel(
            model_to_use._model_name,
            generation_config=model_to_use._generation_config,
            system_instruction=PROMPT_INSTRUCCIONES_SISTEMA,
        )
    except Exception as e:
        print(
            "   ⚠️ Advertencia: Error al configurar System Instruction "
            f"en el modelo: {e}. Usando modelo base."
        )
        model_with_system = model_to_use

    chat_session = model_with_system.start_chat()

    try:
        processed_text = send_message_to_chat(
            chat_session,
            prompt_final,
            files_to_upload=[file_info],
            expect_response=True,
        )
        print(f"   ✅ Procesamiento de '{file_info['name']}' completado.")
        return str(processed_text)
    except Exception as e:
        print(f"   ❌ Error al procesar '{file_info['name']}': {e}")
        return (
            f"[ERROR_PROCESAMIENTO: No se pudo generar el texto para "
            f"{file_info['name']}. Falló la IA: {e}]"
        )
