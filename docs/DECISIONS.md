# Decisiones - Trade-offs Explícitos

## Por qué este documento

Cada decisión arquitectónica tiene trade-offs. Este doc los deja explícitos para que futuro yo (o alguien que mantenga esto) entienda **por qué se eligió una cosa en lugar de la otra**, no solo "porque funciona".

---

## 1. LangChain + LangGraph + Consola vs Botmaker 3.0 Completo

### La Decisión
**Arquitectura elegida:**
- Backend: LangChain + LangGraph (orquestación + agentes)
- Frontend: Consola independiente (Chatwoot o propia)

**Alternativa rechazada:** Botmaker 3.0 (todo integrado)

### Razones

| Aspecto | LangChain+Consola | Botmaker 3.0 |
|---------|-------------------|--------------|
| Control | Total (tu código) | Limitado (UI visual) |
| Backend | Tuyo (escalable) | Vendor (Botmaker) |
| Consola | Tu elección (Chatwoot/propia) | Integrada (Botmaker) |
| Setup | 2 horas | 30 min |
| Escalabilidad | Total | Limitada |
| Lock-in | Bajo | Alto |
| Costo tokens | Depende LLM | Caro |
| HITL | Chatwoot + webhook | Nativo |

### Trade-offs

**LangChain + Consola separada:**
- Control total (qué bot backend, qué consola)
- Sin vendor lock-in
- Trabajo manual (integrar Chatwoot o hacer la propia)
- Responsable de HITL

**Botmaker 3.0 completo:**
- Setup rápido (todo integrado)
- HITL nativo
- Pero: dependencia total de Botmaker
- Caro en tokens
- Difícil escalar, costo alto

### Decisión Final

LangChain + Langraph + Consola porque:
1. Control arquitectónico (sos dueño de todo)
2. Costo flexible (qué LLM, qué consola)
3. Escalabilidad real (no limitado por vendor)
4. Sin lock-in (si Botmaker sube precios, migrás)

Botmaker 3.0 se usa solo DESPUÉS para validar que la arquitectura funciona en esa plataforma.

---

## 2. Multi-Agent vs Monolítico (1 agente para todo)

### La Decisión
**Arquitectura:** 3 agentes especializados (Reintegro, Asistencia, Reclamos)
**Alternativa rechazada:** 1 agente genérico

### Razones

**Multi-Agent:**
- Prompts cortos (menos tokens)
- Especialización (experto en su dominio)
- Fácil debuggear (bug en reintegro no toca asistencia)
- Código repetido (mitigado con herencia)

**Monolítico:**
- Menos código (1 agente)
- Prompt gigante (2000+ tokens contexto)
- Si falla reintegro, afecta asistencia
- Difícil debuggear

### Decisión Final

Multi-agent porque:
1. Tokens más baratos (especialización)
2. Mejor UX (respuestas más precisas)
3. Mantenibilidad (cambios aislados)

**Costo:** Herencia + clase base (5 líneas extra). **Vale la pena.**

---

## 3. RAG (ChromaDB) vs Tool que lee archivos vs Hardcodear

### La Decisión
**Arquitectura:** RAG con ChromaDB por org
**Alternativas rechazadas:** Tool + Hardcodear

### Razones

| Criterio | RAG | Tool | Hardcodear |
|----------|-----|------|-----------|
| Búsqueda semántica | SI | NO | NO |
| Tokens/pregunta | 100 | 10000 | 50 |
| Sin deploy | SI | NO | NO |
| Escalable | SI | Lento | NO |

**RAG:**
- Búsqueda inteligente (semántica)
- Tokens eficientes (solo relevante)
- Cambios sin deploy
- ChromaDB local (no escala)

**Tool (leer archivo):**
- Simple de entender
- Cada pregunta = leer 10k palabras (lento)
- LLM procesa TODO innecesariamente
- Sin búsqueda inteligente

**Hardcodear:**
- Más barato (tokens mínimos)
- Cambio = deploy nuevo
- Estructura rígida
- No escala (+orgs, bolonqui)

### Decisión Final

RAG porque:
1. Escalable (de 3 a 100 orgs)
2. Eficiente (solo tokens relevantes)
3. Cambios rápidos (sin deploy)

**Costo:** ChromaDB local (pierde datos). **Solución:** Producción -> Pinecone.

---

## 4. State Machine en Memoria vs PostgreSQL

### La Decisión
**MVP:** BD en memoria (Pedido + transiciones)
**Producción:** PostgreSQL

### Razones

**En Memoria:**
- Setup rápido (0 configuración)
- Testing fácil (sin DB)
- Costo cero
- Pierde datos al reiniciar

**PostgreSQL:**
- Persistencia real
- Escalable
- Queries complejas
- Setup + mantenimiento
- Costo de infraestructura

### Decisión Final

En memoria para MVP porque:
1. Valida lógica sin complexidad DB
2. Perfecta para demo (nadie reinicia en reunión)
3. Fácil migrarse a PG después (mismo código, solo storage)

**Migración:** `BdPedidos` es interfaz. Implementar `BdPedidosPostgres` sin cambiar agentes.

---

## 5. OpenAI vs Claude vs Ollama

### La Decisión
**MVP:** OpenAI (gpt-4o-mini)
**Alternativas:** Claude, Ollama local

### Razones

