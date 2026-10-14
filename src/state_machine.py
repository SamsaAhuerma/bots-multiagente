from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
from src.observability import log_evento

class EstadoPedido(Enum):
    """Estados posibles de un pedido."""
    CREATED = "created"              # Pedido creado
    PENDING_REVIEW = "pending_review" # Esperando revisión operador
    APPROVED = "approved"             # Aprobado
    REJECTED = "rejected"             # Rechazado
    COMPLETED = "completed"           # Completado


@dataclass
class Pedido:
    """Representa un pedido de reintegro."""
    id: str
    org_id: str
    user_id: str
    monto: float
    motivo: str
    estado: EstadoPedido = EstadoPedido.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    operador_asignado: Optional[str] = None
    comentarios: List[str] = field(default_factory=list)
    
    def transicionar(self, nuevo_estado: EstadoPedido, comentario: str = ""):
        """Transiciona a nuevo estado (con validación)."""
        if not self._es_transicion_valida(self.estado, nuevo_estado):
            raise ValueError(
                f"Transición inválida: {self.estado.value} → {nuevo_estado.value}"
            )
        
        self.estado = nuevo_estado
        self.updated_at = datetime.now()
        
        if comentario:
            self.comentarios.append(f"[{datetime.now()}] {comentario}")
        
        log_evento(
            "pedido_transicion",
            self.org_id,
            pedido_id=self.id,
            estado_anterior=self.estado.value,
            estado_nuevo=nuevo_estado.value,
            comentario=comentario
        )
    
    def _es_transicion_valida(self, desde: EstadoPedido, hacia: EstadoPedido) -> bool:
        """Define transiciones válidas."""
        transiciones_validas = {
            EstadoPedido.CREATED: [EstadoPedido.PENDING_REVIEW],
            EstadoPedido.PENDING_REVIEW: [
                EstadoPedido.APPROVED,
                EstadoPedido.REJECTED
            ],
            EstadoPedido.APPROVED: [EstadoPedido.COMPLETED],
            EstadoPedido.REJECTED: [EstadoPedido.PENDING_REVIEW],  # Reabrir
            EstadoPedido.COMPLETED: []  # Terminal
        }
        
        return hacia in transiciones_validas.get(desde, [])
    
    def asignar_operador(self, operador_id: str):
        """Asigna operador y transiciona a PENDING_REVIEW."""
        self.operador_asignado = operador_id
        self.transicionar(
            EstadoPedido.PENDING_REVIEW,
            f"Asignado a operador {operador_id}"
        )


class BdPedidos:
    """Mock de BD: almacena pedidos en memoria."""
    
    def __init__(self):
        self.pedidos: Dict[str, Pedido] = {}
        self.contador_id = 0
    
    def crear_pedido(
        self,
        org_id: str,
        user_id: str,
        monto: float,
        motivo: str
    ) -> Pedido:
        """Crea nuevo pedido."""
        self.contador_id += 1
        pedido_id = f"REF-{self.contador_id:05d}"
        
        pedido = Pedido(
            id=pedido_id,
            org_id=org_id,
            user_id=user_id,
            monto=monto,
            motivo=motivo
        )
        
        self.pedidos[pedido_id] = pedido
        
        log_evento(
            "pedido_creado",
            org_id,
            pedido_id=pedido_id,
            user_id=user_id,
            monto=monto
        )
        
        return pedido
    
    def obtener_pedido(self, pedido_id: str) -> Optional[Pedido]:
        """Obtiene pedido por ID."""
        return self.pedidos.get(pedido_id)
    
    def obtener_pedidos_usuario(self, org_id: str, user_id: str) -> List[Pedido]:
        """Obtiene todos los pedidos de un usuario en una org."""
        return [
            p for p in self.pedidos.values()
            if p.org_id == org_id and p.user_id == user_id
        ]
    
    def obtener_pedidos_por_estado(
        self,
        org_id: str,
        estado: EstadoPedido
    ) -> List[Pedido]:
        """Obtiene pedidos por org y estado."""
        return [
            p for p in self.pedidos.values()
            if p.org_id == org_id and p.estado == estado
        ]
    
    def actualizar_estado(
        self,
        pedido_id: str,
        nuevo_estado: EstadoPedido,
        comentario: str = ""
    ) -> Optional[Pedido]:
        """Actualiza estado de pedido."""
        pedido = self.obtener_pedido(pedido_id)
        if not pedido:
            return None
        
        pedido.transicionar(nuevo_estado, comentario)
        return pedido


# Singleton global para MVP
_db_pedidos = BdPedidos()

def obtener_db() -> BdPedidos:
    """Retorna instancia global de BD."""
    return _db_pedidos