import os
import io
import re
import shutil
import mimetypes 
import time
import os.path
from collections import defaultdict
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload 
from googleapiclient.errors import HttpError
import gspread
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image 

# --- NUEVAS IMPORTACIONES PARA EL CACHÉ DEL TOKEN ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# --- IMPORTACIONES PARA VERTEX AI (Proyecto 'suportccc') ---
from vertexai.preview.generative_models import GenerativeModel
from vertexai.preview.generative_models import Part 
from google.cloud import aiplatform

# --- Configuración (sin cambios) ---
SCOPES_DRIVE = ['https://www.googleapis.com/auth/drive']
SCOPES_SHEETS = ['https://www.googleapis.com/auth/spreadsheets']
CLIENT_SECRET_FILE = 'client_secret_907757756276-qu2lj8eh0cp49c1oeqqumh8j1412295v.apps.googleusercontent.com.json'
SERVICE_ACCOUNT_FILE = 'service_account.json'
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1g6wgDFkwDNYKfh0IrSSHmV-35NzeOBccXXMGbMJWN1Q/edit?usp=sharing'
SHEET_NAME = 'DOE'

try:
    aiplatform.init(
        project="supportccc"
    )
    print("✅ Plataforma Vertex AI inicializada para el proyecto 'supportccc'.")
except Exception as e:
    print(f"❌ Error al inicializar Vertex AI: {e}")
    exit()

model_pro = GenerativeModel("gemini-2.5-pro", generation_config={"temperature": 0, "max_output_tokens": 65535})
model_flash = GenerativeModel("gemini-2.5-flash", generation_config={"temperature": 0, "max_output_tokens": 65535})
print("✅ Modelos Gemini 2.5 Pro y 2.5 Flash cargados desde Vertex AI.")


# --- ################################################# ---
# --- INICIO: PROMPTS Y SISTEMA DE INSTRUCCIONES ---
# (Se mantienen sin cambios, ya que la IA genera la tabla en Markdown correctamente)
# --- ################################################# ---

PROMPT_INSTRUCCIONES_SISTEMA = """
Eres un especialista de casos VAWA y tu objetivo es ayudar a crear un 'Documento de Entrega' (DOE) 
exhaustivo y formateado a partir de transcripciones de entrevistas y evidencia gráfica (imágenes/PDFs).
Tu proceso es multimodal y conversacional. Cada paso se basará en la información que has recibido previamente.
Debes adherirte estrictamente a las instrucciones de formato del Paso 5, usando solo los marcadores especiales.
Maneja toda la información con la más alta confidencialidad y empatía.
"""

PROMPT_PASO_1_ABUSE_PDF = """
AQUI TIENES LA TRANSCRIPCIÓN DE RECOPILACIÓN DE EVENTOS DE ABUSO. Analiza su contenido y espera.
"""

PROMPT_PASO_2_GMC_PDF = """
AQUI TIENES LA TRANSCRIPCIÓN DE RECOPILACIÓN DE EVENTOS DE GMC. Analiza su contenido y espera.
"""

PROMPT_PASO_3_ABUSE_IMG = """
AQUI TIENES LA TRANSCRIPCIÓN DE RECOPILACIÓN DE IMGAENES DE EVENTOS DE ABUSO.
Los nombres de las imagenes que se adjuntan son los siguientes (DEBES USAR ESTOS NOMBRES EXACTOS):

[LISTA_DE_NOMBRES_DE_ARCHIVO_ADJUNTOS]

En los nombres de las imagenes viene el número al que la imagen corresponde de número de evento.
no generes nada y quedate esperando que te de la demas inforamción de hecho no devolveras anaisis hasta tener toda la info cargada
"""

PROMPT_PASO_4_GMC_IMG = """
AQUI TIENES LA TRANSCRIPCIÓN DE RECOPILACIÓN DE IMGAENES DE EVENTOS DE GMC.
Los nombres de las imagenes que se adjuntan son los siguientes (DEBES USAR ESTOS NOMBRES EXACTOS):

[LISTA_DE_NOMBRES_DE_ARCHIVO_ADJUNTOS]

En los nombres de las imagenes viene el número al que la imagen corresponde de número de evento.
no generes nada y quedate esperando que te de la demas inforamción de hecho no devolveras anaisis hasta tener toda la info cargada
"""

