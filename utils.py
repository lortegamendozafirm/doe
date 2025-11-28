import re

def get_folder_id_from_url(url):
    match = re.search(r'/folders/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    else:
        print(f"❌ No se pudo extraer el ID de la carpeta de la URL: {url}")
        return None

