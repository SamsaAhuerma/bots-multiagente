# Arquitectura - Decisiones de Diseño

## Flujo Completo: De Usuario a Respuesta

```
┌─────────────────────────────────────────────────────────────┐
│ CAPA EXTERNA: Proveedor del Canal                           │
│ (Meta/WhatsApp, Telegram, o cualquier SaaS acorde)         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─ Identifica: phone = +541234567890
                     ├─ Busca en BD: phone → user_id
                     ├─ Si no existe: pregunta DNI → guarda
                     │
┌────────────────────▼────────────────────────────────────────┐
│ CAPA GATEWAY: Backend / Botmaker / Middleware            │
│ (Enriquece el mensaje con contexto)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─ Extrae: org_id (del canal)
                     ├─ Extrae: user_id (de BD)
                     ├─ Extrae: mensaje (del usuario)
                     │
                     │ POST /chat
                     │ {
                     │   "org_id": "org_1",
                     │   "user_id": "user_123",
                     │   "mensaje": "¿Quiero reintegro?"
                     │ }
                     │
┌────────────────────▼────────────────────────────────────────┐
│ ESTE REPO: Sistema Multiagente (Bots Inteligentes)         │
│ (Ya no se preocupa por identificación)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─ Orquestador: "¿Reintegro?"
                     ├─ Agente: Procesa con contexto de org_1
                     ├─ RAG: Consulta org_1_policies.txt
                     ├─ State Machine: Crea pedido
                     │
┌────────────────────▼────────────────────────────────────────┐
│ RESPUESTA AL USUARIO                                        │
│ "Tu solicitud #REF-00001 fue creada. Operador revisará"   │
└─────────────────────────────────────────────────────────────┘
```

---

## Overview

```
Múltiples bots (2 a N) con procesos similares
       ↓
   Orquestador (LangGraph)
   - Identifica org_id
   - Detecta tipo solicitud
   - Rutea a agente correcto
       ↓
Agentes especializados (LangChain)
   - BotReintegro
   - BotAsistencia
   - BotReclamos (arquitectura lista, sin implementación)
       ↓
   RAG (ChromaDB)
   - org_1_kb, org_2_kb, org_3_kb
   - Búsqueda semántica de coberturas/límites
       ↓
   State Machine + BD
   - Gestiona ciclo de vida (CREATED → PENDING_REVIEW → APPROVED)
   - MVP: memoria. Producción: conecta a backend real
       ↓
   Herramientas (MCP Tools)
   - crear_refund, get_refund_status, get_refunds_usuario
   - Llaman a endpoints reales (ai-gateway, backend, etc)
```

---

## 1. Orquestación (LangGraph)

### ¿Por qué LangGraph y no if/elif?

**Decisión:** StateGraph con nodos explícitos

**Nodos:**
```
validar_org -> detectar_tipo -> [procesar_reintegro | procesar_asistencia | procesar_reclamo]
```

**Razones:**

1. **Flujo visual:** Nodos + edges = fácil debuggear. "¿Dónde falló?" → "En nodo X"
2. **Guardrails centralizados:** Valido org_id UNA VEZ antes de ejecutar. Sin validación repetida.
3. **Escalable:** Agregar nodo nuevo = `workflow.add_node()`. Sin modificar lógica existente.
4. **Testeable:** Cada nodo es independiente. Mockeo inputs/outputs fácil.

**Alternativa rechazada:** if/elif/else

```python
# Manual
if org_id not in REGLAS:
    return error
if tipo == "reintegro":
    # Valido org_id de nuevo (repetición)
    agente = BotReintegro(org_id)
    if agente.org_id != org_id:  # ¿Otra validación?
        ...
```

**Problemas:**
- Validación esparcida (la hago en orquestador + agente)
- Difícil de mantener (cada cambio es en la función principal)
- No escalable (N tipos = N ramas)

---

