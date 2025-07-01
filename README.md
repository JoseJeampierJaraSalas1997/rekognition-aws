# 🏦 Analizador de Comprobantes Bancarios

## 📋 Descripción del Proyecto

Esta aplicación web desarrollada en **Streamlit** permite extraer información específica de comprobantes bancarios utilizando **Amazon Textract**, un servicio de AWS especializado en extracción de texto y análisis de documentos. La aplicación puede procesar imágenes de comprobantes y extraer automáticamente datos como montos, números de operación, fechas, y más información relevante.

## 🎯 Funcionalidades Principales

- ✅ Extracción automática de texto de comprobantes bancarios
- ✅ Análisis inteligente de formularios y tablas
- ✅ Reconocimiento de patrones específicos bancarios
- ✅ Exportación de datos extraídos en formato JSON
- ✅ Interfaz web intuitiva con vista previa de documentos

## 🛠️ Tecnologías Utilizadas

### Librerías Principales

- **Streamlit**: Framework para crear aplicaciones web interactivas
- **boto3**: SDK oficial de AWS para Python (interacción con servicios AWS)
- **PIL (Pillow)**: Procesamiento y manipulación de imágenes
- **pandas**: Manipulación y análisis de datos estructurados
- **re**: Expresiones regulares para extracción de patrones

### Servicios AWS

- **Amazon Textract**: Servicio de extracción de texto y análisis de documentos

## 📁 Estructura del Código

### 1. Clase `BankingReceiptAnalyzer`

**Propósito**: Gestiona la comunicación con AWS Textract para el análisis de documentos.