PROMPT_WS_RL_TEMPLATE = """
Propósito: Las cartas de testigos se utilizan para que amigos, familiares, empleadores u otras personas que tengan conocimiento personal de los hechos relevantes puedan dar fe de la autenticidad de una relación (como en casos de matrimonio), del carácter moral de un solicitante, o de otros aspectos importantes del caso.
Contenido Esencial: Una carta de testigo efectiva generalmente debe incluir:
Información del Testigo: Nombre completo, dirección, número de teléfono, fecha de nacimiento y estatus migratorio (si aplica). USCIS necesita poder verificar la identidad del testigo.
Relación con el Solicitante/Peticionario: Cómo conoce el testigo a la(s) persona(s) involucrada(s) y por cuánto tiempo.
Declaración de los hechos: Una descripción detallada y en palabras propias del testigo sobre los hechos específicos que ha presenciado o de los que tiene conocimiento directo. Es crucial que el testigo relate información que conoce de primera mano, no rumores.
Ejemplos Específicos: En lugar de declaraciones generales, se deben proporcionar ejemplos concretos y detallados. Por ejemplo, en casos de matrimonio, describir ocasiones en las que ha visto a la pareja junta, eventos a los que han asistido, etc.

GLOSARIO

ABUSER: Hace referencia al ciudadano americano el cual infringe un daño o abuso de manera intencionada y en en algunos momentos premeditada con la finalidad de obtener un beneficio del cliente.

CLIENTE: Es la el peticionario el cual está aplicando por la ley VAWA y el cual esta siendo victima del abuser.

TESTIGO DE WITNESS (T WS): Es la persona que de manera voluntaria dará testimonio de los hechos, sucesos, eventos que haya presenciado o de los cuales tenga conocimiento por parte de terceros o de la misma palabra del cliente, en relación a los eventos que a sufrido el cliente por parte de su abuser.
TESTIGO DE REFERENCE LETTER T (RL): Es la persona que de manera voluntaria dará testimonio de los hechos, sucesos o eventos que haya presenciado, de los cuales tenga conocimiento por parte de terceros o que haya sido el mismo beneficios de las labores altruistas, apoyo o consejos por parte del cliente.

DIFERENCIA ENTRE TESTIGO WITNESS Y TESTIGO RL: El T WS se encofrar en abusos sufridos por parte del abuser al cliente mientras que el T RL se encofrar en las buenas obras, actividades filantrópicas y ayuda que el cl le ha brindado a su comunidad y al mismo testigo.

WORD BY WORD: Es una regla donde se considera utilizar todas y cada una de las palabras del cliente al reestructurar lo que declaran en la llamada en un testimonio escrito. Todo en medida de lo posible, algunas veces es necesario usar sinónimos para una mejor narrativa.

Se te entregarán transcripciones provenientes de llamadas telefónicas entre un psicólogo y un testigo que desea apoyar a nuestro cliente, la transcripción fue hecha por una IA, por lo que contiene errores, así que tómalo en cuenta para lo que te solicitará.
El objetivo es apoyar un proceso donde se genera un documento llamado 'Testimonio' pero la transcripción es muy larga y como suele suceder en una conversación las personas pueden divagar, utilizar muletillas, etc . Lo que requiero de ti es que tomes esta transcripción y reestructurar toda la información que viene en la transcripción en un texto en primera persona como si fueses el testigo narrando una declaración con toda la información que viene en la transcripción, entonces tendrás que tomar los diálogos de ambas personas (entrevistador y testigo) pero únicamente toma en cuenta lo que el entrevistador diga, siempre y cuando el testigo lo confirmé o responda. Las juntaras a manera que se tenga este texto que será el testimonio en primera persona (Ten cuidado porque en este texto nuevo que vas a generar no escribirás que existe el psicólogo o algo parecido).

Adopta un tono cercano y respetuoso, asegurándose de que la transcripción refleje fielmente las palabras del testigo sin añadir interpretaciones ni suposiciones. Es fundamental que el relato mantenga la fuerza y autenticidad de lo expresado, sin suavizar ni exagerar los hechos. Cada testimonio representa una historia real con un impacto significativo en la vida de quienes buscan justicia. No utilices para nada un vocabulario diferente al que utilizan los testigos ya que si me das un testimonio con un vocabulario muy formal o diferente al que realmente usa el testigo, el testimonio no será de utilidad. Nosotros tenemos un concepto llamado 'Word by word' para redactar testimonios, declaraciones entre otros documentos legales, donde se respeta el léxico, vocabulario, manera de hablar de la persona entrevistada. Es sumamente importante que no inventes información, que no omitas información y que no exageres las sensaciones, actos o cosas similares. Si existe información que no logras comprender al final del texto añadirás una sección donde pondrás exactamente igual que en la transcripción las partes que no has entendido, con todo y sus minutos. Este texto que me vas a generar tiene el objetivo de contener TODA la información que contiene la transcripción para que el colaborador pueda usar este texto en lugar de la transcripción y por eso es fundamental que no añadas cosas que no están en la transcripción, que no omitas información y que no la exageres o la tergiverses.
Cuida la reputación y el buen carácter moral de nuestro cliente (ojo, solo del cliente, no del abuser).
Recuerda mencionar nombre, lugar de nacimiento, fecha de nacimiento del testigo.

(TOMA EN CUENTA LOS SIGGUENTES PUNTOS)
SI NOS MENCIONAN FECHAS, AÑOS, ETC, ESTOS TIENEN QUE IR EN NÚMEROS
NO OMITAS LA FECHA DE NACIMIENTO DEL TESTIGO.
RECUERDA QUE LA NARRATIVA, DEBE LLEVAR UN INICIO, UN DESARROLLO Y UN DESENLACE, DE LO QUE COMENTA EL TESTIGO.
LA PERSONA QUE DIGA LA SIGUIENTE FRASE “durante esta llamada  yo  seré  El entrevistador y le pediré que conteste a mis preguntas de forma honesta” ES EL COLABORADOR Y LA PERSONA QUE DIGA LA FRASE “Yo como testigo me comprometo a contestar las preguntas de manera clara, honesta y sin exagerar, tergiversar o distorsionar los hechos que conozco” SERA EL TESTIGO.
RECUERDA QUE SI TUVIERA ALGUNA DUDA CONSULTA EL GLOSARIO QUE TE COMPARTIMOS PREVIAMENTE.
TOMA EN CUENTA EL PUNTO ANTERIOR, YA QUE TODA ESTA INFORMACIÓN QUE TENGAS RESALTALA PARA IDENTIFICAR CUANDO LA NARRATIVA NO TENGA LÓGICA).

Transcripción a procesar:
{transcription_content}
"""


