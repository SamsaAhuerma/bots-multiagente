"""
Mock de colas de atención para operadores.

En producción, esto se conecta a la plataforma de gestión de la empresa
(Chatwoot u otra), a través de webhooks bidireccionales.

Flujo real:
1. Bot crea pedido y llama a agregar_a_cola()
2. Plataforma de gestión notifica al operador
3. Operador aprueba/rechaza desde su plataforma
4. Plataforma envía webhook → Bot
5. Bot actualiza estado y notifica al usuario
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from src.observability import log_evento, log_error


class TipoCola(Enum):
    REINTEGRO = "reintegro"
    ASISTENCIA = "asistencia"
    RECLAMO = "reclamo"


@dataclass
class ItemCola:
    """Representa un item en cola de atención."""
    id: str
    tipo: TipoCola
    org_id: str
    user_id: str
    pedido_id: str
    datos: dict
    creado_en: datetime = field(default_factory=datetime.now)
    operador_asignado: Optional[str] = None
    resuelto: bool = False


class ColasAtencion:
    """
    Mock de colas de atención.

    En producción: cada método hace llamadas HTTP a la plataforma
    de gestión de la empresa (ej: POST /api/queue/add).
    """

    def __init__(self):
        self.colas: Dict[TipoCola, List[ItemCola]] = {
            TipoCola.REINTEGRO: [],
            TipoCola.ASISTENCIA: [],
            TipoCola.RECLAMO: []
        }
        self.contador_id = 0
        # Webhooks: callbacks que dispara cuando operador resuelve
        self._webhooks: List[Callable] = []

    def registrar_webhook(self, callback: Callable):
        """
        Registra callback para recibir eventos de operadores.

        En producción: La plataforma de gestión envía POST a /webhook
        con payload del evento. Acá simulamos con callbacks.
        """
        self._webhooks.append(callback)

    def agregar_a_cola(
        self,
        tipo: TipoCola,
        org_id: str,
        user_id: str,
        pedido_id: str,
        datos: dict
    ) -> ItemCola:
        """
        Agrega pedido a cola de atención.

        En producción: POST /api/queue/add → Plataforma notifica operador.
        """
        self.contador_id += 1
        item_id = f"COLA-{self.contador_id:05d}"

        item = ItemCola(
            id=item_id,
            tipo=tipo,
            org_id=org_id,
            user_id=user_id,
            pedido_id=pedido_id,
            datos=datos
        )

        self.colas[tipo].append(item)

        log_evento(
            "cola_item_agregado",
            org_id,
            item_id=item_id,
            tipo=tipo.value,
            pedido_id=pedido_id
        )

        return item

    def obtener_cola(self, tipo: TipoCola, org_id: Optional[str] = None) -> List[ItemCola]:
        """
        Obtiene items pendientes de una cola.

        En producción: GET /api/queue/{tipo} → Lista de pedidos pendientes.
        """
        items = [i for i in self.colas[tipo] if not i.resuelto]

        if org_id:
            items = [i for i in items if i.org_id == org_id]

        return items

    def asignar_operador(self, item_id: str, operador_id: str) -> Optional[ItemCola]:
        """
        Operador toma un item de la cola.

        En producción: PATCH /api/queue/{item_id}/assign → Plataforma actualiza.
        """
        item = self._buscar_item(item_id)
        if not item:
            log_error("unknown", f"Item {item_id} no encontrado", "asignar_operador")
            return None

        item.operador_asignado = operador_id

        log_evento(
            "cola_operador_asignado",
            item.org_id,
            item_id=item_id,
            operador_id=operador_id
        )

        return item

    def operador_resuelve(
        self,
        item_id: str,
        operador_id: str,
        accion: str,  # "aprobar" | "rechazar"
        comentario: str = ""
    ) -> Optional[ItemCola]:
        """
        Operador resuelve item desde su plataforma.
        Dispara webhook hacia el bot.

        En producción: Plataforma envía POST /webhook con payload del evento.
        """
        item = self._buscar_item(item_id)
        if not item:
            log_error("unknown", f"Item {item_id} no encontrado", "operador_resuelve")
            return None

        item.resuelto = True
        item.operador_asignado = operador_id

        log_evento(
            "cola_item_resuelto",
            item.org_id,
            item_id=item_id,
            pedido_id=item.pedido_id,
            accion=accion,
            operador_id=operador_id
        )

        # Simula webhook que dispara la plataforma hacia el bot
        self._disparar_webhook({
            "evento": "item_resuelto",
            "item_id": item_id,
            "pedido_id": item.pedido_id,
            "org_id": item.org_id,
            "user_id": item.user_id,
            "accion": accion,
            "operador_id": operador_id,
            "comentario": comentario
        })

        return item

    def _buscar_item(self, item_id: str) -> Optional[ItemCola]:
        """Busca item en todas las colas."""
        for items in self.colas.values():
            for item in items:
                if item.id == item_id:
                    return item
        return None

    def _disparar_webhook(self, payload: dict):
        """
        Dispara webhooks registrados.

        En producción: La plataforma de gestión hace POST /webhook/{bot_endpoint}
        con este payload. Acá lo simulamos con callbacks locales.
        """
        for callback in self._webhooks:
            try:
                callback(payload)
            except Exception as e:
                log_error(
                    payload.get("org_id", "unknown"),
                    str(e),
                    "webhook_error"
                )


# Singleton global
_colas = ColasAtencion()


def obtener_colas() -> ColasAtencion:
    """Retorna instancia global de colas."""
    return _colas