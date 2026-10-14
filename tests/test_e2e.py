import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.router import Orquestador
from src.state_machine import obtener_db, EstadoPedido
from src.integrations.queue_mock import obtener_colas, TipoCola
from src.tools import crear_refund, obtener_refund_status


class TestFlujoCompletoReintegro:
    """
    Flujo: Usuario crea pedido → consulta estado → operador aprueba → notifica
    """

    def setup_method(self):
        self.orq = Orquestador()
        self.db = obtener_db()
        self.colas = obtener_colas()
        self.webhook_payload = None

        # Registrar webhook para simular operador
        def mock_webhook(payload):
            self.webhook_payload = payload

        self.colas.registrar_webhook(mock_webhook)

    def test_usuario_crea_pedido(self):
        """Usuario pide reintegro → pedido creado con ID."""
        resultado = crear_refund.invoke({
            "org_id": "org_1",
            "user_id": "user_e2e_1",
            "monto": 50000,
            "motivo": "Reparación plomería"
        })

        assert resultado["success"]
        assert "pedido_id" in resultado
        assert resultado["pedido_id"].startswith("REF-")
        assert resultado["estado"] == EstadoPedido.PENDING_REVIEW.value

    def test_usuario_consulta_estado(self):
        """Usuario consulta estado de su pedido."""
        # Crear pedido primero
        pedido = crear_refund.invoke({
            "org_id": "org_1",
            "user_id": "user_e2e_2",
            "monto": 30000,
            "motivo": "Test"
        })

        # Consultar estado
        estado = obtener_refund_status.invoke({
            "pedido_id": pedido["pedido_id"]
        })

        assert estado["success"]
        assert estado["pedido_id"] == pedido["pedido_id"]
        assert estado["estado"] == EstadoPedido.PENDING_REVIEW.value

    def test_operador_aprueba_y_webhook_dispara(self):
        """Operador aprueba → webhook notifica bot."""
        # Crear pedido
        pedido = crear_refund.invoke({
            "org_id": "org_1",
            "user_id": "user_e2e_3",
            "monto": 40000,
            "motivo": "Test aprobación"
        })

        # Agregar a cola
        item = self.colas.agregar_a_cola(
            tipo=TipoCola.REINTEGRO,
            org_id="org_1",
            user_id="user_e2e_3",
            pedido_id=pedido["pedido_id"],
            datos={"monto": 40000}
        )

        # Operador resuelve
        self.colas.operador_resuelve(
            item_id=item.id,
            operador_id="operador_1",
            accion="aprobar",
            comentario="Todo correcto"
        )

        # Webhook debe haber disparado
        assert self.webhook_payload is not None
        assert self.webhook_payload["accion"] == "aprobar"
        assert self.webhook_payload["pedido_id"] == pedido["pedido_id"]

    def test_flujo_completo(self):
        """Flujo de punta a punta: crear → cola → aprobar → notificar."""
        # 1. Usuario crea pedido
        pedido = crear_refund.invoke({
            "org_id": "org_1",
            "user_id": "user_e2e_4",
            "monto": 60000,
            "motivo": "Flujo completo"
        })
        assert pedido["success"]

        # 2. Se agrega a cola de operadores
        item = self.colas.agregar_a_cola(
            tipo=TipoCola.REINTEGRO,
            org_id="org_1",
            user_id="user_e2e_4",
            pedido_id=pedido["pedido_id"],
            datos={"monto": 60000}
        )
        assert item is not None

        # 3. Operador asigna
        self.colas.asignar_operador(item.id, "operador_1")
        assert item.operador_asignado == "operador_1"

        # 4. Operador aprueba
        self.colas.operador_resuelve(
            item_id=item.id,
            operador_id="operador_1",
            accion="aprobar"
        )
        assert item.resuelto

        # 5. Webhook notificó
        assert self.webhook_payload["accion"] == "aprobar"
        assert self.webhook_payload["user_id"] == "user_e2e_4"


