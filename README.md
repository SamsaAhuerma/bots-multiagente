# Bots Multiagente - POC

MVP de sistema multi-tenant con agentes especializados de IA, orquestación automática y observabilidad. 

**Estado:** POC funcional | **Objetivo:** Validar arquitectura antes de escalar a producción.

---

## ¿Qué es esto?

Es un experimento arquitectónico. Tengo múltiples bots conversacionales que manejan procesos similares (reintegros, asistencia, reclamos) pero para distintas organizaciones con reglas de negocio diferentes. 

La pregunta fue: **¿Puedo diseñar una arquitectura que soporte N bots de forma escalable, mantenible y con mejor UX?**

La respuesta: **sí, pero requiere cambiar de paradigma (árboles → agentes + orquestación).**

---

## El Problema Original

**El problema de la arqui infelxible**:

- **Árboles de decisión:** Cada nueva regla = extender rama, crece exponencialmente!
- **No escalable:** Agregar organización = crear bot nuevo + mantener árbol completo
- **Sin contexto:** Usuario vuelve días después, bot no recuerda. Sin persistencia multi-turn.
- **UX limitada:** Experiencia conversacional simple. Sin comprensión de contexto complejo.
- **Mantenimiento:** Cambios en lógica común requieren actualizar todos los bots
- **Costos:** TE MI TA a imaginar con lo anterior!

---

## La Solución (Este Repo)

**"N bots a 1 bot?".**

Ó: **Arquitectura que soporta N bots de forma escalable.**

**Componentes:**
- 1 Orquestador inteligente (entiende contexto, rutea automáticamente)
- N Agentes especializados (cada uno experto en su dominio)
- RAG por organización (límites, coberturas, reglas)
- State Machine + persistencia (contexto multi-turn)

```
Usuario (org_1) → Orquestador (¿quién eres? ¿qué necesitas? ¿Detecta org?)
                     ↓
              Agente Reintegro (especialista)
                     ↓
              Consulta RAG (org_1_policies.txt)
              + State Machine (crear/consultar pedido)
              + Herramientas (crear_refund, get_status)
                     ↓
              Respuesta contextualizada
              (User vuelve mañana → recupera contexto)
```

**Escalabilidad:** Agregar org_4 o agente_reclamos = agregar config + archivo. Sin tocar arquitectura.

---

## Decisiones de Arquitectura

### ¿Por qué multi-agent en lugar de 1 bot genérico?

**Decisión:** 3 agentes especializados (Reintegro, Asistencia, Reclamos, Otro)

**Razones:**
- Cada agente es experto en su dominio, respuestas más precisas
- Prompts más cortos, menos tokens, más barato!
- Fácil de testear: modifico agente de reintegro sin tocar asistencia
- Escalable: agregar nuevo proceso = agregar nuevo agente

**Alternativa rechazada:** 1 agente genérico
- Prompt gigante (mezcla todo), generico genera bolonqui!
- Más tokens por consulta
- Si falla reintegro, complica asistencia
- Difícil debuggear

**Costo:** Complejidad extra (composición, herencia). Mitigado con buenas prácticas (BotBase + especialización).

---

### ¿Por qué LangGraph para orquestación?

**Decisión:** StateGraph (nodos explícitos: validar → detectar tipo → rutear agente)

**Razones:**
- Flujo visual: nodos + edges = fácil de debuggear
- Guardrails centralizados (validar org_id ANTES de ejecutar)
- Escalable: agregar nodo nuevo = agregar `workflow.add_node()`
- Testeable: cada nodo es independiente

**Alternativa rechazada:** if/elif/else manual
- Guardrails esparcidos (repito validación en cada agente)
- Difícil de mantener (cada cambio afecta la función principal)
- No escalable (8 organizaciones = 8 ramas)

**Costo:** Curva de aprendizaje de LangGraph. **Vale la pena para sistemas complejos.**

---

### ¿Por qué RAG (ChromaDB) para coberturas/límites?

**Decisión:** Separado por org (org_1_kb, org_2_kb, org_3_kb)

**Razones:**
- Límites cambian frecuentemente (no quiero redeploy por cada cambio)
- Búsqueda semántica: usuario pregunta "¿aire acondicionado?" → RAG busca en cobertura
- Datos grandes sin explotar (3 orgs × 5 productos × 20 coberturas) = no cabe en config.py
- Usar una tool no alcanzaría ya que aumentan los costos de lectura del LLM, el RAG optimiza esto.

**Alternativa rechazada:** Hardcodear en config.py
- Cambio de cobertura = git push (deploy nuevo)
- Crece exponencialmente
- Difícil mantener

**Costo:** ChromaDB en memoria (pierde datos entre reinicios). **Para MVP está bien, producción se recomienda Pinecone!.**

---

### ¿Por qué State Machine + BD para pedidos? 

**Decisión:** Gestionar ciclo de vida (CREATED → PENDING_REVIEW → APPROVED → COMPLETED)
**Nota de integración:** Este MVP usa BD en memoria. En producción, la lógica de pedidos vive en el backend que corresponda(ai-gateway o similar). El agente consulta vía MCP tools (`crear_refund`, `get_status`) que llaman a endpoints reales.

