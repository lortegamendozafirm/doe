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
