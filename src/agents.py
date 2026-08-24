from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from src.config import REGLAS_NEGOCIO, MODEL, TEMPERATURE, ANTHROPIC_API_KEY
from src.rag import OrganizacionRAG
from langchain_openai import ChatOpenAI

class BotReintegro:
    def __init__(self, org_id: str):
        self.org_id = org_id
        self._validar_org(org_id)
        
        self.config = REGLAS_NEGOCIO[org_id]
        self.llm = ChatOpenAI(
            model=MODEL,
            temperature=TEMPERATURE,
            api_key=ANTHROPIC_API_KEY  # va a leer OPENAI_API_KEY
        )
        self.rag = OrganizacionRAG(org_id)
    
    def _validar_org(self, org_id: str):
        """GUARDRAIL: org_id debe existir."""
        if org_id not in REGLAS_NEGOCIO:
            raise ValueError(f"Organización '{org_id}' no autorizada para reintegro")
    
    def procesar(self, user_id: str, solicitud: str) -> str:
        """Procesa solicitud de reintegro."""
        
        # Obtiene contexto de RAG de ESTA org
        contexto_rag = self.rag.obtener_contexto(solicitud)
        
        prompt = ChatPromptTemplate.from_template("""
Eres un asistente de reintegros para {org}.

LÍMITES Y REGLAS:
- Monto máximo: ${max_reintegro}
- Requisitos: {requisitos}
- Tiempo de respuesta: {tiempo}

CONTEXTO DE LA ORGANIZACIÓN:
{contexto}

Solicitud del usuario:
{solicitud}

Responde de forma clara y profesional. Si el reintegro es válido, apruébalo. 
Si no cumple requisitos, explica por qué y qué le falta.
""")
        
        chain = prompt | self.llm
        
        respuesta = chain.invoke({
            "org": self.org_id,
            "max_reintegro": self.config["max_reintegro"],
            "requisitos": ", ".join(self.config["requisitos"]),
            "tiempo": self.config["tiempo_respuesta"],
            "contexto": contexto_rag,
            "solicitud": solicitud
        })
        
        return respuesta.content


class BotAsistencia:
    """Agente especializado en asistencia. Aislado por org_id."""
    
    def __init__(self, org_id: str):
        self.org_id = org_id
        self._validar_org(org_id)  # GUARDRAIL
        
        self.config = REGLAS_NEGOCIO[org_id]
        self.llm = ChatOpenAI(
            model=MODEL,
            temperature=TEMPERATURE,
            api_key=ANTHROPIC_API_KEY
        )
        self.rag = OrganizacionRAG(org_id)
    
    def _validar_org(self, org_id: str):
        """GUARDRAIL: org_id debe existir."""
        if org_id not in REGLAS_NEGOCIO:
            raise ValueError(f"Organización '{org_id}' no autorizada para asistencia")
    
    def procesar(self, user_id: str, solicitud: str) -> str:
        """Procesa solicitud de asistencia."""
        
        contexto_rag = self.rag.obtener_contexto(solicitud)
        
        prompt = ChatPromptTemplate.from_template("""
Eres un asistente de soporte para {org}.

CONTEXTO DE LA ORGANIZACIÓN:
{contexto}

Pregunta del usuario:
{solicitud}

Responde de forma amable y clara. Proporciona información sobre coberturas y servicios disponibles.
""")
        
        chain = prompt | self.llm
        
        respuesta = chain.invoke({
            "org": self.org_id,
            "contexto": contexto_rag,
            "solicitud": solicitud
        })
        
        return respuesta.content