| Criterio | OpenAI | Claude | Ollama |
|----------|--------|--------|--------|
| Latencia | Rápido | Rápido | Muy lento (local) |
| Costo | $ | $$ | $0 |
| HITL | Bueno | Bueno | N/A |
| Integración | SI | ⚠️ | Buena |

**OpenAI:**
- Rápido
- Barato
- LangChain perfecto support
- API dependency

**Claude:**
- Mejor contexto window
- Menos alucinaciones
- Más caro
- Rate limits stringentes

**Ollama (local):**
- Gratis
- Sin API dependency
- Muy lento (CPU)
- Modelos mediocres

### Decisión Final

OpenAI porque:
1. Balance: precio + velocidad
2. LangChain integration perfecta
3. Fácil cambiar después (solo `MODEL = "..."`)

**No es decisión permanente.** Si presupuesto lo permite, evaluar Claude.

---

## 6. Logging Local vs LangSmith vs Datadog

### La Decisión
**MVP:** Logging local (archivo JSON)
**Producción:** Datadog / LangSmith

### Razones

**Local:**
- Gratis
- Control total
- Sin dependencies
- No es visualizable
- Análisis manual

**LangSmith:**
- Dashboard nativo para LangChain
- Traces automáticos
- Caro ($$$)
- Vendor lock-in

**Datadog:**
- Profesional
- APM + Logs integrados
- Muy caro
- Overkill para MVP

### Decisión Final

Local para MVP porque:
1. MVP no necesita dashboards (yo analizaré logs)
2. Gratis (presupuesto = cero)
3. Script `analizar_logs.py` es suficiente

**Producción:** Datadog si escalas a + bots.

---

## 7. Docker vs Python directo

### La Decisión
**MVP:** Docker + docker-compose
**Alternativa:** python main.py directo

### Razones

**Docker:**
- Reproducibilidad (funciona en cualquier máquina)
- Escalable (K8s después)
- Profesional (muestra mentalidad SSR)
- Overhead de setup

**Python directo:**
- Rápido para dev
- "Funciona en mi máquina" (no en producción)
- Dependencias sistema operativo

### Decisión Final

Docker porque:
1. Alguien clona, corre `docker-compose up`, listo
2. Cualquier máquina (Linux, Mac, Windows) funciona igual
3. Si después entra a producción, ya está containerizado

**Costo:** 10 min extra de setup. **Ganancia:** Profesionalismo.

---

## 8. Colas en Chatwoot vs Cola Propia

### La Decisión
**MVP:** Mock de colas (simuladas)
**Producción:** Chatwoot real O cola propia

### Razones

**Chatwoot (real):**
- HITL profesional
- Dashboard operador
- Webhooks integrados
- Setup (Docker + DB)
- Costo

**Colas propias (BD):**
- Control total
- Integración simple
- HITL manual
- Dashboard casero

**Mock (MVP):**
- Valida flujo sin dependency
- Fácil de testear
- No es real

### Decisión Final

Mock para MVP porque:
1. Valida arquitectura sin infraestructura extra
2. Fácil migrar a Chatwoot real después

**Producción:** Decidir entre Chatwoot (profesional) o cola propia (control pero requiere más capacidad técnica).

---

## 9. Tests Unitarios vs E2E vs Ambos

### La Decisión
**MVP:** Unitarios + básicos (routing, guardrails)
**Pendiente:** E2E (multi-turn complejos)

### Razones

**Unitarios:**
- Rápido (run en 2 seg)
- Fácil escribir
- No valida flujo completo

**E2E:**
- Valida sistema completo
- Detecta integraciones rotas
- Lento (10+ seg)
- Frágil (mock + real se rompen juntos)

**Ambos:**
- Cobertura 360°

### Decisión Final

Unitarios para MVP porque:
1. Rápido iterar (feedback inmediato)
2. Valida componentes críticos (guardrails, routing)
3. E2E después (cuando arquitectura está estable)

**Roadmap:** Agregar E2E en Fase 3.

---

## 10. Monorepo vs Multirepo

### La Decisión
**MVP:** Monorepo (todo en bots-multiagente/)
**Alternativa:** Separar en múltiples repos

### Razones

**Monorepo:**
- Fácil entender (todo junto)
- Sincronización simple (1 git push)
- Testing integrado
- Más peso (clonar todo)

**Multirepo:**
- Modular (cada cosa su repo)
- Más ligero
- Sincronización compleja
- Difícil ver dependencias

### Decisión Final

Monorepo porque:
1. MVP debe ser simple
2. Cuando escale, es fácil extraer a multirepo
3. Testing y deployment es más simple

**No es permanente.** Si crece a 50+ componentes, migrar a multirepo.

---

## Resumen: Principios de Decisión

1. **MVP = Simple primero**
   - Cargo en memoria, no PostgreSQL
   - Mock, no integraciones reales
   - Unitarios, no E2E

2. **Escalabilidad para el futuro**
   - Código modular (BotBase, interfaces)
   - Sin hardcoding
   - Fácil reemplazar componentes

3. **Profesionalismo**
   - Docker (reproducibilidad)
   - Tests (confianza)
   - Documentación (mantenibilidad)

4. **No lock-in**
   - LangChain, no Botmaker solo
   - OpenAI, pero `MODEL = "..."`
   - Local logging, fácil cambiar

5. **Costo efectivo**
   - Gratis mientras sea posible
   - Pago solo cuando escale
   - Benchmarks antes de invertir