#### Método `__init__(self)`
```python
def __init__(self):
```
- **Función**: Constructor que inicializa la conexión con AWS Textract
- **Consumo de librería**: Utiliza `boto3.client()` para crear cliente de Textract
- **Configuración**: Lee credenciales desde `st.secrets` (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
- **Manejo de errores**: Valida credenciales y maneja excepciones de conexión

#### Método `analyze_document_with_forms(self, image_bytes)`
```python
def analyze_document_with_forms(self, image_bytes: bytes) -> Dict[str, Any]:
```
- **Función**: Análisis avanzado de documentos con reconocimiento de formularios y tablas
- **Consumo AWS**: Utiliza `textract.analyze_document()` con características:
  - `FORMS`: Detecta pares clave-valor en formularios
  - `TABLES`: Reconoce estructuras tabulares
- **Parámetros**: Recibe bytes de la imagen del documento
- **Retorno**: Diccionario con bloques de texto estructurados o mensaje de error

#### Método `extract_text_simple(self, image_bytes)`
```python
def extract_text_simple(self, image_bytes: bytes) -> Dict[str, Any]:
```
- **Función**: Extracción básica de texto línea por línea
- **Consumo AWS**: Utiliza `textract.detect_document_text()` (método más simple)
- **Procesamiento**: Filtra bloques de tipo 'LINE' para obtener texto legible
- **Uso**: Ideal para documentos con texto simple sin estructura compleja

### 2. Clase `BankingDataExtractor`

**Propósito**: Procesa el texto extraído y identifica campos específicos bancarios usando patrones.

#### Método `extract_banking_fields(text)`
```python
@staticmethod
def extract_banking_fields(text: str) -> Dict[str, str]:
```
- **Función**: Extrae información bancaria específica usando expresiones regulares
- **Consumo de librería**: Utiliza `re.search()` para patrones regex
- **Campos detectables**:
  - 💰 Importe enviado (S/ XXX.XX)
  - 🏦 Entidad destino (nombre del banco)
  - 💳 Comisión (S/ X.XX)
  - 📊 ITF (Impuesto a las Transacciones Financieras)
  - 🔢 Número de operación
  - 📝 Tipo de operación
  - 📅 Fecha y hora
  - ✅ Estado de operación

**Patrones de Búsqueda Ejemplo**:
```python
'importe_enviado': [
    r'Importe enviado\s*S/\s*(\d+\.?\d*)',
    r'S/\s*(\d+\.?\d*)',
    r'Monto\s*S/\s*(\d+\.?\d*)'
]
```

#### Método `_extract_account_numbers(text, fields)`
```python
@staticmethod
def _extract_account_numbers(text: str, fields: Dict[str, str]) -> None:
```
- **Función**: Identifica números de cuenta origen y destino
- **Patrones**: Busca formatos como "•1234", "Cuenta 123456789"
- **Lógica**: Asigna primera cuenta como origen y segunda como destino

#### Método `_extract_bank_names(text, fields)`
```python
@staticmethod
def _extract_bank_names(text: str, fields: Dict[str, str]) -> None:
```
- **Función**: Detecta nombres de bancos peruanos comunes
- **Bancos soportados**: BBVA, Plin, BCP, Interbank, Scotiabank, BanBif
- **Método**: Búsqueda case-insensitive en el texto

### 3. Función `display_extracted_banking_data(fields)`

**Propósito**: Presenta los datos extraídos en una interfaz visual organizada.

- **Consumo Streamlit**: Utiliza `st.metric()`, `st.dataframe()`, `st.columns()`
- **Funcionalidades**:
  - Métricas destacadas (importe, entidad, estado)
  - Tabla detallada con todos los campos
  - Indicadores de estado (detectado/no detectado)
  - Botón de descarga en formato JSON
- **Exportación**: Genera archivo JSON con timestamp y estadísticas de completitud

### 4. Función `process_banking_receipt(uploaded_file, analyzer)`

**Propósito**: Orquesta el proceso completo de análisis de un comprobante.

- **Consumo PIL**: Utiliza `Image.open()` para mostrar vista previa
- **Funcionalidades**:
  - Vista previa del documento subido
  - Dos métodos de análisis (Tabs):
    - Análisis avanzado con formularios
    - Extracción simple de texto
  - Procesamiento de bytes del archivo
  - Manejo de errores y estados de carga

### 5. Función `main()`

**Propósito**: Función principal que construye la interfaz de usuario completa.

- **Consumo Streamlit**: Utiliza múltiples componentes:
  - `st.title()`, `st.markdown()`: Títulos y contenido
  - `st.sidebar`: Panel lateral informativo
  - `st.file_uploader()`: Subida de archivos
  - `st.columns()`: Layout en columnas
- **Validaciones**: Verifica credenciales AWS antes de continuar
- **Tipos de archivo**: Soporta JPG, PNG, PDF

## 🔧 Configuración y Uso

### 1. Configuración de AWS

**Archivo**: `secrets.toml` (Streamlit)
```toml
[aws]
AWS_ACCESS_KEY_ID = "tu_access_key"
AWS_SECRET_ACCESS_KEY = "tu_secret_key"
AWS_DEFAULT_REGION = "us-east-1"
```

### 2. Instalación de Dependencias

```bash
pip install streamlit boto3 pillow pandas
```

### 3. Ejecución

```bash
streamlit run app.py
```

## 📊 Flujo de Trabajo

1. **Carga de Documento**: Usuario sube imagen del comprobante
2. **Procesamiento AWS**: Textract extrae texto y estructura
3. **Análisis de Patrones**: Regex identifica campos bancarios específicos
4. **Visualización**: Streamlit muestra datos extraídos
5. **Exportación**: Descarga opcional en JSON

## 🎯 Casos de Uso

- ✅ Automatización de contabilidad empresarial
- ✅ Reconciliación bancaria automatizada
- ✅ Digitalización de comprobantes físicos
- ✅ Auditorías y reportes financieros
- ✅ Integración con sistemas ERP

## ⚠️ Consideraciones Importantes

### Limitaciones de AWS Textract
- **Costo**: Servicio pagado por documento procesado
- **Calidad**: Requiere imágenes claras y bien iluminadas
- **Idioma**: Optimizado para texto en español/inglés

### Seguridad
- Credenciales AWS deben mantenerse seguras
- Los documentos se procesan temporalmente en AWS
- No se almacenan datos permanentemente

## 🚀 Mejoras Futuras

- 🔄 Procesamiento por lotes (múltiples comprobantes)
- 🤖 Machine Learning personalizado para patrones específicos
- 📱 Versión móvil optimizada
- 🔐 Autenticación de usuarios
- 📈 Dashboard de estadísticas

## 📞 Soporte

Para consultas técnicas o mejoras al código, contactar al desarrollador: [@JoseJeampierJaraSalas1997](https://github.com/JoseJeampierJaraSalas1997)

---

**Nota**: Este proyecto utiliza Amazon Textract, no Amazon Rekognition. Textract está especializado en extracción de texto y análisis de documentos, mientras que Rekognition se enfoca en reconocimiento de imágenes, caras y objetos.