# Integraciones - Qué se Conecta

## Overview

```
[Canal: Meta/WhatsApp/Telegram]
           ↓
[Tu Gateway / Botmaker]
           ↓
[Este Repo: Bots Inteligentes]
           ↓
[Consola: Chatwoot / Propia]
           ↓
[Backend: ai-gateway / Tu servidor]
           ↓
[BD: PostgreSQL / Tu BD]
```

---

## 1. Canales de Entrada

### Meta (WhatsApp)
- Proveedor: Meta Business Platform
- Identificación: phone → user_id
- Capa anterior: Tu gateway extrae (org_id, user_id, mensaje)
- Este repo recibe: POST /chat con datos identificados

### Telegram
- Proveedor: Telegram Bot API
- Identificación: telegram_id → user_id
- Igual que Meta: gateway enriquece antes de llegar

### Otros
- Aplicación propia (web, mobile)
- Same pattern: gateway enriquece, este repo procesa

---

## 2. Consola de Operadores

### Opción A: Chatwoot (Recomendado para MVP)

**Qué es:** SaaS/self-hosted para gestión de tickets

**Flujo:**
```
1. Bot crea solicitud de reintegro
2. Mock agrega a cola (MVP)
3. Operador ve en Chatwoot
4. Operador aprueba/rechaza
5. Webhook: Chatwoot → Bot
6. Bot notifica usuario
```

**Integración:**
- Webhook POST `/webhook/chatwoot`
- Payload: `{ticket_id, accion, pedido_id, estado}`

**Setup:** Docker local (opensourced)

### Opción B: Consola Propia

**Qué es:** Panel simple en tu servidor

**Flujo:**
```
1. Bot crea solicitud
2. Operador abre: GET /api/pedidos/pendientes
3. Operador aprueba: POST /api/pedidos/{id}/aprobar
4. Estado actualizado en BD
5. Bot consulta: GET /api/pedidos/{id}/status
```

**Integración:** Endpoints REST (más control)

**Setup:** Tiempo extra (tienes que hacerla)

---

## 3. Backend: ai-gateway / Tu Servidor

### Endpoints que el bot necesita

**MVP (Mock):**
```python
# En memoria, no llamadas reales
POST /chat
  Input: {org_id, user_id, mensaje}
  Output: respuesta
```

**Producción:**

El bot llama a herramientas que hacen POST a tu backend:

```
@tool
def crear_refund(org_id, user_id, monto):
    → POST /api/refunds
    ← {pedido_id, estado}

@tool  
def get_refund_status(pedido_id):
    → GET /api/refunds/{pedido_id}
    ← {estado, operador, comentarios}
```

**Responsabilidad de tu backend:**
- Validaciones de negocio (límites, requisitos)
- BD (guardar pedidos)
- Notificaciones (email, SMS)
- Auditoría

---

## 4. Base de Datos

### MVP
- BD en memoria (Pedido class)
- Suficiente para demo

### Producción
- PostgreSQL (persistencia)
- Tablas: pedidos, usuarios, eventos, auditoría

**Schema mínimo:**
```
Pedidos:
  - id (REF-00001)
  - org_id
  - user_id
  - monto
  - estado (CREATED, PENDING_REVIEW, APPROVED)
  - created_at, updated_at

Auditoría:
  - pedido_id
  - evento (creado, aprobado, rechazado)
  - timestamp
  - quién (operador_id)
```

---

## Integraciones NO Incluidas (MVP)

**Qué falta:**
- Notificaciones (email, SMS, push)
- Webhooks bidireccionales reales
- Chatwoot real (solo mock)
- PostgreSQL real (solo memoria)

**Cuándo:** Fase 2-3

---

## Flujo Completo (Ejemplo)

```
1. Usuario Meta: "Quiero reintegro de $50k"
2. Meta → tu gateway
3. Gateway: extrae (org_id="org_1", user_id="123", msg="...")
4. POST /chat → Este repo
5. Orquestador: detecta "reintegro"
6. BotReintegro: crea pedido (herramienta)
7. Herramienta: POST /api/refunds
8. Backend: crea en BD, devuelve REF-00001
9. Bot: "Solicitud REF-00001 creada. Operador revisará"
10. Operador en tu plataforma de gestión ve pedido nuevo
11. Operador aprueba desde tu plataforma
12. Plataforma actualiza estado en BD
13. Bot consulta: GET /api/refunds/REF-00001
14. Bot: "Tu reintegro fue aprobado"
```

---

## Próximos Pasos

- Fase 1: MVP (mock todo)
- Fase 2: Chatwoot real
- Fase 3: Endpoints reales + PostgreSQL