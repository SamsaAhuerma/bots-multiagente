import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.router import Orquestador
from src.agents import BotReintegro, BotAsistencia
from src.rag import OrganizacionRAG

class TestAislamiento:
    """Tests de aislamiento de datos por org."""
    
    def test_rag_aislado_org_1(self):
        """¿RAG de org_1 está aislado?"""
        rag1 = OrganizacionRAG("org_1")
        assert rag1.org_id == "org_1"
    
    def test_rag_aislado_org_2(self):
        """¿RAG de org_2 está aislado?"""
        rag2 = OrganizacionRAG("org_2")
        assert rag2.org_id == "org_2"
    
    def test_agente_rechaza_org_invalida(self):
        """¿El agente rechaza org_id inválida?"""
        with pytest.raises(ValueError):
            BotReintegro("org_fake")
    
    def test_rag_rechaza_org_invalida(self):
        """¿RAG rechaza org_id inválida?"""
        with pytest.raises(ValueError):
            OrganizacionRAG("org_fake")


class TestGuardrails:
    """Tests de guardrails y seguridad."""
    
    def test_agente_no_puede_cambiar_org(self):
        """¿El agente mantiene su org_id original?"""
        agente = BotReintegro("org_1")
        assert agente.org_id == "org_1"
        assert agente.org_id != "org_2"
    
    def test_requisitos_diferentes_por_org(self):
        """¿Cada org tiene sus propios requisitos?"""
        agente1 = BotReintegro("org_1")
        agente2 = BotReintegro("org_2")
        
        req1 = set(agente1.config["requisitos"])
        req2 = set(agente2.config["requisitos"])
        
        # org_1: DNI, comprobante
        # org_2: DNI, comprobante, factura
        assert "factura" in req2
        assert "factura" not in req1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])