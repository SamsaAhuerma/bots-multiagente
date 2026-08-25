import logging
import json
import time
from functools import wraps
from datetime import datetime
import os

# Crear directorio de logs
os.makedirs("logs", exist_ok=True)

# Configurar logger
logger = logging.getLogger("bots_multiagente")
logger.setLevel(logging.INFO)

# Handler: archivo
file_handler = logging.FileHandler("logs/app.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)

# Handler: consola (para desarrollo)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def log_evento(evento: str, org_id: str, **kwargs):
    """Logguea evento estructurado."""
    datos = {
        "timestamp": datetime.now().isoformat(),
        "evento": evento,
        "org_id": org_id,
        **kwargs
    }
    logger.info(json.dumps(datos))


def medir_latencia(func):
    """Decorador: mide latencia de una función."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        inicio = time.time()
        resultado = func(*args, **kwargs)
        latencia_ms = (time.time() - inicio) * 1000
        
        # Log automático
        log_evento(
            evento=f"{func.__name__}_ejecutado",
            org_id=kwargs.get("org_id", "unknown"),
            latencia_ms=round(latencia_ms, 2),
            funcion=func.__name__
        )
        
        return resultado
    return wrapper


def contar_tokens(texto: str) -> int:
    """Estimación rápida: ~4 caracteres = 1 token."""
    return len(texto) // 4


def log_agente(org_id: str, tipo_agente: str, tokens_input: int, tokens_output: int, latencia_ms: float):
    """Logguea ejecución de agente."""
    log_evento(
        evento="agente_ejecutado",
        org_id=org_id,
        tipo_agente=tipo_agente,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        tokens_total=tokens_input + tokens_output,
        latencia_ms=round(latencia_ms, 2)
    )


def log_routing(org_id: str, mensaje: str, tipo_detectado: str):
    """Logguea decisión de routing."""
    log_evento(
        evento="routing_decisión",
        org_id=org_id,
        tipo_detectado=tipo_detectado,
        mensaje_preview=mensaje[:50]
    )


def log_error(org_id: str, error: str, contexto: str = ""):
    """Logguea errores."""
    log_evento(
        evento="error",
        org_id=org_id,
        error=error,
        contexto=contexto
    )


def log_guardrail(org_id: str, tipo: str, detalles: str):
    """Logguea eventos de guardrails."""
    log_evento(
        evento="guardrail",
        org_id=org_id,
        tipo=tipo,
        detalles=detalles
    )


class AnalysisLogs:
    """Analiza logs para métricas."""
    
    @staticmethod
    def leer_logs(archivo: str = "logs/app.log"):
        """Lee archivo de logs."""
        eventos = []
        try:
            with open(archivo, 'r') as f:
                for linea in f:
                    try:
                        # Formato: "TIMESTAMP - {"json": "data"}"
                        partes = linea.split(" - ", 1)
                        if len(partes) == 2:
                            datos = json.loads(partes[1].strip())
                            eventos.append(datos)
                    except:
                        pass
        except FileNotFoundError:
            print(f"Archivo {archivo} no encontrado")
        
        return eventos
    
    @staticmethod
    def por_org(eventos):
        """Agrupa eventos por org_id."""
        por_org = {}
        for evento in eventos:
            org = evento.get("org_id", "unknown")
            if org not in por_org:
                por_org[org] = []
            por_org[org].append(evento)
        return por_org
    
    @staticmethod
    def metricas_por_org(eventos):
        """Calcula métricas por org."""
        por_org = AnalysisLogs.por_org(eventos)
        metricas = {}
        
        for org, eventos_org in por_org.items():
            agentes = [e for e in eventos_org if e.get("evento") == "agente_ejecutado"]
            
            if agentes:
                tokens_totales = sum(e.get("tokens_total", 0) for e in agentes)
                latencias = [e.get("latencia_ms", 0) for e in agentes]
                
                metricas[org] = {
                    "total_requests": len(agentes),
                    "tokens_totales": tokens_totales,
                    "latencia_promedio_ms": round(sum(latencias) / len(latencias), 2) if latencias else 0,
                    "latencia_max_ms": max(latencias) if latencias else 0,
                    "latencia_min_ms": min(latencias) if latencias else 0
                }
        
        return metricas
    
    @staticmethod
    def imprimir_reporte():
        """Imprime reporte de métricas."""
        eventos = AnalysisLogs.leer_logs()
        metricas = AnalysisLogs.metricas_por_org(eventos)
        
        print("\n" + "="*60)
        print("REPORTE DE OBSERVABILIDAD")
        print("="*60)
        
        for org, m in metricas.items():
            print(f"\n{org}:")
            print(f"  Requests: {m['total_requests']}")
            print(f"  Tokens totales: {m['tokens_totales']}")
            print(f"  Latencia promedio: {m['latencia_promedio_ms']}ms")
            print(f"  Latencia (min/max): {m['latencia_min_ms']}/{m['latencia_max_ms']}ms")
        
        print("\n" + "="*60)