class TestFlujoCambioIntencion:
    """
    Flujo: Usuario pregunta asistencia → cambia a reintegro mid-conversación
    """

    def setup_method(self):
        self.orq = Orquestador()

    def test_cambia_de_asistencia_a_reintegro(self):
        """Orquestador re-evalúa intención en cada mensaje."""
        # Primer mensaje: asistencia
        respuesta_1 = self.orq.procesar(
            "org_1", "user_e2e_5",
            "¿Qué coberturas tengo?"
        )
        assert respuesta_1  # Bot responde algo sobre coberturas

        # Segundo mensaje: cambia a reintegro
        respuesta_2 = self.orq.procesar(
            "org_1", "user_e2e_5",
            "Quiero un reintegro de $50k"
        )
        assert respuesta_2
        # Bot debe haber cambiado de agente sin problema
        assert "reintegro" in respuesta_2.lower() or "solicitud" in respuesta_2.lower()

    def test_vuelta_a_asistencia(self):
        """Usuario puede volver a asistencia después de reintegro."""
        # Primero reintegro
        self.orq.procesar("org_1", "user_e2e_6", "Quiero reintegro de $30k")

        # Después asistencia
        respuesta = self.orq.procesar(
            "org_1", "user_e2e_6",
            "¿Qué coberturas tengo disponibles?"
        )
        assert respuesta
        # Orquestador debe haber ruteado a asistencia sin error


class TestFlujoGuardrails:
    """
    Flujo: Guardrails contra spam de 'operador' y derivación inválida
    """

    def setup_method(self):
        self.orq = Orquestador()

    def test_spam_operador_sin_pedido(self):
        """Usuario spammea 'operador' sin solicitud activa → rechazado."""
        respuesta = self.orq.procesar(
            "org_1", "user_e2e_7",
            "operador operador operador"
        )
        # Debe responder algo, no crashear
        assert respuesta
        # No debe derivar a operador sin pedido
        assert "error" not in respuesta.lower() or "pedido" in respuesta.lower()

    def test_org_invalida_bloqueada(self):
        """Org inválida → orquestador bloquea antes de procesar."""
        respuesta = self.orq.procesar(
            "org_fake", "user_e2e_8",
            "Quiero reintegro"
        )
        assert "error" in respuesta.lower() or "no autorizada" in respuesta.lower()

    def test_mensaje_fuera_de_dominio(self):
        """Mensaje fuera de dominio → bot no improvisa."""
        respuesta = self.orq.procesar(
            "org_1", "user_e2e_9",
            "¿Cuál es tu color favorito?"
        )
        # Bot debe responder sin salirse de su dominio
        assert respuesta
        assert len(respuesta) > 0


class TestFlujoLimiteExcedido:
    """
    Flujo: Usuario pide monto mayor al límite de la organización
    """

    def test_monto_excede_limite_org_1(self):
        """org_1: límite $100k. Pide $200k → rechazado."""
        resultado = crear_refund.invoke({
            "org_id": "org_1",
            "user_id": "user_e2e_10",
            "monto": 200000,
            "motivo": "Monto excedido"
        })

        assert not resultado["success"]
        assert "excede" in resultado["error"].lower()
        assert resultado["max_permitido"] == 100000

    def test_monto_dentro_limite_org_2(self):
        """org_2: límite $150k. Pide $120k → aprobado."""
        resultado = crear_refund.invoke({
            "org_id": "org_2",
            "user_id": "user_e2e_11",
            "monto": 120000,
            "motivo": "Dentro del límite"
        })

        assert resultado["success"]
        assert resultado["estado"] == EstadoPedido.PENDING_REVIEW.value

    def test_monto_cero(self):
        """Monto = 0 → rechazado."""
        resultado = crear_refund.invoke({
            "org_id": "org_1",
            "user_id": "user_e2e_12",
            "monto": 0,
            "motivo": "Monto inválido"
        })

        assert not resultado["success"]

    def test_monto_negativo(self):
        """Monto negativo → rechazado."""
        resultado = crear_refund.invoke({
            "org_id": "org_1",
            "user_id": "user_e2e_13",
            "monto": -5000,
            "motivo": "Monto negativo"
        })

        assert not resultado["success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])