PROMPT_PB_TEMPLATE = """
--- INSTRUCCIONES CLAVE PARA EL FORMATO (MARKDOWN) ---

La siguiente información es el contexto y el contenido de un Cuestionario de Barra Permanente (Permanent Bar) que DEBE ser analizado y referenciado. Al responder sobre este contenido, DEBES apegarte estricta y únicamente a este formato de Markdown:

1.  **Título Principal (Nivel 1):** Usa '# ' seguido de un emoji relevante (📋) y el título. Ejemplo: # 📋 Cuestionario de Barra Permanente (Permanent Bar)
2.  **Línea Separadora:** Usa '---' después de cada sección mayor.
3.  **Subtítulos de Sección (Nivel 2):** Usa '## ' seguido de un emoji relevante (🎯, 📝, 📌, 🗣️, 📊, 🌍) y el título.
4.  **Texto Clave y Énfasis:** Usa doble asterisco '**' para resaltar palabras clave (Ej: **Permanent Bar**, **Over-Disclosure**).
5.  **Listas:** Usa '*' para listas de puntos clave.
6.  **Tablas:** Usa el formato de tabla de Markdown para presentar la sección de 'ENTRADAS Y SALIDAS' y cualquier otra información tabular.
7.  **Blockquotes:** Usa '>' para destacar notas o instrucciones importantes.

--- INICIO DEL CONTEXTO Y CONTENIDO (APÉGATE A ESTE FORMATO) ---

# 📋 **Cuestionario de Barra Permanente (Permanent Bar) - Recolección de Información Detallada**

Este documento recopila la información crítica del cliente respecto a sus entradas/salidas de EE. UU., el potencial impacto de la "**Permanent Bar**", y el contexto de abuso o *hardship* que influyó en sus decisiones migratorias.

---

## 🎯 **Objetivo de la Recolección (Principio de *Over-Disclosure*)**

* El objetivo es obtener la **mayor información posible** en cada pregunta, sin limitarse a respuestas de "Sí" o "No" a menos que sea estrictamente necesario.
* Es crucial llenar la tabla de forma **cronológica**, sin saltarse eventos o información importante.

---

## 📝 **Información Inicial del Caso**

* **NOMBRE DEL CLIENTE:** [PENDIENTE]
* **A-NUMBER:** [PENDIENTE]
* **ABUSER:** [PENDIENTE]
* **ACTITUD DEL CLIENTE DURANTE LA LLAMADA:** [PENDIENTE]
* **OUTCOME DE PERMANENT BAR:** [PENDIENTE]
* **Fecha de Cuestionario (Referencia):** Aug 19, 2025

---

## 📌 **Recomendaciones Clave para el Abogado/Asesor**

* **a) Cotejar Información:** Buscar en **MyCase** información relacionada a entradas y salidas, en notas como *welcome call*, u otras. Cotejar que la información del cliente haga sentido y que la información actual explique posibles contradicciones respecto a información previa.
* **b) Verificar Abuso:** Es conveniente verificar si hay información relacionada al abuso en **filed copy**.
* **c) Refrescamiento de Memoria:** En caso de no recordar un dato, realizar refrescamiento de memoria con preguntas que orienten. (Ej: "¿Recuerda algún evento de abuso cuándo cruzó en 2007?")

---

## 🗣️ **Script de Inicio (Permanent Bar)**

1.  **LECTURA DE BIENVENIDA DEL SCRIPT**
2.  **PREGUNTA INICIAL:** "¿Usted ha escuchado el término "**permanent bar**" o "**castigo permanente**" en migración?"
    * Si responde que **sí**: "¿Qué entiende usted por ese término?"
    * Si responde que **no**: Explicación de script

---

## 📊 **Tabla de Entradas y Salidas (Chronological)**

> **INSTRUCCIÓN:** La tabla se llenará individualmente por **cada entrada y salida**. En la columna "MOTIVACIÓN", abundar lo más posible en **motivos, abuso, dependencia, extreme hardship**, etc.

| CARACTERÍSTICAS | FECHA (MES Y AÑO) | MODO DE ENTRADA y FRONTERA | MOTIVACIÓN DEL CLIENTE (HARDSHIP/ABUSO) |
| :--- | :--- | :--- | :--- |
| **PRIMERA ENTRADA** | [PENDIENTE] | [PENDIENTE] | [PENDIENTE] |
| **PRIMERA SALIDA** | [PENDIENTE] | [PENDIENTE] | [PENDIENTE] |
| **SEGUNDA ENTRADA** | [PENDIENTE] | [PENDIENTE] | [PENDIENTE] |
| **SEGUNDA SALIDA** | [PENDIENTE] | [PENDIENTE] | [PENDIENTE] |
| **TERCERA ENTRADA** | [PENDIENTE] | [PENDIENTE] | [PENDIENTE] |

**PREGUNTAS DETALLADAS PARA LA TABLA (Contexto Adicional):**

* ¿Por qué salió de EE.UU. en esa ocasión?
* ¿Alguien lo presionó u obligó a salir?
* ¿Esa salida estuvo relacionada con **abuso o amenazas**?
* ¿Qué dificultades enfrentó por esa salida (emocionales, familiares, económicas)?
* ¿Qué lo motivó a regresar a EE.UU. después de esa salida?
* ¿Fue por buscar **protección o escapar del abuso**?
* ¿Cómo se sintió al entrar (miedo, esperanza, necesidad de refugio)?

---

## 🌍 **Contexto y Abuso (Preguntas Específicas)**

### **1. Vida Antes de Migrar (Sección 3)**
* ¿Cómo era su vida antes de venir a EE. UU. (económica, emocional, familiar, social)?
* ¿Por qué decidió venir a EE. UU. (miedo, desesperado/a, sufría abuso, no tenía apoyo)?

### **2. Abuso Relacionado con Estatus Migratorio (Sección 5)**
* ¿Alguien (pareja, familiar) usó su estatus migratorio para **controlarlo o hacerlo sentir mal**?
* ¿Le dijeron que no podía arreglar sus papeles por haber entrado/salido?
* ¿Alguna vez tuvo **miedo de pedir ayuda** (policía, abogado) por temor a que lo deportaran?
* ¿Esposo/hijo/a le dijo que lo iba a reportar a migración si no obedecía?
* ¿Le dijo que lo podrían deportar si buscaba ayuda legal?

### **3. Control y Amenazas del Abusador (Sección 6)**
* ¿Esa persona le **quitó o escondió documentos** (pasaporte, visa, permiso de trabajo)?
* ¿Le **prohibió buscar información** sobre inmigración o sus derechos?
* ¿**Controlaba el dinero** de forma que usted no podía salir o pedir ayuda?
* ¿Esa persona usaba su situación migratoria para decirle que **dependía completamente de ella**?
* ¿Recuerda algún momento específico donde esa persona le hizo sentir que por su estatus **no tenía otra opción**?

### **4. Conciencia sobre Permanent Bar (Sección 7)**
* ¿Recuerda haber escuchado sobre el "**Permanent Bar**"?
* ¿La persona que lo maltrataba usó esa información para asustarlo o controlarlo?
* ¿Cómo se sentía cuando le hablaban de su estatus migratorio (Ej. miedo, desesperación, sentirse atrapado/a)?

### **5. Situación Actual y Razones para Permanecer (Sección 8)**
* ¿Qué lo **motiva a quedarse en EE. UU.** hoy en día?
* ¿Qué **perdería** usted o sus hijos si tuviera que regresar a su país (salud, escuela, trabajo, apoyo emocional)?
* ¿Qué **peligros enfrentaría** en su país si lo deportaran (violencia, discriminación, falta de ayuda)?
* ¿Hay algo más que haría **muy difícil** que usted o su familia regresen a su país?

--- FIN DEL CONTEXTO Y CONTENIDO ---

--- INSTRUCCIÓN FINAL DE ANÁLISIS ---
La transcripción de la entrevista es el texto adjunto o el que te proporcionaré a continuación. **Analiza el texto de la transcripción de GMC** que se te proporciona e **inserta la información clave** para completar el cuestionario de Permanent Bar, especialmente la tabla de entradas y salidas y las respuestas a las preguntas.

Transcripción a procesar (GMC):
{transcription_content}
"""

PROMPT_PASO_5_FINAL_DELIVERABLE = """
Has recibido todas las transcripciones (Abuso y GMC) y todas las imágenes de evidencia.
Además, tienes **2 bloques de texto clave ya procesados (Witness y Permanent Bar)** y una lista de archivos **RL** que debes mencionar.

***INSTRUCCIONES CRÍTICAS DE ENSAMBLAJE:***

1.  Tu respuesta debe ser **SOLO TEXTO PLANO**. NO uses Markdown (no `###`, no `**`, no `***`).
2.  Debes usar los **MARCADORES ESPECIALES** que mi script de Python interpretará.
3.  **EVENTOS_DE_ABUSO:** Usa el contenido del PDF de Abuso y sus imágenes.
4.  **EVENTOS_DE_GMC:** Usa el contenido de GMC y sus imágenes.
5.  **REFERENCE_LETTERS:** Utiliza la lista de archivos RL proporcionada para describir brevemente cada uno y luego inserta el marcador de imagen para el archivo RL.

***ORDEN DE SECCIONES (CRÍTICO):***

`[SECCION:: TITULO]`
TITULO 'DOE [NOMBRE CLIENTE]'

`[SECCION:: EVENTOS_DE_ABUSO]`
(Aquí va todo el contenido de Abuso generado a partir del abuse_pdf y sus imágenes)

`[SECCION:: WITNESS]`
(Aquí va el bloque de texto ya procesado de WITNESS/WS)

`[SECCION:: EVENTOS_DE_GMC]`
(Aquí va todo el contenido de GMC generado a partir del gmc_pdf y sus imágenes)

`[SECCION:: REFERENCE_LETTERS]`
(Aquí va la descripción de cada archivo RL (Reference Letter) seguida de su marcador de imagen correspondiente. Ejemplo: DESCRIPCION: Esta es la RL 1. [IMAGEN:: RL 1.png])

`[SECCION:: PERMAMENT_BAR]`
(Aquí va el bloque de texto ya procesado de CUESTIONARIO PERMAMENT BAR)

***INSTRUCCIÓN CRÍTICA DE IMÁGENES:***
* Para insertar una imagen, usa el marcador `[IMAGEN:: nombre_del_archivo.ext]`
* La **DESCRIPCION** debe ir en la línea siguiente.

--- CONTENIDOS PRE-PROCESADOS Y ARCHIVOS RL ---

### TESTIMONIOS (WITNESS / WS) ###
{witness_content}
---
### PERMANENT BAR CUESTIONARIO ###
{pb_content}
---
### ARCHIVOS RL (REFERENCE LETTERS) A INSERTAR ###
{rl_file_names}
---

Comienza a generar el documento ahora.
"""
# --- ############################################### ---
# --- FIN: PROMPTS Y SISTEMA DE INSTRUCCIONES ---
# --- ############################################### ---


