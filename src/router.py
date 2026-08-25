from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
from src.config import REGLAS_NEGOCIO
from src.agents import BotReintegro, BotAsistencia
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import time
from src.observability import log_evento, log_routing, log_error, log_guardrail

class Estado(TypedDict):
    """Estado que viaja entre nodos de LangGraph."""
    org_id: str
    user_id: str
    mensaje: str
    tipo_solicitud: str | None
    respuesta: str

class Orquestador:
    """Orquestador central. Rutea según org_id + tipo solicitud."""
    
    def __init__(self):
        self.workflow = self._construir_grafo()
        self.app = self.workflow.compile()
    
    def _construir_grafo(self):
        """Construye el grafo LangGraph."""
        workflow = StateGraph(Estado)
        
        # Nodos
        workflow.add_node("validar_org", self._nodo_validar_org)
        workflow.add_node("detectar_tipo", self._nodo_detectar_tipo)
        workflow.add_node("procesar_reintegro", self._nodo_procesar_reintegro)
        workflow.add_node("procesar_asistencia", self._nodo_procesar_asistencia)
        
        # Edges
        workflow.set_entry_point("validar_org")
        workflow.add_edge("validar_org", "detectar_tipo")
        
        # Condicional: según tipo, va a agente
        workflow.add_conditional_edges(
            "detectar_tipo",
            self._decidir_agente,
            {
                "reintegro": "procesar_reintegro",
                "asistencia": "procesar_asistencia"
            }
        )
        
        workflow.add_edge("procesar_reintegro", END)
        workflow.add_edge("procesar_asistencia", END)
        
        return workflow
    
    def _nodo_validar_org(self, state: Estado) -> Estado:
        """GUARDRAIL: valida que org_id existe."""
        org_id = state["org_id"]
        
        if org_id not in REGLAS_NEGOCIO:
            log_guardrail(org_id, "org_rechazada", f"Organización {org_id} no autorizada")
            return {
                **state,
                "respuesta": f"Error: Organización '{org_id}' no autorizada"
            }
        
        log_evento("org_validada", org_id)
        return state
    
    def _nodo_detectar_tipo(self, state: Estado) -> Estado:
        """Detecta tipo de solicitud: reintegro o asistencia."""
        mensaje = state["mensaje"].lower()
        
        if any(palabra in mensaje for palabra in ["reintegro", "devolver", "reembolso"]):
            tipo = "reintegro"
        elif any(palabra in mensaje for palabra in ["cobertura", "qué cubre", "asistencia", "ayuda"]):
            tipo = "asistencia"
        else:
            tipo = "asistencia"  # Default
        
        log_routing(state["org_id"], state["mensaje"], tipo)
        return {**state, "tipo_solicitud": tipo}
    
    def _nodo_procesar_reintegro(self, state: Estado) -> Estado:
        """Ejecuta BotReintegro."""
        try:
            agente = BotReintegro(state["org_id"])
            respuesta = agente.procesar(state["user_id"], state["mensaje"])
            return {**state, "respuesta": respuesta}
        except ValueError as e:
            return {**state, "respuesta": f"Error: {str(e)}"}
    
    def _nodo_procesar_asistencia(self, state: Estado) -> Estado:
        """Ejecuta BotAsistencia."""
        try:
            agente = BotAsistencia(state["org_id"])
            respuesta = agente.procesar(state["user_id"], state["mensaje"])
            return {**state, "respuesta": respuesta}
        except ValueError as e:
            return {**state, "respuesta": f"Error: {str(e)}"}
    
    def _decidir_agente(self, state: Estado) -> str:
        """Decide cuál agente usar."""
        return state["tipo_solicitud"]
    
    def procesar(self, org_id: str, user_id: str, mensaje: str) -> str:
        """API pública: procesa un mensaje y devuelve respuesta."""
        
        inicio = time.time()
        
        estado_inicial = {
            "org_id": org_id,
            "user_id": user_id,
            "mensaje": mensaje,
            "tipo_solicitud": None,
            "respuesta": ""
        }
        
        try:
            resultado = self.app.invoke(estado_inicial)
            latencia_ms = (time.time() - inicio) * 1000
            
            log_evento(
                "orquestador_completado",
                org_id,
                user_id=user_id,
                latencia_ms=round(latencia_ms, 2)
            )
            
            return resultado["respuesta"]
        except Exception as e:
            log_error(org_id, str(e), f"user_id={user_id}")
            raise