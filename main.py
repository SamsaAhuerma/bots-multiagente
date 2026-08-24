# main.py
from fastapi import FastAPI, HTTPException
from src.router import Orquestador
from src.rag import OrganizacionRAG

app = FastAPI()

# Cargar datos en RAG al iniciar
def cargar_datos_rag():
    """Carga archivos de data/ en RAG de cada org."""
    for org_id in ["org_1", "org_2", "org_3"]:
        try:
            rag = OrganizacionRAG(org_id)
            rag.cargar_desde_archivo(f"data/{org_id}_policies.txt")
            print(f"✓ Datos cargados para {org_id}")
        except Exception as e:
            print(f"✗ Error cargando {org_id}: {e}")

cargar_datos_rag()

@app.post("/chat")
def chat(org_id: str, user_id: str, mensaje: str):
    try:
        orquestador = Orquestador()
        respuesta = orquestador.procesar(org_id, user_id, mensaje)
        return {"respuesta": respuesta, "org": org_id}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)