## 2. Agentes Especializados (LangChain)

### ¿Por qué multi-agent en lugar de 1 genérico?

**Decisión:** 3 agentes (Reintegro, Asistencia, Reclamos) + clase base reutilizable

```python
class BotBase:
    """Clase base: lógica común"""
    def __init__(self, org_id):
        self._validar_org(org_id)
        self.config = REGLAS_NEGOCIO[org_id]
        self.rag = OrganizacionRAG(org_id)

class BotReintegro(BotBase):
    """Especialización: solo lógica de reintegro"""
    def procesar(self, user_id, solicitud):
        # Prompt específico para reintegro
        # Consulta RAG ("¿Qué cubre org_1?")
        # Invoca herramientas (crear_refund)
```

**Razones:**

1. **Especialización:** Cada agente es experto. Prompt corto = menos tokens = más barato.
   - BotReintegro entiende límites, validaciones, aprobaciones
   - BotAsistencia entiende pólizas, coberturas
   - No compite contexto irrelevante

2. **Isolation:** Bug en reintegro no afecta asistencia.

3. **Testeable:** Pruebo BotReintegro sin tocar BotAsistencia.

4. **Mantenible:** Cambio prompt de reintegro sin riesgo.

**Alternativa rechazada:** 1 agente genérico

```python
# Monolítico
class BotGenerico:
    def procesar(self, solicitud):
        # Prompt gigante:
        """Eres un bot para reintegros, asistencias, reclamos...
        Si el usuario pregunta sobre reintegros, haz X
        Si pregunta sobre asistencias, haz Y
        Si pregunta sobre reclamos, haz Z
        ... etc"""
```

**Problemas:**
- Prompt gigante (2000+ tokens en contexto antes de procesar)
- Si falla reintegro, complica asistencia
- Difícil debuggear ("¿por qué falló?")
- Más caro (más tokens por consulta)

**Trade-off:** Código repetido mitigado con herencia (`BotBase`).

---

## Riesgos Mitigados con Multi-Agent

**Bot genérico** = prompt gigante con "si reintegro haz X, si asistencia haz Y, si reclamo haz Z"

**Problemas:**
- LLM confunde contextos (usuario pregunta "¿aire acondicionado para reintegro?" -> puede mezclar dominios)
- Bug en validación de reintegro afecta lógica de asistencia
- Prompt muy largo = más caro + más lugar para errar
- Inyección de prompt más fácil (usuario escapa a otro dominio)

**Bot especializado** = prompt acotado, solo su dominio

- BotReintegro: límites, validaciones, aprobaciones. Nada más.
- BotAsistencia: pólizas, coberturas. Nada más.
- Menos contexto = menos errores
- Cambio en reintegro no toca asistencia
- Validaciones específicas por dominio

**No es que "menos alucinaciones" automáticamente.** Es que con scope acotado, hay menos oportunidad de fallar fuera del dominio.

---

## 3. RAG - Recuperación de Datos (ChromaDB)

### ¿Por qué RAG y no hardcodear en config.py?

**Decisión:** RAG separado por org + búsqueda semántica

```
data/
├── org_1_policies.txt  (coberturas, límites)
├── org_2_policies.txt
└── org_3_policies.txt

ChromaDB indexa cada archivo.
Agente pregunta: "¿Aire acondicionado qué cubre?"
-> ChromaDB busca semánticamente
-> Devuelve párrafo relevante
```

**Razones:**

1. **Datos grandes sin explotar:** 3 orgs × 5 productos × 20 coberturas = mucho para config.py
2. **Cambios sin deploy:** se actualiza PDF -> ChromaDB re-indexa. Sin git push.
3. **Búsqueda semántica:** Usuario pregunta "¿aire?" -> encuentra "aire acondicionado" en "clima"
4. **Escalabilidad:** Agregar org_4 = crear org_4_policies.txt

**Alternativa rechazada:** Hardcodear en config.py