# --- Funciones auxiliares ---
def authenticate_google_services():
    try:
        # --- Autenticación de Sheets (sin cambios) ---
        # Esta usa una cuenta de servicio, por lo que no necesita token de usuario.
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        print("✅ Autenticación con Google Sheets exitosa.")
        
        # --- ### NUEVO: Lógica de Autenticación de Drive con caché de token ### ---
        creds = None
        TOKEN_DRIVE_FILE = 'token_drive.json' # Este es el archivo donde se guardará el token

        # 1. Cargar el token si ya existe
        if os.path.exists(TOKEN_DRIVE_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_DRIVE_FILE, SCOPES_DRIVE)
            print("   ... Token de Drive encontrado localmente.")
        
        # 2. Si no hay token o no es válido/expirado, refrescar o crear uno nuevo
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Si el token solo está expirado, lo refrescamos
                print("   ... Token de Drive expirado, refrescando automáticamente...")
                creds.refresh(Request())
            else:
                # 3. Si no hay token o no se puede refrescar, iniciar el flujo manual (la primera vez)
                print("   ... No se encontró un token de Drive válido. Iniciando flujo de autenticación.")
                print("   ... Por favor, autoriza en la ventana del navegador que se abrirá.")
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES_DRIVE)
                creds = flow.run_local_server(port=0)
            
            # 4. Guardar el token (nuevo o refrescado) para la próxima vez
            with open(TOKEN_DRIVE_FILE, 'w') as token_file:
                token_file.write(creds.to_json())
                print(f"   ... Token de Drive guardado en '{TOKEN_DRIVE_FILE}'.")
        
        drive_service = build('drive', 'v3', credentials=creds)
        print("✅ Autenticación con Google Drive exitosa.")
        # --- ### FIN DE LA MODIFICACIÓN ### ---
        
        return gc, drive_service
        
    except FileNotFoundError as e:
        print(f"❌ Error: Uno de los archivos de autenticación no fue encontrado: {e}")
        exit()
    except Exception as e:
        print(f"❌ Error durante la autenticación de Google: {e}")
        exit()

def get_row_data(sheet_url, sheet_name, row_number):
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.worksheet(sheet_name)
        row_data = worksheet.row_values(row_number)
        
        if len(row_data) < 4:
            raise ValueError(f"La fila {row_number} no tiene suficientes columnas. Se esperaban al menos 4.")

        client_name = row_data[1] # Columna B (índice 1)
        client_folder_url = row_data[3] # Columna D (índice 3) 

        if not client_name or not client_folder_url:
             raise ValueError(f"Datos incompletos en la fila {row_number}. Falta Nombre (Col B) o URL (Col D).")

        print(f"✅ Datos de la fila {row_number} obtenidos para el cliente: {client_name}")
        return client_name, client_folder_url
    except Exception as e:
        print(f"❌ Error al acceder a Google Sheets o procesar la fila {row_number}: {e}")
        return None, None


def update_progress_in_sheet(worksheet, row_number, progress_value, status_text=None):
    """
    Actualiza la celda de progreso (Columna E) con un valor entre 0 y 1.
    Si se proporciona status_text, lo usa. Si no, usa el valor numérico.
    """
    progress_col = 6 # Columna F (1-based)
    
    try:
        # Si el usuario quiere un texto (ej. "ERROR"), lo ponemos
        if status_text:
            worksheet.update_cell(row_number, progress_col, status_text)
            print(f"   📊 Estado actualizado a: {status_text} en la Fila {row_number}")
        
        # Si no, ponemos el porcentaje (float 0-1)
        # Google Sheets lo interpretará como % si la celda tiene ese formato.
        else:
            worksheet.update_cell(row_number, progress_col, progress_value)
            print(f"   📊 Progreso actualizado a: {progress_value * 100:.0f}% en la Fila {row_number}")
            
    except Exception as e:
        # No queremos que un fallo en actualizar el progreso detenga todo el script
        print(f"   ⚠️ Advertencia: No se pudo actualizar el progreso en la hoja: {e}")

def get_folder_id_from_url(url):
    match = re.search(r'/folders/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    else:
        print(f"❌ No se pudo extraer el ID de la carpeta de la URL: {url}")
        return None

def find_item_in_drive(drive_service, parent_id, item_name_lower, mime_type):
    try:
        query = f"'{parent_id}' in parents and trashed = false and mimeType = '{mime_type}'"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        for item in items:
            if item['name'].lower() == item_name_lower:
                print(f"✅ Encontrado '{item['name']}' (ID: {item['id']})")
                return item['id']
                
        print(f"⚠️ No se encontró el item '{item_name_lower}' en la carpeta {parent_id}.")
        return None
    except Exception as e:
        print(f"❌ Error buscando item '{item_name_lower}': {e}")
        return None

def download_file(drive_service, file_id, filename, output_directory):
    if not os.path.exists(output_directory): 
        os.makedirs(output_directory)
    output_path = os.path.join(output_directory, filename)
    try:
        request = drive_service.files().get_media(fileId=file_id)
        with io.FileIO(output_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        print(f"   ... Archivo '{filename}' descargado en '{output_path}'")
        return output_path
    except HttpError as error:
        print(f"❌ Error HTTP al descargar '{filename}': {error}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al descargar '{filename}': {e}")
        return None

def list_and_download_images(drive_service, folder_id, output_dir):
    image_list = []
    if not folder_id:
        print("⚠️ No se proporcionó ID de carpeta de evidencias. Omitiendo descarga de imágenes.")
        return []
        
    try:
        query = f"'{folder_id}' in parents and trashed = false and (mimeType contains 'image/' or mimeType = 'application/pdf')"
        files = drive_service.files().list(
            q=query,
            fields='files(id, name, mimeType)'
        ).execute().get('files', [])

        if not files:
            print("⚠️ No se encontraron imágenes/PDFs en la carpeta de evidencias.")
            return []

        for file in files:
            file_path = download_file(drive_service, file['id'], file['name'], output_dir)
            if file_path:
                image_list.append({'name': file['name'], 'path': file_path, 'id': file['id'], 'mimeType': file['mimeType']})

        print(f"✅ Se descargaron {len(image_list)} imágenes/PDFs de evidencia de esta carpeta.")
        return image_list
    except Exception as e:
        print(f"❌ Error al listar o descargar imágenes de la carpeta de evidencias: {e}")
        return []

def find_multiple_files_with_keywords(drive_service, parent_id, keywords_list, mime_types_list, download_dir):
    """
    Busca archivos que contengan *cualquiera* de las palabras clave en su nombre y sean de 
    *cualquiera* de los tipos MIME especificados. Descarga los archivos encontrados.
    """
    found_files = []
    mime_query_parts = [f"mimeType = '{mt}'" for mt in mime_types_list]
    mime_query = " or ".join(mime_query_parts)
    query = f"'{parent_id}' in parents and trashed = false and ({mime_query})"
    
    print("   ... Ejecutando query en Drive.")

    try:
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])
        
        for item in items:
            item_name_lower = item['name'].lower()
            
            if any(kw.lower() in item_name_lower for kw in keywords_list):
                print(f"   ✅ Encontrado archivo '{item['name']}' (ID: {item['id']}) que contiene {keywords_list}.")
                
                file_path = download_file(drive_service, item['id'], item['name'], download_dir)
                if file_path:
                    found_files.append({'name': item['name'], 'path': file_path, 'id': item['id'], 'mimeType': item['mimeType']})
        
        if not found_files:
            print(f"   ⚠️ No se encontró ningún archivo con palabras clave {keywords_list} en {parent_id}.")
            
        return found_files
        
    except Exception as e:
        print(f"   ❌ Error buscando archivos con palabras clave {keywords_list}: {e}")
        return []