**Razones:**
- Usuario crea pedido, se va, vuelve días después
- "¿Qué pasó con mi pedido?" → Consulta BD → Estado actual
- Operador aprueba → Webhook notifica bot → Bot continúa conversación

**Alternativa rechazada:** Sin persistencia
- Single-turn (usuario termina, listo)
- No soporta "¿dónde está mi pedido?"
- Operador no tiene dónde ver qué hacer

**Costo:** BD en memoria (MVP). **Producción → PostgreSQL.**

---

### ¿Por qué OpenAI (no Anthropic)?

**Decisión:** gpt-4o-mini

**Razones:**
- API más rápida
- Mejor integración LangChain
- Costo menor para POC

**Flexible:** Solo cambiar `config.py`, soporta cualquier LLM.

---

## Estructura

```
bots-multiagente/
├── src/
│   ├── config.py              # Orgs, límites, endpoints
│   ├── agents.py              # Agentes (LangChain)
│   ├── router.py              # Orquestación (LangGraph)
│   ├── rag.py                 # ChromaDB por org
│   ├── state_machine.py       # State machine + BD pedidos
│   ├── tools.py               # MCP tools (crear_refund, get_status)
│   ├── observability.py       # Logging + métricas
│   └── integrations/
│       └── chatwoot_mock.py   # Mock colas (simulación)
├── data/
│   ├── org_1_policies.txt
│   ├── org_2_policies.txt
│   └── org_3_policies.txt
├── tests/
│   ├── test_routing.py        # Tests de routing
│   └── test_guardrails.py     # Tests de seguridad
├── scripts/
│   └── analizar_logs.py       # Analiza logs + métricas
├── docs/
│   ├── ARQUITECTURA.md
│   ├── DECISIONS.md
│   └── INTEGRACIONES.md
├── Dockerfile
├── docker-compose.yml
├── main.py                    # FastAPI
├── requirements.txt
└── README.md
```

---

## Cómo Correr

### Local (sin Docker)

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Variables de entorno
echo "OPENAI_API_KEY=sk-..." > .env

# Crear datos
mkdir -p data
echo "Cobertura org_1: aire acondicionado, plomería" > data/org_1_policies.txt
echo "Cobertura org_2: aire, electricidad, vidrios" > data/org_2_policies.txt
echo "Cobertura org_3: plomería, electricidad" > data/org_3_policies.txt

# Correr
python main.py
```

### Con Docker

```bash
docker-compose up --build
```

---

## Testing

```bash
# Tests unitarios
pytest tests/ -v

# Análisis de logs
python scripts/analizar_logs.py
```

---

## Estado Actual (MVP)

✅ **Funciona:**
- Routing inteligente por org_id
- Agentes especializados
- RAG por organización
- State machine (gestión de pedidos)
- Observabilidad (logs + métricas)
- Guardrails (validación de org)
- Docker

⚠️ **Mock (no real aún):**
- BD en memoria (pierde datos al reiniciar)
- Chatwoot integración (stub)
- Colasde atención (simuladas)

❌ **No implementado (Fase 3):**
- Tests E2E (flujos multi-turn complejos)
- Integración Chatwoot real
- PostgreSQL para persistencia
- MCP tools completos

---

## Limitaciones Conocidas

1. **BD en memoria:** Perfecta para POC. En producción necesita PostgreSQL.
2. **ChromaDB local:** Sin escalabilidad. Producción → Pinecone/Weaviate.
3. **OpenAI fijo:** Config dice gpt-4o-mini. Fácil cambiar, pero requiere update.
4. **Chatwoot mock:** Simula colas. Integración real requiere credenciales + webhooks.

---

## Próximos Pasos

**Fase 2.3 (Tests E2E):**
- Flujos multi-turn complejos
- Usuario crea pedido → consulta estado → operador aprueba → usuario notificado

**Fase 3 (Producción):**
- Conectar ai-gateway real (endpoints de tu backend)
- PostgreSQL en lugar de memoria
- Chatwoot real en lugar de mock
- Observabilidad: Datadog o LangSmith

---

## Por Qué Este Diseño

Este MVP me permite:

- **Validar arquitectura antes de escalar:** Probar concepto con 3 orgs antes de meterme en 3 meses de desarrollo
- **Entender trade-offs:** Monolito vs microservicios, árboles vs agentes, mock vs real
- **Mostrar criterio técnico:** Decisiones justificadas con trade-offs explícitos
- **Escalar sin dolor:** Agregar org_N o agente_Y sin reescribir nada

Diseño pensado para crecer de 2 a 20 bots sin quebrar. Si algo falla con 8, fallaría peor con 50.

**Es un POC. Está bien que no sea perfecto!!**

---

## Recursos

- **Docs técnicos:** Ver `docs/ARQUITECTURA.md`, `docs/DECISIONS.md`
- **Logs:** Revisar `scripts/analizar_logs.py`
- **Tests:** `pytest tests/ -v`

---

**¿Preguntas o sugerencias?** Abierto a feedback.