import chromadb
from typing import List

class OrganizacionRAG:
    """RAG separado por organización. Aislamiento de datos."""
    
    def __init__(self, org_id: str):
        self.org_id = org_id
        self._validar_org(org_id)
        
        # ChromaDB client (local, persiste en memoria)
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=f"{org_id}_kb",
            metadata={"org": org_id}
        )
    
    def _validar_org(self, org_id: str):
        """GUARDRAIL: org_id debe ser válido."""
        from src.config import REGLAS_NEGOCIO
        if org_id not in REGLAS_NEGOCIO:
            raise ValueError(f"Organización '{org_id}' no autorizada")
    
    def agregar_documento(self, doc_id: str, contenido: str, metadata: dict = None):
        """Agrega documento a KB de la org."""
        if metadata is None:
            metadata = {}
        
        # Asegura que org_id está en metadata (GUARDRAIL)
        metadata["org_id"] = self.org_id
        
        self.collection.add(
            ids=[doc_id],
            documents=[contenido],
            metadatas=[metadata]
        )
    
    def cargar_desde_archivo(self, ruta_archivo: str):
        """Carga todo un archivo .txt a la KB."""
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        doc_id = f"{self.org_id}_doc_{ruta_archivo.split('/')[-1]}"
        self.agregar_documento(doc_id, contenido)
    
    def consultar(self, pregunta: str, n_resultados: int = 3) -> List[str]:
        """Busca en RAG de la org. Devuelve documentos relevantes."""
        resultados = self.collection.query(
            query_texts=[pregunta],
            n_results=n_resultados
        )
        
        # Devuelve solo documentos (sin metadata)
        documentos = []
        if resultados and resultados['documents']:
            documentos = resultados['documents'][0]
        
        return documentos
    
    def obtener_contexto(self, pregunta: str) -> str:
        """Devuelve contexto como string para pasar al agente."""
        documentos = self.consultar(pregunta, n_resultados=2)
        return "\n---\n".join(documentos) if documentos else "No hay contexto disponible"