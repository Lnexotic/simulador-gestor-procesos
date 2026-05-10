"""
===============================================================================
  Módulo: logger.py — Sistema de Logging del SO Simulado
===============================================================================

  CONCEPTO PEDAGÓGICO:
  --------------------
  En un SO real, el kernel mantiene un registro (log) de todos los eventos
  importantes: creación de procesos, cambios de contexto, asignación de
  recursos, errores, etc. En Linux esto se consulta con dmesg o journalctl;
  en Windows con el Event Viewer.

  Este logger cumple dos funciones:
    1. Almacenar eventos en memoria (lista) para consulta posterior.
    2. Imprimir eventos en tiempo real con timestamp para feedback inmediato.

  ¿POR QUÉ un logger propio y no el módulo logging de Python?
  Porque queremos control total sobre el formato y la semántica del log,
  alineado con el concepto de un kernel log simplificado.
===============================================================================
"""

import time
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """
    Una entrada individual del log del sistema.

    Atributos:
    ----------
    tick : int
        Tick del reloj simulado en el que ocurrió el evento.
    timestamp : float
        Timestamp real (time.time()) para referencia temporal.
    message : str
        Descripción del evento.
    """
    tick: int
    timestamp: float
    message: str

    def __str__(self) -> str:
        # Formato: [Tick NNN | HH:MM:SS] Mensaje
        t = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"[Tick {self.tick:>4} | {t}] {self.message}"


class Logger:
    """
    Sistema de logging para el simulador del SO.

    Almacena todos los eventos en una lista interna y opcionalmente
    los imprime en consola en tiempo real.

    Atributos:
    ----------
    entries : list[LogEntry]
        Lista de todas las entradas del log.
    verbose : bool
        Si True, imprime cada evento al registrarlo.
    """

    def __init__(self, verbose: bool = True) -> None:
        """
        Inicializa el logger.

        Parámetros:
        -----------
        verbose : bool
            Si True, imprime eventos en consola al registrarlos.
        """
        self.entries: list[LogEntry] = []
        self.verbose: bool = verbose

    def log(self, message: str, tick: int = 0) -> None:
        """
        Registra un evento en el log.

        Parámetros:
        -----------
        message : str
            Descripción del evento.
        tick : int
            Tick del reloj simulado (default: 0).
        """
        entry = LogEntry(
            tick=tick,
            timestamp=time.time(),
            message=message,
        )
        self.entries.append(entry)

        if self.verbose:
            print(f"  {entry}")

    def show_history(self, last_n: int = 0) -> None:
        """
        Muestra el historial del log.

        Parámetros:
        -----------
        last_n : int
            Si > 0, muestra solo las últimas N entradas.
            Si 0, muestra todas.
        """
        print("\n" + "=" * 65)
        print("              HISTORIAL DEL LOG DEL SISTEMA")
        print("=" * 65)

        entries = self.entries[-last_n:] if last_n > 0 else self.entries

        if not entries:
            print("  (sin entradas)")
        else:
            for entry in entries:
                print(f"  {entry}")

        print("=" * 65)

    def clear(self) -> None:
        """Limpia el historial del log."""
        self.entries.clear()
