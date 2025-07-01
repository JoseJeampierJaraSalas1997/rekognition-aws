import streamlit as st
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import json
from PIL import Image
import io
import base64
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import re
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Analizador de Comprobantes Bancarios",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

class BankingReceiptAnalyzer:
    """Clase para analizar comprobantes bancarios usando AWS Textract"""
    
    def __init__(self):
        """Inicializa el cliente de AWS Textract"""
        try:
            # Cargar credenciales desde secrets.toml
            aws_access_key = st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
            aws_secret_key = st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]
            aws_region = st.secrets["aws"]["AWS_DEFAULT_REGION"]
            
            # Inicializar cliente AWS Textract
            self.textract = boto3.client(
                'textract',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
            self.credentials_valid = True
            
        except KeyError as e:
            st.error(f"❌ Credencial AWS faltante: {e}")
            self.credentials_valid = False
        except Exception as e:
            st.error(f"❌ Error al inicializar AWS: {str(e)}")
            self.credentials_valid = False
    
    def analyze_document_with_forms(self, image_bytes: bytes) -> Dict[str, Any]:
        """Analiza un documento usando Textract con análisis de formularios"""
        try:
            response = self.textract.analyze_document(
                Document={'Bytes': image_bytes},
                FeatureTypes=['FORMS', 'TABLES']
            )
            return {"success": True, "blocks": response['Blocks']}
        except ClientError as e:
            return {"success": False, "error": f"Error de AWS: {e.response['Error']['Message']}"}
        except Exception as e:
            return {"success": False, "error": f"Error inesperado: {str(e)}"}
    
    def extract_text_simple(self, image_bytes: bytes) -> Dict[str, Any]:
        """Extrae texto simple del documento"""
        try:
            response = self.textract.detect_document_text(
                Document={'Bytes': image_bytes}
            )
            
            # Extraer texto línea por línea
            text_blocks = []
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block['Text'])
            
            return {
                "success": True, 
                "text": '\n'.join(text_blocks),
                "blocks": response['Blocks']
            }
        except ClientError as e:
            return {"success": False, "error": f"Error de AWS: {e.response['Error']['Message']}"}
        except Exception as e:
            return {"success": False, "error": f"Error inesperado: {str(e)}"}

class BankingDataExtractor:
    """Clase para extraer información específica de comprobantes bancarios"""
    
    @staticmethod
    def extract_banking_fields(text: str) -> Dict[str, str]:
        """
        Extrae campos específicos del texto del comprobante bancario
        usando expresiones regulares y patrones
        """
        fields = {
            'importe_enviado': '',
            'entidad_destino': '',
            'comision': '',
            'itf': '',
            'numero_operacion': '',
            'tipo_operacion': '',
            'fecha': '',
            'cuenta_origen': '',
            'cuenta_destino': '',
            'estado_operacion': ''
        }
        
        # Patrones de búsqueda
        patterns = {
            'importe_enviado': [
                r'Importe enviado\s*S/\s*(\d+\.?\d*)',
                r'S/\s*(\d+\.?\d*)',
                r'Monto\s*S/\s*(\d+\.?\d*)',
                r'Importe\s*S/\s*(\d+\.?\d*)'
            ],
            'entidad_destino': [
                r'Entidad destino\s*([^\n]+)',
                r'Destino\s*([^\n]+)',
                r'Banco destino\s*([^\n]+)'
            ],
            'comision': [
                r'Comisión\s*S/\s*(\d+\.?\d*)',
                r'Comision\s*S/\s*(\d+\.?\d*)'
            ],
            'itf': [
                r'ITF\s*S/\s*(\d+\.?\d*)'
            ],
            'numero_operacion': [
                r'Número de operación\s*(\d+)',
                r'Numero de operacion\s*(\d+)',
                r'Operación\s*(\d+)',
                r'Nro\.\s*operación\s*(\d+)'
            ],
            'tipo_operacion': [
                r'Tipo de operación\s*([^\n]+)',
                r'Tipo de operacion\s*([^\n]+)',
                r'Operación\s*([^\n]+)'
            ],
            'fecha': [
                r'(\d{1,2}\s+\w+\s+\d{4},?\s+\d{1,2}:\d{2}\s*h?)',
                r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})',
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
            ],
            'estado_operacion': [
                r'(Operación exitosa)',
                r'(Operacion exitosa)',
                r'(Exitosa)',
                r'(Completada)',
                r'(Aprobada)'
            ]
        }
        
        # Buscar cada patrón en el texto
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    fields[field] = match.group(1).strip()
                    break
        
        # Búsquedas adicionales específicas
        BankingDataExtractor._extract_account_numbers(text, fields)
        BankingDataExtractor._extract_bank_names(text, fields)
        
        return fields
    
    @staticmethod
    def _extract_account_numbers(text: str, fields: Dict[str, str]) -> None:
        """Extrae números de cuenta del texto"""
        # Buscar patrones de cuentas
        account_patterns = [
            r'•(\d{4})',
            r'Cuenta\s*(\d+)',
            r'Cta\.\s*(\d+)'
        ]
        
        accounts = []
        for pattern in account_patterns:
            matches = re.findall(pattern, text)
            accounts.extend(matches)
        
        if len(accounts) >= 2:
            fields['cuenta_origen'] = accounts[0]
            fields['cuenta_destino'] = accounts[1]
        elif len(accounts) == 1:
            fields['cuenta_origen'] = accounts[0]
    
    @staticmethod
    def _extract_bank_names(text: str, fields: Dict[str, str]) -> None:
        """Extrae nombres de bancos del texto"""
        bank_names = ['BBVA', 'Plin', 'BCP', 'Interbank', 'Scotiabank', 'BanBif']
        
        for bank in bank_names:
            if bank.lower() in text.lower():
                if not fields['entidad_destino']:
                    fields['entidad_destino'] = bank
                break

