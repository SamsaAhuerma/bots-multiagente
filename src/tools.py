from langchain.tools import tool
from typing import Optional, List
from src.state_machine import obtener_db, EstadoPedido, Pedido
from src.observability import log_evento, log_error

# Obtener instancia de BD global
db = obtener_db()


@tool
def crear_refund(
    org_id: str,
    user_id: str,
    monto: float,
    motivo: str
) -> dict:
    """
    Crea una solicitud de reintegro.
    
    Args:
        org_id: Identificador de la organización
        user_id: Identificador del usuario
        monto: Monto del reintegro
        motivo: Motivo del reintegro
    
    Returns:
        dict con id del pedido y estado
    """
    try:
        # Validar org_id
        from src.config import REGLAS_NEGOCIO
        if org_id not in REGLAS_NEGOCIO:
            log_error(org_id, "org_invalida", "crear_refund")
            return {
                "success": False,
                "error": f"Organización '{org_id}' no válida"
            }
        
        # Validar monto
        max_monto = REGLAS_NEGOCIO[org_id]["max_reintegro"]
        if monto > max_monto:
            log_error(
                org_id,
                f"monto_excedido: {monto} > {max_monto}",
                "crear_refund"
            )
            return {
                "success": False,
                "error": f"Monto ${monto} excede límite ${max_monto}",
                "max_permitido": max_monto
            }
        
        if monto <= 0:
            return {
                "success": False,
                "error": "Monto debe ser positivo"
            }
        
        # Crear pedido
        pedido = db.crear_pedido(
            org_id=org_id,
            user_id=user_id,
            monto=monto,
            motivo=motivo
        )
        
        # Transicionar a PENDING_REVIEW
        pedido.transicionar(
            EstadoPedido.PENDING_REVIEW,
            "Creado automáticamente por bot"
        )
        
        log_evento(
            "refund_creado",
            org_id,
            pedido_id=pedido.id,
            user_id=user_id,
            monto=monto
        )
        
        return {
            "success": True,
            "pedido_id": pedido.id,
            "estado": pedido.estado.value,
            "monto": pedido.monto,
            "mensaje": f"Solicitud creada (ID: {pedido.id}). Operador revisará en breve."
        }
    
    except Exception as e:
        log_error(org_id, str(e), "crear_refund")
        return {
            "success": False,
            "error": f"Error al crear solicitud: {str(e)}"
        }


@tool
def obtener_refund_status(pedido_id: str) -> dict:
    """
    Consulta el estado de una solicitud de reintegro.
    
    Args:
        pedido_id: ID del pedido (ej: REF-00001)
    
    Returns:
        dict con estado actual del pedido
    """
    try:
        pedido = db.obtener_pedido(pedido_id)
        
        if not pedido:
            return {
                "success": False,
                "error": f"Pedido '{pedido_id}' no encontrado"
            }
        
        # Mapear estados a mensajes amigables
        mensajes_estado = {
            EstadoPedido.CREATED: "Creado",
            EstadoPedido.PENDING_REVIEW: "En revisión por operador",
            EstadoPedido.APPROVED: "Aprobado ✓",
            EstadoPedido.REJECTED: "Rechazado ✗",
            EstadoPedido.COMPLETED: "Completado"
        }
        
        log_evento(
            "refund_consulta",
            pedido.org_id,
            pedido_id=pedido_id,
            estado=pedido.estado.value
        )
        
        return {
            "success": True,
            "pedido_id": pedido.id,
            "estado": pedido.estado.value,
            "estado_amigable": mensajes_estado[pedido.estado],
            "monto": pedido.monto,
            "motivo": pedido.motivo,
            "creado": pedido.created_at.isoformat(),
            "actualizado": pedido.updated_at.isoformat(),
            "operador_asignado": pedido.operador_asignado,
            "comentarios": pedido.comentarios
        }
    
    except Exception as e:
        log_error("unknown", str(e), "obtener_refund_status")
        return {
            "success": False,
            "error": f"Error al consultar: {str(e)}"
        }


@tool
def obtener_refunds_usuario(org_id: str, user_id: str) -> dict:
    """
    Obtiene todas las solicitudes de reintegro de un usuario.
    
    Args:
        org_id: Identificador de la organización
        user_id: Identificador del usuario
    
    Returns:
        dict con lista de pedidos del usuario
    """
    try:
        pedidos = db.obtener_pedidos_usuario(org_id, user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "org_id": org_id,
            "total": len(pedidos),
            "pedidos": [
                {
                    "id": p.id,
                    "monto": p.monto,
                    "estado": p.estado.value,
                    "creado": p.created_at.isoformat()
                }
                for p in pedidos
            ]
        }
    
    except Exception as e:
        log_error(org_id, str(e), "obtener_refunds_usuario")
        return {
            "success": False,
            "error": f"Error al consultar: {str(e)}"
        }


# Agrupar todas las tools para MCP
REFUND_TOOLS = [
    crear_refund,
    obtener_refund_status,
    obtener_refunds_usuario
]


def obtener_herramientas():
    """Retorna todas las herramientas disponibles."""
    return REFUND_TOOLS