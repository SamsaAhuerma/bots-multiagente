import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.router import Orquestador
from src.agents import BotReintegro, BotAsistencia

class TestRouting:
    """Tests de routing y orquestación."""
    
    def test_routing_reintegro(self):
        """¿El orquestador rutea correctamente a reintegro?"""
        orq = Orquestador()
        respuesta = orq.procesar("org_1", "user_123", "quiero reintegro de 50000")
        assert "reintegro" in respuesta.lower()
    
    def test_routing_asistencia(self):
        """¿El orquestador rutea correctamente a asistencia?"""
        orq = Orquestador()
        respuesta = orq.procesar("org_1", "user_123", "¿qué coberturas tiene?")
        assert respuesta
    
    def test_org_invalida(self):
        """¿Rechaza org_id inválida?"""
        orq = Orquestador()
        respuesta = orq.procesar("org_fake", "user_123", "hola")
        assert "error" in respuesta.lower() or "no autorizada" in respuesta.lower()
    
    def test_limites_org_1(self):
        """¿Valida límites de org_1 correctamente?"""
        agente = BotReintegro("org_1")
        assert agente.config["max_reintegro"] == 100000
    
    def test_limites_org_2(self):
        """¿Valida límites de org_2 correctamente?"""
        agente = BotReintegro("org_2")
        assert agente.config["max_reintegro"] == 150000

if __name__ == "__main__":
    pytest.main([__file__, "-v"])