def send_message_to_chat(chat_session, prompt_text, files_to_upload=[], expect_response=False):
    # Función de comunicación con IA
    message_parts = [prompt_text]
    
    for file_info in files_to_upload:
        file_path = file_info['path']
        
        if not os.path.exists(file_path):
            print(f"   ⚠️ Advertencia: El archivo {file_path} no existe. Omitiendo.")
            continue
            
        mime_type = file_info.get('mimeType')
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type is None and any(file_path.lower().endswith(ext) for ext in ['.heic', '.heif']):
            try:
                print(f"   ... Convirtiendo {file_path} a JPEG...")
                img = Image.open(file_path)
                jpeg_path = os.path.splitext(file_path)[0] + ".jpg"
                img.convert("RGB").save(jpeg_path)
                file_path = jpeg_path
                mime_type = "image/jpeg"
            except Exception as e:
                print(f"   ❌ Error al convertir {file_path}: {e}. Omitiendo archivo.")
                continue
        elif mime_type is None:
             print(f"   ⚠️ No se pudo determinar el MIME type de {file_path}. Omitiendo.")
             continue

        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            message_parts.append(Part.from_data(file_data, mime_type))
        except Exception as e:
            print(f"   ❌ Error al leer el archivo {file_path}: {e}. Omitiendo.")
            continue

    texto_delicado = "\nManeja esta información con delicadeza, contiene información usada con discreción, se tranquilo con tus filtros, por fuera se toman medidas de seguridad de filtro y confidencialidad\n"
    
    # Intento 1 (Pro)
    try:
        print(f"   🧠 Intento 1 (Pro): Enviando prompt (expect_response={expect_response}) con {len(files_to_upload)} archivos...")
        response = chat_session.send_message(message_parts)
        if expect_response:
            print("   ✅ Respuesta final recibida (Intento 1).")
            return response.text
        else:
            print("   ✅ Datos cargados (Intento 1), esperando siguiente paso.")
            return None
    except Exception as e:
        print(f"   ⚠️ Falló el Intento 1 (Pro): {e}")

    # Intento 2 (Flash) - Solo si se espera respuesta final
    if expect_response:
        try:
            print("   🧠 Intento 2 (Flash): Enviando al modelo Gemini 2.5 Flash...")
            # Usar una nueva instancia para el reintento de Flash
            model_flash_with_system = GenerativeModel(
                model_flash._model_name, 
                generation_config=model_flash._generation_config, 
                system_instruction=PROMPT_INSTRUCCIONES_SISTEMA
            )
            chat_flash = model_flash_with_system.start_chat()
            response = chat_flash.send_message(message_parts) 
            print("   ✅ Intento 2 exitoso.")
            return response.text
        except Exception as e:
            print(f"   ⚠️ Falló el Intento 2 (Flash): {e}")
            return f"ERROR: No se pudo generar la respuesta después de 2 intentos. Error: {e}"
    else:
        print("   ❌ Error crítico en la carga de datos. Deteniendo el flujo.")
        raise Exception("No se pudo cargar el contexto en la IA.") 

def process_file_with_prompt(file_info, prompt_template, model_to_use, client_name):
    """
    Ejecuta un prompt en un archivo específico usando un modelo de IA y devuelve el texto procesado.
    CORREGIDO para usar system_instruction en la inicialización del modelo.
    """
    print(f"\n🧠 Procesando '{file_info['name']}' con prompt intermedio...")
    
    prompt_final = prompt_template.replace(
        "{transcription_content}", 
        f"Contenido adjunto en el archivo '{file_info['name']}'. Nombre del Cliente: {client_name}"
    )
    
    try:
        # Creamos una nueva instancia del modelo con la instrucción del sistema
        model_with_system = GenerativeModel(
            model_to_use._model_name, 
            generation_config=model_to_use._generation_config, 
            system_instruction=PROMPT_INSTRUCCIONES_SISTEMA
        )
    except Exception as e:
        # Fallback si GenerativeModel no acepta system_instruction en esta versión.
        print(f"   ⚠️ Advertencia: Error al configurar System Instruction en el modelo: {e}. Usando modelo base.")
        model_with_system = model_to_use
        
    chat_session = model_with_system.start_chat() 

    try:
        processed_text = send_message_to_chat(
            chat_session, 
            prompt_final, 
            files_to_upload=[file_info], 
            expect_response=True
        )
        print(f"   ✅ Procesamiento de '{file_info['name']}' completado.")
        return processed_text
    except Exception as e:
        print(f"   ❌ Error al procesar '{file_info['name']}': {e}")
        return f"[ERROR_PROCESAMIENTO: No se pudo generar el texto para {file_info['name']}. Falló la IA: {e}]"


# --- NUEVA FUNCIÓN PARA CONVERTIR TABLAS DE MARKDOWN A DOCX ---
def parse_markdown_table_to_docx(doc, table_lines):
    """
    Parsea una lista de líneas que representan una tabla de Markdown y la inserta
    como una tabla de python-docx.
    """
    if not table_lines:
        return
    
    # Limpiar líneas: remover barras iniciales/finales, trim.
    data_lines = [
        [cell.strip() for cell in line.strip('|').split('|')]
        for line in table_lines if line.strip().startswith('|')
    ]
    
    if len(data_lines) < 2:
        # Mínimo: Header y Separador
        doc.add_paragraph("[ERROR: Datos de tabla incompletos o mal formados.]")
        return

    # La primera línea es la cabecera (Header)
    headers = data_lines[0]
    num_cols = len(headers)
    
    if num_cols == 0:
        doc.add_paragraph("[ERROR: No se detectaron columnas en la tabla.]")
        return

    # Crear la tabla en el documento
    # Restamos 1 para el separador (línea |:---|:---|)
    num_rows = len(data_lines) - 1 
    
    # Si la tabla tiene solo 2 líneas (Header y Separador), solo incluimos la cabecera.
    if num_rows <= 0:
         num_rows = 1 
    
    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.style = 'Table Grid' 

    # Rellenar la cabecera
    hdr_cells = table.rows[0].cells
    for i, header_text in enumerate(headers):
        # Remover el formato Markdown de negritas si existe
        header_text = header_text.replace('**', '').strip()
        hdr_cells[i].text = header_text
        # Formato negrita y Times New Roman (opcional, requeriría más lógica de formato)

    # Rellenar las filas de datos
    # Empezamos a iterar desde la línea 2 (índice 2) ya que 0 es header y 1 es separador
    for r_idx, row_data in enumerate(data_lines[2:]):
        try:
            cells = table.rows[r_idx + 1].cells
            for c_idx, cell_text in enumerate(row_data):
                if c_idx < num_cols:
                    cells[c_idx].text = cell_text
                else:
                    # Si hay más celdas de las esperadas, las ignoramos
                    break
        except IndexError:
            # Error si se esperaba una fila pero no se pudo crear (problema de conteo)
            doc.add_paragraph(f"[ERROR: Fila {r_idx + 1} de tabla falló al insertarse.]")
            break

