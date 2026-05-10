import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ipc.producer_consumer import run_demo

if __name__ == "__main__":
    print("Iniciando demostración independiente de Productor-Consumidor...")
    run_demo()