def display_extracted_banking_data(fields: Dict[str, str]) -> None:
    """Muestra los datos extraídos del comprobante bancario de forma estructurada"""
    st.subheader("🏦 Información Extraída del Comprobante")
    
    # Crear métricas principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if fields['importe_enviado']:
            st.metric(
                label="💰 Importe Enviado",
                value=f"S/ {fields['importe_enviado']}" if fields['importe_enviado'] else "No detectado"
            )
    
    with col2:
        if fields['entidad_destino']:
            st.metric(
                label="🏦 Entidad Destino",
                value=fields['entidad_destino'] or "No detectado"
            )
    
    with col3:
        if fields['estado_operacion']:
            st.metric(
                label="✅ Estado",
                value=fields['estado_operacion'] or "No detectado"
            )
        st.subheader("📋 Detalle Completo")
    
    data_rows = []
    field_labels = {
        'importe_enviado': '💰 Importe Enviado',
        'entidad_destino': '🏦 Entidad Destino',
        'comision': '💳 Comisión',
        'itf': '📊 ITF',
        'numero_operacion': '🔢 Número de Operación',
        'tipo_operacion': '📝 Tipo de Operación',
        'fecha': '📅 Fecha y Hora',
        'cuenta_origen': '📤 Cuenta Origen',
        'cuenta_destino': '📥 Cuenta Destino',
        'estado_operacion': '✅ Estado Operación'
    }
    
    for field, label in field_labels.items():
        value = fields.get(field, '')
        status = "✅ Detectado" if value else "❌ No detectado"
        data_rows.append({
            'Campo': label,
            'Valor': value or 'No encontrado',
            'Estado': status
        })
    
    df = pd.DataFrame(data_rows)
    
    # Mostrar tabla con colores
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Campo": st.column_config.TextColumn("Campo", width="medium"),
            "Valor": st.column_config.TextColumn("Valor Extraído", width="large"),
            "Estado": st.column_config.TextColumn("Estado", width="small")
        }
    )
    
    if any(fields.values()):
        # Crear JSON con los datos extraídos
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'campos_extraidos': fields,
            'resumen': {
                'total_campos': len(field_labels),
                'campos_detectados': len([v for v in fields.values() if v]),
                'porcentaje_completitud': len([v for v in fields.values() if v]) / len(field_labels) * 100
            }
        }
        
        st.download_button(
            label="📥 Descargar Datos Extraídos (JSON)",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name=f"comprobante_bancario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

def process_banking_receipt(uploaded_file, analyzer: BankingReceiptAnalyzer) -> None:
    """Procesa un comprobante bancario completo"""
    try:
        # Leer bytes del archivo
        image_bytes = uploaded_file.read()
        
        # Mostrar vista previa
        st.subheader("🖼️ Vista Previa del Comprobante")
        image = Image.open(io.BytesIO(image_bytes))
        st.image(image, caption=f"Comprobante: {uploaded_file.name}", width=300)
        
        # Crear tabs para diferentes métodos de análisis
        tab1, tab2 = st.tabs(["📄 Análisis con Textract", "🔍 Extracción Simple"])
        
        # Tab 1: Análisis con Textract Forms
        with tab1:
            st.info("📋 Usando Amazon Textract con análisis de formularios")
            if st.button("Analizar con Textract", key="textract_btn", type="primary"):
                with st.spinner("Analizando estructura del documento..."):
                    result = analyzer.analyze_document_with_forms(image_bytes)
                
                if result["success"]:
                    st.success("✅ Análisis completado")
                    
                    # Extraer texto de los bloques
                    text_blocks = []
                    for block in result["blocks"]:
                        if block['BlockType'] == 'LINE':
                            text_blocks.append(block['Text'])
                    
                    full_text = '\n'.join(text_blocks)
                    
                    # Extraer campos bancarios
                    banking_fields = BankingDataExtractor.extract_banking_fields(full_text)
                    display_extracted_banking_data(banking_fields)
                    
                    # Mostrar texto completo en expandible
                    with st.expander("Ver texto completo extraído"):
                        st.text_area("Texto detectado:", full_text, height=300)
                else:
                    st.error(f"❌ Error: {result['error']}")
        
        # Tab 2: Extracción simple
        with tab2:
            st.info("🔍 Extracción simple de texto y análisis con patrones")
            if st.button("Extracción Simple", key="simple_btn"):
                with st.spinner("Extrayendo texto..."):
                    result = analyzer.extract_text_simple(image_bytes)
                
                if result["success"]:
                    st.success("✅ Extracción completada")
                    
                    # Extraer campos bancarios
                    banking_fields = BankingDataExtractor.extract_banking_fields(result["text"])
                    display_extracted_banking_data(banking_fields)
                    
                    # Mostrar texto original
                    with st.expander("Ver texto extraído"):
                        st.text_area("Texto:", result["text"], height=200)
                else:
                    st.error(f"❌ Error: {result['error']}")
                    
    except Exception as e:
        st.error(f"❌ Error al procesar comprobante: {str(e)}")

def main():
    """Función principal de la aplicación"""
    
    # Título y descripción
    st.title("🏦 Analizador de Comprobantes Bancarios")
    st.markdown("""
    Esta aplicación especializada extrae información específica de comprobantes bancarios usando:
    - 📄 **Amazon Textract** con análisis de formularios
    - 🔍 **Patrones de reconocimiento** específicos para datos bancarios
    """)
    
    # Inicializar analizador
    analyzer = BankingReceiptAnalyzer()
    
    if not analyzer.credentials_valid:
        st.error("❌ No se pudieron cargar las credenciales de AWS")
        st.stop()
    
    # Sidebar con información
    with st.sidebar:
        st.header("🎯 Campos Detectables")
        st.markdown("""
        **Información Financiera:**
        - 💰 Importe enviado
        - 💳 Comisión
        - 📊 ITF
        
        **Datos de Operación:**
        - 🔢 Número de operación
        - 📝 Tipo de operación  
        - 📅 Fecha y hora
        - ✅ Estado de operación
        
        **Información de Cuentas:**
        - 🏦 Entidad destino
        - 📤 Cuenta origen
        - 📥 Cuenta destino
        """)
    
    # Subida de archivos
    st.header("📤 Subir Comprobante Bancario")
    uploaded_file = st.file_uploader(
        "Selecciona una imagen del comprobante bancario:",
        type=['jpg', 'jpeg', 'png', 'pdf'],
        help="Sube una imagen clara del comprobante para extraer la información automáticamente"
    )
    
    if uploaded_file is not None:
        # Procesar archivo
        if uploaded_file.type.startswith('image/'):
            process_banking_receipt(uploaded_file, analyzer)
        elif uploaded_file.type == 'application/pdf':
            st.warning("⚠️ Los PDFs se procesarán como imágenes. Para mejores resultados, usa imágenes JPG/PNG.")
            process_banking_receipt(uploaded_file, analyzer)
        else:
            st.error("❌ Formato no soportado. Usa JPG, PNG o PDF.")
    
    # Información adicional
    st.markdown("---")
    st.header("📚 Información Adicional")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏦 Bancos Soportados")
        st.markdown("""
        - BBVA
        - Plin
        - BCP
        - Interbank
        - Scotiabank
        - BanBif
        - Y otros...
        """)
    
    with col2:
        st.subheader("📋 Tipos de Operación")
        st.markdown("""
        - Envío a contactos
        - Transferencias
        - Pagos de servicios
        - Recargas
        - Y otros...
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🏦 Analizador de Comprobantes Bancarios - Desarrollado con Streamlit y AWS por <a href="https://github.com/JoseJeampierJaraSalas1997" target="_blank">@JoseJeampierJaraSalas1997</a></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()