```python
# Malo
REGLAS_NEGOCIO = {
    "org_1": {
        "coberturas": ["aire", "plomería", "electricidad"],
        "límites": {
            "aire": 50000,
            "plomería": 30000
        }
        # ... crece exponencialmente
    }
}
```

**Problemas:**
- Cambio de cobertura = git commit + deploy
- Struct rígido (si agregan nueva categoría, modifico schema)
- Datos cruzados (aire vs aire acondicionado -> no encuentra)

### B. Tool que lee archivos (sin indexación)

```python
@tool
def leer_cobertura(org_id: str, pregunta: str):
    with open(f"data/{org_id}_policies.txt") as f:
        contenido = f.read()  # Lee TODO el archivo
    return contenido  # Devuelve 10k palabras
```

**Problemas:**
- **Cada pregunta = leer archivo completo** (lento)
- **Todo el contenido al LLM** (muchos tokens innecesarios)
  - Usuario: "¿Aire?"
  - LLM recibe: 20 págs de coberturas de org_1 (desperdicio)
- **LLM filtra manualmente** (menos preciso)
  - "En esta montaña de texto, busca aire"
  - Vs RAG: "Índice + búsqueda + 1 párrafo relevante"
- **Sin búsqueda semántica:** Si usuario dice "clima" y el doc dice "aire acondicionado" → no conecta

**Comparativa:**

| Criterio | RAG | Tool | Config.py |
|----------|-----|------|-----------|
| Búsqueda semántica | Sí | No | No |
| Tokens por pregunta | 100 (solo relevante) | 10000 (todo) | 50 (hardcoded) |
| Cambios sin deploy | Sí | Redeploy archivo | Git push |
| Escalable (100+ orgs) | Sí | Lento | No |

**Trade-off:** ChromaDB en memoria (MVP). Producción -> Pinecone/Weaviate (escalable).

---

## 4. State Machine - Gestión de Ciclo de Vida

### ¿Por qué State Machine + BD?

**Decisión:** Máquina de estados con transiciones validadas + BD en memoria (MVP)

```python
CREATED -> PENDING_REVIEW -> [APPROVED | REJECTED] -> COMPLETED
          (operador)            (usuario espera)     (resuelto)

Transiciones válidas definidas. No puedo ir de COMPLETED a nada.
```

**Razones:**

1. **Contexto multi-turn:** Usuario crea pedido, se va, vuelve mañana
   - Consulta: "¿Qué pasó con mi pedido REF-00001?"
   - BD devuelve: estado actual + historial

2. **Operador sabe qué hacer:** Ve cola de pedidos en PENDING_REVIEW. Sabe actuar.

3. **Audit trail:** Cada cambio de estado se logguea. "¿Quién aprobó? ¿Cuándo?"

4. **Integración con backend:** Estado real vive en backend. Bot consulta vía herramientas.

**Alternativa rechazada:** Sin persistencia

```python
# Single-turn
usuario: "Quiero reintegro"
bot: "Creando pedido REF-00001"
bot: [end of conversation]

Usuario vuelve en 3 días: "¿Qué pasó?"
bot: "No tengo contexto" 
```

**MVP vs Producción:**
- **MVP:** BD en memoria. Suficiente para demostración.
- **Producción:** Estado vive en backend (ai-gateway, PostgreSQL, etc). Bot consulta vía `get_refund_status()` POST /api/refunds/REF-00001

---

## 5. Herramientas (MCP Tools)

### ¿Por qué MCP Tools?

**Decisión:** Función anotada con `@tool` que agente invoca automáticamente

```python
@tool
def crear_refund(org_id, user_id, monto, motivo):
    """Crea solicitud de reintegro"""
    # Validaciones
    # Llamada a backend
    # Devuelve resultado

# Agente ve: "Tengo herramienta 'crear_refund'. ¿La uso aquí?"
# Invoca automáticamente
```

