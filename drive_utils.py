# drive_utils.py
from __future__ import annotations

import os
import io
from typing import List, Dict, Any

from googleapiclient.discovery import Resource
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError


def find_item_in_drive(
    drive_service: Resource,
    parent_id: str,
    item_name_lower: str,
    mime_type: str,
) -> str | None:
    """
    Busca un item con nombre exacto (case-insensitive) y tipo MIME en una carpeta.
    """
    try:
        query = (
            f"'{parent_id}' in parents and trashed = false "
            f"and mimeType = '{mime_type}'"
        )
        results = (
            drive_service.files()
            .list(q=query, fields="files(id, name)")
            .execute()
        )
        items = results.get("files", [])

        for item in items:
            if item["name"].lower() == item_name_lower:
                print(f"✅ Encontrado '{item['name']}' (ID: {item['id']})")
                return item["id"]

        print(f"⚠️ No se encontró el item '{item_name_lower}' en la carpeta {parent_id}.")
        return None

    except Exception as e:
        print(f"❌ Error buscando item '{item_name_lower}': {e}")
        return None


def download_file(
    drive_service: Resource,
    file_id: str,
    filename: str,
    output_directory: str,
) -> str | None:
    """
    Descarga un archivo de Drive en un directorio local y devuelve la ruta.
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    output_path = os.path.join(output_directory, filename)

    try:
        request = drive_service.files().get_media(fileId=file_id)
        with io.FileIO(output_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        print(f"   ... Archivo '{filename}' descargado en '{output_path}'")
        return output_path

    except HttpError as error:
        print(f"❌ Error HTTP al descargar '{filename}': {error}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al descargar '{filename}': {e}")
        return None


def list_and_download_images(
    drive_service: Resource,
    folder_id: str | None,
    output_dir: str,
) -> List[Dict[str, Any]]:
    """
    Lista y descarga imágenes/PDFs de una carpeta de Drive.
    """
    image_list: List[Dict[str, Any]] = []

    if not folder_id:
        print(
            "⚠️ No se proporcionó ID de carpeta de evidencias. "
            "Omitiendo descarga de imágenes."
        )
        return []

    try:
        query = (
            f"'{folder_id}' in parents and trashed = false and "
            "(mimeType contains 'image/' or mimeType = 'application/pdf')"
        )
        files = (
            drive_service.files()
            .list(q=query, fields="files(id, name, mimeType)")
            .execute()
            .get("files", [])
        )

        if not files:
            print("⚠️ No se encontraron imágenes/PDFs en la carpeta de evidencias.")
            return []

        for file in files:
            file_path = download_file(
                drive_service, file["id"], file["name"], output_dir
            )
            if file_path:
                image_list.append(
                    {
                        "name": file["name"],
                        "path": file_path,
                        "id": file["id"],
                        "mimeType": file["mimeType"],
                    }
                )

        print(
            f"✅ Se descargaron {len(image_list)} imágenes/PDFs de evidencia "
            f"de esta carpeta."
        )
        return image_list

    except Exception as e:
        print(f"❌ Error al listar o descargar imágenes de la carpeta de evidencias: {e}")
        return []


def find_multiple_files_with_keywords(
    drive_service: Resource,
    parent_id: str,
    keywords_list: List[str],
    mime_types_list: List[str],
    download_dir: str,
) -> List[Dict[str, Any]]:
    """
    Busca archivos que contengan *cualquiera* de las palabras clave en su nombre
    y sean de *cualquiera* de los tipos MIME especificados. Descarga los archivos
    encontrados.
    """
    found_files: List[Dict[str, Any]] = []
    mime_query_parts = [f"mimeType = '{mt}'" for mt in mime_types_list]
    mime_query = " or ".join(mime_query_parts)
    query = (
        f"'{parent_id}' in parents and trashed = false and ({mime_query})"
    )

    print("   ... Ejecutando query en Drive.")

    try:
        results = (
            drive_service.files()
            .list(q=query, fields="files(id, name, mimeType)")
            .execute()
        )
        items = results.get("files", [])

        for item in items:
            item_name_lower = item["name"].lower()

            if any(kw.lower() in item_name_lower for kw in keywords_list):
                print(
                    f"   ✅ Encontrado archivo '{item['name']}' "
                    f"(ID: {item['id']}) que contiene {keywords_list}."
                )

                file_path = download_file(
                    drive_service, item["id"], item["name"], download_dir
                )
                if file_path:
                    found_files.append(
                        {
                            "name": item["name"],
                            "path": file_path,
                            "id": item["id"],
                            "mimeType": item["mimeType"],
                        }
                    )

        if not found_files:
            print(
                f"   ⚠️ No se encontró ningún archivo con palabras clave "
                f"{keywords_list} en {parent_id}."
            )

        return found_files

    except Exception as e:
        print(
            f"   ❌ Error buscando archivos con palabras clave "
            f"{keywords_list}: {e}"
        )
        return []