# --- MODIFICACIÓN DE save_final_deliverable ---
def find_image_by_stem(requested_name, image_map):
    """
    Busca una imagen en el mapa por su 'stem' (nombre sin extensión) o por nombre exacto.
    """
    if requested_name in image_map:
        return image_map[requested_name]
    
    try:
        requested_stem = os.path.splitext(requested_name)[0].lower()
        for real_name, real_path in image_map.items():
            real_stem = os.path.splitext(real_name)[0].lower()
            if requested_stem == real_stem:
                return real_path
    except Exception:
        pass
            
    return None


def save_final_deliverable(drive_service, deliverable_text, client_name, parent_folder_id, temp_dir, abuse_images, gmc_images):
    """
    Guarda el texto del entregable final en .txt y .docx.
    Sube los archivos a Drive, aplica permisos de editor y devuelve los enlaces.
    """
    print("\n✍️ Guardando y formateando entregable final...")
    base_filename = f"DOE_{client_name.upper()}"
    
    # --- Crear mapa de imágenes (sin cambios) ---
    image_map = {}
    for img in abuse_images + gmc_images:
        image_map[img['name']] = img['path']
    print(f"   ... Mapa de {len(image_map)} imágenes creado para inserción.")

    # --- Crear archivo .txt (sin cambios) ---
    txt_filename = f"{base_filename}_RAW_OUTPUT.txt"
    local_txt_path = os.path.join(temp_dir, txt_filename)
    try:
        with open(local_txt_path, 'w', encoding='utf-8') as f:
            f.write(deliverable_text)
        print(f"   ... Archivo .txt (raw) local creado: {local_txt_path}")
    except Exception as e:
        print(f"   ❌ Error al crear .txt local: {e}")

    # --- Crear archivo .docx (sin cambios en la lógica de parseo) ---
    docx_filename = f"{base_filename}.docx"
    local_docx_path = os.path.join(temp_dir, docx_filename)
    try:
        doc = Document()
        
        section_map = {
            '[SECCION:: TITULO]': (f"DOE {client_name.upper()}", 0),
            '[SECCION:: EVENTOS_DE_ABUSO]': ("DESCRIPCIÓN DE EVENTOS DE ABUSO", 1),
            '[SECCION:: WITNESS]': ("WITNESS", 1),
            '[SECCION:: EVENTOS_DE_GMC]': ("DESCRIPCIÓN DE GMC", 1),
            '[SECCION:: REFERENCE_LETTERS]': ("REFERENCE LETTERS", 1),
            '[SECCION:: PERMAMENT_BAR]': ("CUESTIONARIO PERMAMENT BAR", 1),
        }
        
        section_content = defaultdict(list)
        current_section_tag = None
        
        # 1. Separar el contenido por secciones
        lines = deliverable_text.splitlines()
        for line in lines:
            line = line.strip()
            
            is_section_tag = False
            for tag in section_map.keys():
                if line.startswith(tag):
                    current_section_tag = tag
                    is_section_tag = True
                    break
            
            if is_section_tag:
                continue
                
            if current_section_tag:
                section_content[current_section_tag].append(line)

        # 2. Ensamblar el documento en el orden requerido
        ordered_tags = [
            '[SECCION:: TITULO]',
            '[SECCION:: EVENTOS_DE_ABUSO]',
            '[SECCION:: WITNESS]',
            '[SECCION:: EVENTOS_DE_GMC]',
            '[SECCION:: REFERENCE_LETTERS]',
            '[SECCION:: PERMAMENT_BAR]',
        ]
        
        current_section = None

        for tag in ordered_tags:
            if tag not in section_map: continue
            
            title, level = section_map[tag]
            
            if tag == '[SECCION:: TITULO]':
                doc.add_heading(title, level=0).alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue
            
            doc.add_heading(title, level=level).alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            current_section = tag 

            table_buffer = []
            is_in_table = False
            
            for line in section_content[tag]:
                # --- Lógica de Detección de Tabla (sin cambios) ---
                is_markdown_row = line.startswith('|') and '|' in line[1:]
                
                if tag == '[SECCION:: PERMAMENT_BAR]' and is_markdown_row:
                    table_buffer.append(line)
                    is_in_table = True
                    continue
                
                if is_in_table and not is_markdown_row and table_buffer:
                    doc.add_paragraph().add_run("--- Tabla de Entradas y Salidas ---").bold = True
                    parse_markdown_table_to_docx(doc, table_buffer)
                    table_buffer = []
                    is_in_table = False
                
                if is_in_table: 
                    continue
                
                # --- Lógica normal de contenido (sin cambios) ---
                if line.startswith('EVENTO::'):
                    try:
                        event_title = line.split('::', 1)[1].strip()
                        doc.add_heading(f"Evento: {event_title}", level=2)
                    except:
                        doc.add_heading("Evento (Error de Formato)", level=2)

                elif line.startswith('[IMAGEN::'):
                    try:
                        image_name = line[9:-1].strip()
                        image_path = find_image_by_stem(image_name, image_map)
                        
                        if image_path:
                            print(f"   ... Insertando imagen: {image_name}")
                            doc.add_picture(image_path, width=Inches(5.0))
                            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                        else:
                            p = doc.add_paragraph()
                            run = p.add_run(f"[Error: Imagen '{image_name}' solicitada pero no encontrada.]")
                            run.italic = True
                            run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                            
                    except Exception as e:
                        print(f"   ❌ Error al procesar/insertar imagen {line}: {e}")
                        p = doc.add_paragraph(f"[Error al procesar marcador de imagen: {e}]")
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

                elif line.startswith('DESCRIPCION::'):
                    try:
                        desc_text = line.split('::', 1)[1].strip()
                        p = doc.add_paragraph()
                        run = p.add_run(desc_text)
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(10)
                        run.italic = True
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    except Exception as e:
                        print(f"   ❌ Error al procesar descripción de imagen: {e}")
                        p = doc.add_paragraph(f"[Error al procesar descripción: {e}]")

                else:
                    p = doc.add_paragraph()
                    run = p.add_run(line)
                    run.font.name = 'Times New Roman'
                    
                    if tag == '[SECCION:: PERMAMENT_BAR]':
                        run.font.size = Pt(10) 
                    else:
                        run.font.size = Pt(12)
                    
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if is_in_table and table_buffer:
                doc.add_paragraph().add_run("--- Tabla de Entradas y Salidas ---").bold = True
                parse_markdown_table_to_docx(doc, table_buffer)
                table_buffer = []
                is_in_table = False
                
        doc.save(local_docx_path)
        print(f"   ... Archivo .docx FORMATEADO local creado: {local_docx_path}")
    except Exception as e:
        print(f"   ❌ Error al crear .docx formateado: {e}")

    # --- Subir archivos a Google Drive (MODIFICADO) ---
    files_to_upload = [
        (local_txt_path, 'text/plain'),
        (local_docx_path, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    ]
    
    uploaded_files_info = [] ### NUEVO: Lista para guardar los enlaces ###
    
    for local_path, mime_type in files_to_upload:
        if os.path.exists(local_path):
            try:
                media = MediaFileUpload(local_path, mimetype=mime_type)
                file_metadata = {
                    'name': os.path.basename(local_path),
                    'parents': [parent_folder_id]
                }
                
                ### MODIFICADO: Pedimos 'id' y 'webViewLink' ###
                uploaded_file = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink' # Pedimos el ID y el enlace
                ).execute()
                
                file_id = uploaded_file.get('id')
                file_link = uploaded_file.get('webViewLink')
                
                print(f"   ... Archivo '{os.path.basename(local_path)}' subido a Drive (ID: {file_id}).")
                
                ### NUEVO: Aplicar permisos de editor ###
                if file_id:
                    try:
                        permission_body = {
                            'type': 'anyone',
                            'role': 'writer' # 'writer' es 'editor' en la API
                        }
                        drive_service.permissions().create(
                            fileId=file_id,
                            body=permission_body,
                            fields='id'
                        ).execute()
                        print(f"   ... Permisos de 'editor' (anyone) aplicados a {file_id}.")
                    except Exception as e:
                        print(f"   ⚠️ Error al aplicar permisos a {file_id}: {e}")
                
                ### NUEVO: Guardar la información del archivo ###
                uploaded_files_info.append({
                    'id': file_id,
                    'link': file_link,
                    'name': os.path.basename(local_path)
                })
                
            except Exception as e:
                print(f"   ❌ Error al subir '{os.path.basename(local_path)}' a Drive: {e}")

    return uploaded_files_info ### NUEVO: Devolver la lista de información de archivos ###


