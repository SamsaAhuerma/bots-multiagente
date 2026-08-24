# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Credenciales
ANTHROPIC_API_KEY = os.getenv("OPENAI_API_KEY")  

# Reglas de negocio por organización
REGLAS_NEGOCIO = {
    "org_1": {
        "max_reintegro": 100000,
        "requisitos": ["DNI", "comprobante"],
        "tiempo_respuesta": "24h"
    },
    "org_2": {
        "max_reintegro": 150000,
        "requisitos": ["DNI", "comprobante", "factura"],
        "tiempo_respuesta": "48h"
    },
    "org_3": {
        "max_reintegro": 80000,
        "requisitos": ["DNI", "comprobante"],
        "tiempo_respuesta": "72h"
    }
}

# Endpoints externos (simulados)
ENDPOINTS = {
    "validate_user": "http://localhost:8000/api/validate-user",
    "check_coverage": "http://localhost:8000/api/check-coverage",
    "create_refund": "http://localhost:8000/api/create-refund"
}

# Configuración LLM
MODEL = "gpt-4o-mini"
TEMPERATURE = 0.7