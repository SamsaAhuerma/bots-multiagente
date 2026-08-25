# scripts/analizar_logs.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.observability import AnalysisLogs

if __name__ == "__main__":
    AnalysisLogs.imprimir_reporte()