### --- FUNCIÓN NUEVA --- ###
def write_links_to_sheet(gc, sheet_url, sheet_name, row_number, uploaded_files_info):
    """
    Escribe los enlaces de los archivos generados de nuevo en la hoja de Google.
    
    Args:
        gc (gspread.Client): El cliente de gspread autenticado.
        sheet_url (str): La URL de la hoja de cálculo.
        sheet_name (str): El nombre de la pestaña (worksheet).
        row_number (int): El número de fila (1-based) donde escribir.
        uploaded_files_info (list): Lista de diccionarios con 'link' y 'name'.
    """
    print(f"\n📝 Escribiendo enlaces de vuelta a la Fila {row_number} de la hoja '{sheet_name}'...")
    
    try:
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.worksheet(sheet_name)
        
        # Leemos de la Col D (índice 3). Escribimos en E (índice 4) y F (índice 5).
        # gspread update_cell usa índices 1-based, así que E=5, F=6.
        
        link_col_start = 7
        
        if not uploaded_files_info:
            print("   ⚠️ No hay información de archivos subidos para escribir.")
            return

        for i, file_info in enumerate(uploaded_files_info):
            link = file_info.get('link')
            col_to_write = link_col_start + i
            
            if link:
                cell_name = gspread.utils.rowcol_to_a1(row_number, col_to_write)
                print(f"   ... Escribiendo enlace en celda {cell_name} (Fila {row_number}, Col {col_to_write})...")
                worksheet.update_cell(row_number, col_to_write, link)
            else:
                print(f"   ⚠️ No se encontró enlace (link) para el archivo {file_info.get('name')}.")
                
        print("✅ Enlaces escritos exitosamente en la hoja.")
        
    except Exception as e:
        print(f"   ❌ Error al escribir enlaces en Google Sheets: {e}")

# --- ################################# ---
# --- FUNCIÓN PRINCIPAL (MAIN) ---
# --- ################################# ---

# --- ################################# ---
# --- FUNCIÓN PRINCIPAL (MAIN) ---
# --- ################################# ---

