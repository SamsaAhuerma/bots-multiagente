# Bots Multiagente - POC

Sistema multi-tenant de bots inteligentes usando LangChain + LangGraph + ChromaDB.

## ¿Qué es esto?

**Problema:** 3 organizaciones (org_1, org_2, org_3) con procesos similares (reintegro, asistencia) pero reglas diferentes.

**Solución:** 1 bot multiagente que:
- Reconoce la organización automáticamente
- Rutea a agentes especializados (Reintegro, Asistencia)
- Consulta RAG por organización
- Aplica guardrails de seguridad

## Decisiones de Arquitectura

### 1. **¿Por qué Multi-Agent en lugar de 1 bot para todos?**

**Decisión:** Multi-agent (3 agentes: Reintegro, Asistencia, potencial Reclamos)

**Razones:**
- Separación de responsabilidades: cada agente es experto en su dominio
- Escalabilidad: agregar nuevo proceso = agregar nuevo agente
- Testeable: puedo testear agente de reintegro sin tocar asistencia
- Menor token consumption: agente solo ve su prompt + contexto relevante

**Alternativa rechazada:** 1 agente genérico que hace todo
- Prompts más largos = más tokens
- Difícil de debuggear si falla reintegro vs asistencia
- Menos preciso (mezclaba contextos)

---

### 2. **¿Por qué LangGraph para orquestación?**

**Decisión:** LangGraph (StateGraph) para routing

**Razones:**
- Flujo explícito y visual (nodos + edges)
- Fácil debuggear: "¿en qué nodo falló?"
- Guardrails centralizados (validación de org_id antes de ejecutar)
- Futura escalabilidad: agregar loops, reintentos, etc.

**Alternativa rechazada:** Lógica manual con if/elif
- Guardrails esparcidos (repetición)
- Difícil de mantener
- No escalable (cada org = nueva rama)

---

### 3. **¿Por qué RAG (ChromaDB) para coberturas/límites?**

**Decisión:** RAG por organización (separado: org_1_kb, org_2_kb, org_3_kb)

**Razones:**
- Límites/coberturas cambian frecuentemente (no queremos redeployar código)
- Búsqueda semántica: usuario pregunta "¿aire acondicionado?" → RAG busca cobertura
- Escalable: agregar org_N = agregar archivo .txt

**Alternativa rechazada:** Config.py hardcodeado
- Cambia cobertura → redeploy
- Información crece exponencialmente (3 orgs × 5 productos × 20 coberturas)

---

### 4. **¿Por qué OpenAI (no Anthropic)?**

**Decisión:** ChatOpenAI (gpt-4o-mini)

**Razones:**
- API más rápida (latencia menor)
- Mejor soporte en LangChain
- Costo menor para POC

**Flexible:** Agregar env var para cambiar LLM sin redeploy

---

### 5. **¿Por qué ChromaDB local (no Pinecone)?**

**Decisión:** ChromaDB (memoria local)

**Razones:**
- POC: sin costo
- Desarrollo rápido (no esperar cluster externo)
- Persiste en `.chroma` (datos entre reinicios)

**Para producción:** Migrar a Pinecone/Weaviate

---

## Estructura

```
bots-multiagente/
├── src/
│   ├── config.py          # Orgs, límites, endpoints
│   ├── rag.py             # ChromaDB por org
│   ├── agents.py          # LangChain: BotReintegro, BotAsistencia
│   ├── router.py          # LangGraph: orquestación
├── data/
│   ├── org_1_policies.txt # Coberturas org_1
│   ├── org_2_policies.txt # Coberturas org_2
│   ├── org_3_policies.txt # Coberturas org_3
├── tests/
│   ├── test_routing.py    # Tests de routing
│   ├── test_guardrails.py # Tests de guardrails
├── main.py                # FastAPI + CLI
├── requirements.txt
└── README.md
```

---

## Cómo correr

### Instalar

```bash
pip install -r requirements.txt
```

### Servidor (FastAPI)

```bash
python main.py
```

Luego en otra terminal:

```bash
# Test org_1 - reintegro
curl -X POST "http://localhost:8000/chat?org_id=org_1&user_id=user_123&mensaje=quiero+reintegro+de+50000"

# Test org_2 - asistencia
curl -X POST "http://localhost:8000/chat?org_id=org_2&user_id=user_456&mensaje=que+coberturas+tiene"

# Test guardrail - org inválida
curl -X POST "http://localhost:8000/chat?org_id=org_fake&user_id=user_123&mensaje=hola"
```

### Tests

```bash
pytest tests/ -v
```

**Resultado esperado:** 10 passed, 1 xfail (asistencia requiere API key válida)

---

## Guardrails Implementados

✅ **Validación de org_id:** Orquestador valida antes de ejecutar
✅ **Aislamiento de RAG:** Cada org consulta su propia KB
✅ **Aislamiento de config:** Cada agente carga config de su org
✅ **Tests de seguridad:** Verifica que org_1 no accede org_2

---

## Decisiones Futuras

**Fase 2:**
- [ ] MCP: Exponer agentes como herramientas
- [ ] Observabilidad: Traces, latencia, tokens consumidos
- [ ] Docker: Containerizar para prod
- [ ] Tests E2E: Flujos complejos (ej: usuario cambia de idea mid-conversación)

**Fase 3:**
- [ ] Migrar RAG a Pinecone
- [ ] Base de datos para historial
- [ ] Human-in-the-loop para casos escalados

---

## Cómo contribuir

1. Tests primero (TDD)
2. Docstring en cada función
3. No hardcodear org_id: siempre pasar como parámetro
4. Si cambias prompt: actualiza tests

---

## Resultado

**MVP funcional:** 
- ✅ Multi-tenant
- ✅ Multi-agent  
- ✅ RAG por org
- ✅ Guardrails
- ✅ Tests (10/11 passing)
- ✅ Documentado

**Objetivo:** Validar arquitectura antes de migrar a producción con Botmaker 3.0 o escalar a LangGraph completo.