**Razones:**

1. **Agente decide cuándo usar:** No hardcodeo "siempre crear pedido". Agente lo decide.
2. **Reutilizable:** Herramienta se usa en múltiples agentes/contextos.
3. **Extensible:** Agregar herramienta = agregar `@tool`. Agente la descubre solo.

**Integración con backend:**
- MVP: Mock (validaciones básicas, BD en memoria)
- Producción: `crear_refund` hace `POST /api/refunds` a backend real

---

## 6. Observabilidad (Logging)

### ¿Por qué logging centralizado?

**Decisión:** Logs JSON -> archivo. Análisis posterior.

```json
{"timestamp": "2024-01-15T10:23:45", "evento": "pedido_creado", "org_id": "org_1", "pedido_id": "REF-00001"}
{"timestamp": "2024-01-15T10:24:12", "evento": "agente_ejecutado", "org_id": "org_1", "latencia_ms": 1234, "tokens": 142}
```

**Razones:**

1. **Debug:** ¿Cuál fue el último evento antes de fallar?
2. **Métricas:** Latencia promedio por org. Tokens gastados. Errores frecuentes.
3. **Audit:** ¿Quién creó el pedido? ¿Cuándo?

**Alternativa rechazada:** Sin logs

- No sé qué falló
- No puedo debuggear en producción
- Sin visibilidad de performance

**MVP:** Archivo local. **Producción:** Datadog/LangSmith

---

## Trade-offs y Decisiones Pendientes

### 1. Botmaker 3.0 vs LangChain Puro

| Criterio | Botmaker 3.0 | LangChain |
|----------|--------------|-----------|
| Setup | Rápido (UI visual) | Manual (código) |
| Escalabilidad | Limitada (vendor) | Total (control) |
| HITL | Nativo | Manual |
| Costo | Tokens caros | Depende LLM |
| Control | Bajo | Total |

**Decisión actual:** LangChain POC. Botmaker 3.0 para validar arquitectura después.

### 2. ChromaDB vs Pinecone vs Weaviate

| Criterio | ChromaDB | Pinecone | Weaviate |
|----------|----------|----------|----------|
| Costo | $0 | $$ (SaaS) | $ (self-hosted) |
| Escalabilidad | Limitada | Total | Alta |
| Setup | 5 min | 15 min | 1 hora |

**Decisión actual:** ChromaDB (MVP). Migrar a Pinecone si escala.

### 3. BD en Memoria vs PostgreSQL

**MVP:** En memoria (demo rápida)
**Producción:** PostgreSQL (datos reales)

---

## Limitaciones Conocidas

1. **ChromaDB local:** Sin escalabilidad. 100+ orgs → performance cae.
2. **Estado en agente:** Si agent se reinicia, pierde contexto. (Mitigado con logging + recuperación)
3. **OpenAI fijo:** Cambiar LLM requiere actualizar config.
4. **Chatwoot mock:** No es integración real. Faltan webhooks bidireccionales.
5. **Sin transacciones:** Si falla entre "crear pedido" y "notificar", puede haber inconsistencia.

---

## Cómo Escala de 2 a 20 Bots

```
Hoy (N=2):
├── org_1
└── org_2

Mañana (N=5):
├── org_1
├── org_2
├── org_3
├── org_4
└── org_5

Sin cambiar:
- router.py
- agents.py
- state_machine.py

Cambio solo:
- config.py (agregar org)
- data/org_N_policies.txt (agregar archivo)
```

---

## Próximos Pasos

1. **Tests E2E:** Flujos multi-turn complejos (usuario crea → consulta → operador aprueba)
2. **Integración real:** Conectar ai-gateway + PostgreSQL
3. **Chatwoot real:** Webhooks bidireccionales
4. **Performance:** Benchmarks con 100+ orgs
5. **Observabilidad profesional:** Datadog/LangSmith en lugar de logs locales