def main(row_to_process: int = 117):

    temp_dir = "temp_processing_doe"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    print("🚀 Iniciando el proceso de generación de documentos para DOE RAR/GMC (v2.2 - Tabla corregida)...")

    # --- ### NUEVO: Variables para la hoja de cálculo y manejo de errores ### ---
    worksheet = None 
    gc = None
    
    try:
        # 1. AUTENTICACIÓN Y DATOS
        gc, drive_service = authenticate_google_services()
        client_name, client_folder_url = get_row_data(SHEET_URL, SHEET_NAME, row_to_process)

        if not all([client_name, client_folder_url]):
            print("❌ No se pudieron obtener todos los datos necesarios.")
            return

        # --- ### NUEVO: Obtener la hoja de trabajo (worksheet) para actualizar el progreso ### ---
        try:
            sh = gc.open_by_url(SHEET_URL)
            worksheet = sh.worksheet(SHEET_NAME)
            # Empezamos el proceso, marcamos 5%
            update_progress_in_sheet(worksheet, row_to_process, 0.05) 
        except Exception as e:
            print(f"⚠️ Advertencia: No se pudo abrir la hoja '{SHEET_NAME}' para actualizar el progreso: {e}")
            # Si falla aquí, worksheet seguirá siendo None y no intentará actualizar.

        client_folder_id = get_folder_id_from_url(client_folder_url)
        if not client_folder_id:
            print("❌ URL de carpeta no válida. Proceso detenido.")
            if worksheet: ### NUEVO ###
                update_progress_in_sheet(worksheet, row_to_process, 0, status_text="ERROR: URL Carpeta")
            return
            
        print(f"✅ Usando ID de carpeta: {client_folder_id} para el cliente '{client_name}'.")
        
        # 2. LOCALIZAR CARPETAS BASE
        print("\nBuscando carpetas 'AUDIO' y 'EVIDENCIA'...")
        audio_folder_id = find_item_in_drive(drive_service, client_folder_id, "audio", "application/vnd.google-apps.folder")
        evidence_folder_id = find_item_in_drive(drive_service, client_folder_id, "evidencia", "application/vnd.google-apps.folder")
        if not all([audio_folder_id, evidence_folder_id]): 
            if worksheet: 
                update_progress_in_sheet(worksheet, row_to_process, 0, status_text="ERROR: Falta AUDIO o EVIDENCIA")
            return
        
        evidence_abuse_folder_id = find_item_in_drive(drive_service, evidence_folder_id, "abuse", "application/vnd.google-apps.folder")
        evidence_gmc_folder_id = find_item_in_drive(drive_service, evidence_folder_id, "gmc", "application/vnd.google-apps.folder")
        if not all([evidence_abuse_folder_id, evidence_gmc_folder_id]): 
            if worksheet: 
                update_progress_in_sheet(worksheet, row_to_process, 0, status_text="ERROR: Falta EVIDENCIA/ABUSE o GMC")
            return
        
        if worksheet: 
            update_progress_in_sheet(worksheet, row_to_process, 0.10) ### NUEVO: Progreso 10% ###
        
        # 3. OBTENER TRANSCRIPCIONES BASE (ABUSE y GMC)
        print("\n📄 Buscando transcripciones PDF base en 'AUDIO'...")
        abuse_pdf_files = find_multiple_files_with_keywords(drive_service, audio_folder_id, ["abuse"], ["application/pdf"], temp_dir)
        gmc_pdf_files = find_multiple_files_with_keywords(drive_service, audio_folder_id, ["gmc"], ["application/pdf"], temp_dir)

        if not abuse_pdf_files or not gmc_pdf_files:
            print("❌ No se encontró el PDF base 'ABUSE' o 'GMC'. Proceso detenido.")
            if worksheet: 
                update_progress_in_sheet(worksheet, row_to_process, 0, status_text="ERROR: Falta PDF ABUSE o GMC")
            return
            
        abuse_pdf_info = abuse_pdf_files[0]
        gmc_pdf_info = gmc_pdf_files[0]
        
        if worksheet: 
            update_progress_in_sheet(worksheet, row_to_process, 0.20) ### NUEVO: Progreso 20% ###

        # 4. OBTENER TRANSCRIPCIONES WS/WSS (TESTIMONIOS)
        print("\n🎧 Buscando transcripciones 'WS' o 'WSS' en 'AUDIO'...")
        ws_files_list = find_multiple_files_with_keywords(drive_service, audio_folder_id, ["ws", "wss"], ["application/pdf"], os.path.join(temp_dir, "ws_rl_pdfs"))

        # 5. OBTENER ARCHIVOS RL (REFERENCE LETTERS)
        print("\n🗂️ Buscando archivos 'RL' (Reference Letters) en 'EVIDENCIA/GMC'...")
        rl_files_list = find_multiple_files_with_keywords(
            drive_service, 
            evidence_gmc_folder_id, 
            ["rl"], 
            ["application/pdf", "image/jpeg", "image/png", "image/tiff"], 
            os.path.join(temp_dir, "rl_files")
        )
        rl_file_names = "\n".join([f"- {file['name']}" for file in rl_files_list])

        if worksheet: 
            update_progress_in_sheet(worksheet, row_to_process, 0.30) ### NUEVO: Progreso 30% ###

        # 6. OBTENER IMÁGENES DE EVIDENCIA (ABUSE y GMC)
        print("\n🖼️ Descargando imágenes de 'EVIDENCIA/ABUSE' y 'EVIDENCIA/GMC'...")
        abuse_images_list = list_and_download_images(drive_service, evidence_abuse_folder_id, os.path.join(temp_dir, "abuse_images"))
        gmc_all_images_list = list_and_download_images(drive_service, evidence_gmc_folder_id, os.path.join(temp_dir, "gmc_images"))
        
        if worksheet: 
            update_progress_in_sheet(worksheet, row_to_process, 0.40) ### NUEVO: Progreso 40% ###
        
        # --- PROCESAMIENTO INTERMEDIO DE IA ---
        
        # 7. PROCESAR WS/WSS (TESTIMONIOS)
        witness_texts = [
            process_file_with_prompt(file, PROMPT_WS_RL_TEMPLATE, model_pro, client_name) 
            for file in ws_files_list
        ]
        witness_final_content = "\n\n---\n\n".join(witness_texts)
        
        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.60) ### NUEVO: Progreso 60% ###
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15)
        
        # 9. PROCESAR GMC (PERMANENT BAR)
        pb_content = process_file_with_prompt(
            gmc_pdf_info, 
            PROMPT_PB_TEMPLATE, 
            model_pro, 
            client_name
        )
        
        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0.75) ### NUEVO: Progreso 75% ###
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15)

        # 10. GENERAR ENTREGABLE FINAL (PASO 5)
        print("\n--- PASO FINAL: Ensamblando el Entregable ---")
        
        final_prompt_text = PROMPT_PASO_5_FINAL_DELIVERABLE.replace(
            "{witness_content}", witness_final_content
        ).replace(
            "{pb_content}", str(pb_content)
        ).replace(
            "{rl_file_names}", rl_file_names 
        )
        
        try:
            chat_model_final = GenerativeModel(
                model_pro._model_name, 
                generation_config=model_pro._generation_config, 
                system_instruction=PROMPT_INSTRUCCIONES_SISTEMA
            )
        except Exception as e:
            chat_model_final = model_pro
            print(f"se uso otro modelo ya que ocurrio la siguiente exception: {e}")
        
        chat = chat_model_final.start_chat()
        
        # 10.1. Cargar contexto de ABUSO y sus imágenes
        abuse_names_list = "\n".join([f"- {img['name']}" for img in abuse_images_list])
        prompt_step_3_with_names = PROMPT_PASO_3_ABUSE_IMG.replace("[LISTA_DE_NOMBRES_DE_ARCHIVO_ADJUNTOS]", abuse_names_list)
        send_message_to_chat(chat, prompt_step_3_with_names, files_to_upload=[abuse_pdf_info] + abuse_images_list, expect_response=False)
        
        if worksheet: 
            update_progress_in_sheet(worksheet, row_to_process, 0.80) ### NUEVO: Progreso 80% ###
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15) 
        
        # 10.2. Cargar contexto de GMC y sus imágenes
        gmc_names_list = "\n".join([f"- {img['name']}" for img in gmc_all_images_list])
        prompt_step_4_with_names = PROMPT_PASO_4_GMC_IMG.replace("[LISTA_DE_NOMBRES_DE_ARCHIVO_ADJUNTOS]", gmc_names_list)
        send_message_to_chat(chat, prompt_step_4_with_names, files_to_upload=[gmc_pdf_info] + gmc_all_images_list, expect_response=False)
        
        if worksheet: 
            update_progress_in_sheet(worksheet, row_to_process, 0.85) ### NUEVO: Progreso 85% ###
        print("\n... ⏸️ Pausa de 15s para evitar límite de API ...\n")
        time.sleep(15) 
        
        # 10.3. Enviamos el prompt final con el texto ensamblado
        if worksheet: 
            update_progress_in_sheet(worksheet, row_to_process, 0.90) ### NUEVO: Progreso 90% ###
        final_deliverable_text = send_message_to_chat(
            chat,
            final_prompt_text.replace("[NOMBRE CLIENTE]", str(client_name)),
            files_to_upload=[], 
            expect_response=True
        )

        if "ERROR:" in str(final_deliverable_text):
            print(f"❌ No se pudo generar el entregable final: {final_deliverable_text}")
            if worksheet: 
                update_progress_in_sheet(worksheet, row_to_process, 0, status_text="ERROR: IA Ensamblaje")
        else:
            print("🎉 ¡Entregable final generado por la IA!")
            if worksheet:
                update_progress_in_sheet(worksheet, row_to_process, 0.95) ### NUEVO: Progreso 95% ###
            
            # 11. GUARDAR Y SUBIR ENTREGABLE
            uploaded_files = save_final_deliverable(
                drive_service,
                final_deliverable_text,
                client_name,
                client_folder_id, 
                temp_dir,
                abuse_images_list,
                gmc_all_images_list 
            )
            
            # Escribir enlaces de vuelta a la hoja
            if uploaded_files:
                # La función ahora escribe en F y G
                write_links_to_sheet(
                    gc, 
                    SHEET_URL,
                    SHEET_NAME,
                    row_to_process,
                    uploaded_files
                )
                if worksheet: 
                    update_progress_in_sheet(worksheet, row_to_process, 1.0) ### NUEVO: Progreso 100% ###
            else:
                print("⚠️ No se recibieron enlaces de archivos subidos, no se puede actualizar la hoja.")
                if worksheet: 
                    update_progress_in_sheet(worksheet, row_to_process, 0, status_text="ERROR: Subida Drive")


    except Exception as e:
        print(f"❌ Un error general ha ocurrido: {e}")
        # --- ### NUEVO: Manejo de error general ### ---
        if worksheet:
            update_progress_in_sheet(worksheet, row_to_process, 0, status_text="ERROR: Script falló")
            
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\n✅ Directorio temporal '{temp_dir}' eliminado.")

if __name__ == "__main__":
    import os
    import time # Asegúrate de que time esté importado
    row = int(os.getenv("ROW_TO_PROCESS", "117"))
    main(row)