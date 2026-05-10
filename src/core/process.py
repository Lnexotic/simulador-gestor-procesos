"""
===============================================================================
  Módulo: process.py — Bloque de Control de Proceso (PCB)
===============================================================================

  CONCEPTO PEDAGÓGICO:
  --------------------
  En un Sistema Operativo real, cada proceso que se ejecuta es representado
  internamente mediante una estructura llamada PCB (Process Control Block).
  El PCB almacena TODA la información que el SO necesita para gestionar un
  proceso: su identificador único (PID), su estado actual, cuánta CPU y
  memoria requiere, etc.

  Este módulo define:
    1. ProcessState  — Los 5 estados clásicos de un proceso.
    2. ExitReason    — La razón por la que un proceso terminó.
    3. PCB           — La estructura que encapsula la metadata de un proceso.

  DIAGRAMA DE TRANSICIÓN DE ESTADOS (modelo de 5 estados):
  ─────────────────────────────────────────────────────────

      ┌─────┐   admit   ┌───────┐  dispatch  ┌─────────┐
      │ NEW │──────────►│ READY │──────────►│ RUNNING │
      └─────┘           └───────┘           └────┬────┘
                            ▲                    │
                            │  I/O complete      │ ┌──────────────┐
                            │  o evento          ├─┤ preempt      │
                         ┌──┴────┐               │ │ (Ready)      │
                         │WAITING│◄──────────────┘ └──────────────┘
                         └───────┘  I/O request
                                    o wait
                              │
                              │       ┌────────────┐
                              └──────►│ TERMINATED │  (exit / kill)
                                      └────────────┘
                              (Running también va directo a Terminated)

  TRANSICIONES VÁLIDAS:
    NEW       → READY                      (el proceso es admitido)
    READY     → RUNNING                    (el scheduler lo despacha)
    RUNNING   → READY                      (suspensión o cambio de contexto)
    RUNNING   → WAITING                    (solicita I/O o recurso)
    RUNNING   → TERMINATED                 (finaliza ejecución o es matado)
    WAITING   → READY                      (I/O completado, recurso disponible)

  Cualquier otra transición es INVÁLIDA y refleja un bug en el scheduler.
===============================================================================
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import ClassVar


# =============================================================================
# ProcessState — Estados del ciclo de vida de un proceso
# =============================================================================
class ProcessState(Enum):
    """
    Enumeración de los 5 estados clásicos de un proceso en un SO.

    ¿POR QUÉ usar un Enum?
    -----------------------
    Los Enums garantizan que el estado de un proceso solo pueda tomar uno
    de los valores definidos. Esto previene bugs donde alguien asigne un
    string arbitrario como "runing" (typo) al estado de un proceso.
    Además, los Enums son comparables, hasheables e inmutables.
    """
    NEW = auto()         # Proceso recién creado, aún no admitido
    READY = auto()       # En cola, listo para ejecutarse
    RUNNING = auto()     # Actualmente en la CPU
    WAITING = auto()     # Bloqueado esperando I/O o recurso
    TERMINATED = auto()  # Finalizó su ejecución


# =============================================================================
# ExitReason — Motivo de terminación del proceso
# =============================================================================
class ExitReason(Enum):
    """
    Razón por la cual un proceso pasó a estado TERMINATED.

    En un SO real, es importante registrar la causa de terminación para:
    - Diagnóstico: ¿fue un cierre normal o un error?
    - Depuración: ¿hubo deadlock detectado?
    - Auditoría: ¿un usuario mató el proceso manualmente?
    """
    NORMAL = auto()     # Terminación exitosa (cpu_burst completado)
    ERROR = auto()      # Terminación por error (ej. recurso no disponible)
    DEADLOCK = auto()   # Terminación por detección de deadlock
    USER_KILL = auto()  # Terminación forzada por el usuario


# =============================================================================
# Mapa de transiciones válidas
# =============================================================================
# Este diccionario define las reglas de la máquina de estados.
# La clave es el estado ACTUAL y el valor es un conjunto (frozenset)
# de estados a los que se permite transicionar.
#
# ¿POR QUÉ frozenset?
# Porque es inmutable: nadie puede modificar las reglas de transición
# en tiempo de ejecución, lo cual es exactamente lo que queremos para
# simular la rigidez de un kernel real.
VALID_TRANSITIONS: dict[ProcessState, frozenset[ProcessState]] = {
    ProcessState.NEW: frozenset({ProcessState.READY}),
    ProcessState.READY: frozenset({ProcessState.RUNNING}),
    ProcessState.RUNNING: frozenset({
        ProcessState.READY,       # Cambio de contexto (suspensión)
        ProcessState.WAITING,     # Solicitud de I/O
        ProcessState.TERMINATED,  # Fin de ejecución o kill
    }),
    ProcessState.WAITING: frozenset({ProcessState.READY}),
    ProcessState.TERMINATED: frozenset(),  # Estado sumidero: no hay salida
}


# =============================================================================
# PCB — Process Control Block
# =============================================================================
@dataclass
class PCB:
    """
    Bloque de Control de Proceso (Process Control Block).

    ¿POR QUÉ un dataclass?
    -----------------------
    Los dataclasses generan automáticamente __init__, __repr__ y __eq__,
    reduciendo boilerplate. Esto nos permite enfocarnos en la lógica del
    dominio (transiciones de estado, gestión de recursos) en lugar de
    escribir constructores manuales.

    Atributos:
    ----------
    pid : int
        Identificador único del proceso, generado de forma autoincremental.
        En un SO real, el kernel asigna PIDs secuenciales (Linux empieza
        en 1 para init/systemd).

    name : str
        Nombre legible del proceso (ej. "Firefox", "gcc", "bash").

    state : ProcessState
        Estado actual del proceso según el diagrama de 5 estados.

    priority : int
        Prioridad del proceso (0 = máxima prioridad).
        En sistemas UNIX, el rango suele ser -20 (max) a 19 (min).
        Aquí usamos 0 como máxima para simplificar.

    cpu_burst : int
        Tiempo total de CPU que el proceso necesita (en ticks de reloj).
        Representa la ráfaga de CPU completa.

    mem_mb : int
        Memoria RAM requerida por el proceso, en megabytes.

    time_remaining : int
        Tiempo de CPU que le queda al proceso. Inicia igual a cpu_burst
        y se decrementa en cada tick de ejecución. Cuando llega a 0,
        el proceso ha terminado su trabajo.

    exit_reason : ExitReason | None
        Motivo de terminación. Es None mientras el proceso no haya
        terminado.
    """

    # -------------------------------------------------------------------------
    # Generador de PIDs atómico (autoincremental)
    # -------------------------------------------------------------------------
    # ClassVar indica que este atributo pertenece a la CLASE, no a cada
    # instancia. Así, todos los PCBs comparten un único contador.
    #
    # ¿POR QUÉ no usamos threading.Lock aquí?
    # Porque la creación de procesos en nuestro simulador ocurre en el
    # hilo principal (la parte "determinista" del núcleo). Si usáramos
    # hilos para crear procesos, necesitaríamos proteger este contador.
    # -------------------------------------------------------------------------
    _next_pid: ClassVar[int] = 1

    # Campos de la instancia
    name: str
    priority: int = 0          # 0 = máxima prioridad
    cpu_burst: int = 1         # Al menos 1 tick de CPU
    mem_mb: int = 64           # 64 MB por defecto

    # Campos auto-generados (no se pasan al constructor)
    pid: int = field(init=False)
    state: ProcessState = field(init=False, default=ProcessState.NEW)
    time_remaining: int = field(init=False)
    exit_reason: ExitReason | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        """
        Método invocado automáticamente por dataclass después de __init__.

        Aquí realizamos:
        1. Asignación del PID autoincremental.
        2. Validación de los parámetros de entrada.
        3. Inicialización de time_remaining = cpu_burst.
        """
        # --- Asignación de PID ---
        self.pid = PCB._next_pid
        PCB._next_pid += 1

        # --- Validaciones de integridad ---
        # Un proceso sin ráfaga de CPU no tiene sentido: nunca ejecutaría.
        if self.cpu_burst < 1:
            raise ValueError(
                f"cpu_burst debe ser >= 1, recibido: {self.cpu_burst}. "
                "Un proceso sin trabajo de CPU no tiene razón de existir."
            )

        # La memoria debe ser positiva; un proceso siempre ocupa algo de RAM.
        if self.mem_mb < 1:
            raise ValueError(
                f"mem_mb debe ser >= 1, recibido: {self.mem_mb}. "
                "Todo proceso requiere al menos 1 MB de memoria."
            )

        # La prioridad no puede ser negativa en nuestro modelo simplificado.
        if self.priority < 0:
            raise ValueError(
                f"priority debe ser >= 0, recibido: {self.priority}. "
                "En este simulador, 0 es la prioridad más alta."
            )

        # Inicializar el tiempo restante al burst total
        self.time_remaining = self.cpu_burst

    # =========================================================================
    # Transición de estados con validación exhaustiva
    # =========================================================================
    def transition(self, new_state: ProcessState) -> None:
        """
        Cambia el estado del proceso, validando que la transición sea legal.

        ¿POR QUÉ validar las transiciones?
        ------------------------------------
        En un SO real, las transiciones de estado de un proceso están
        estrictamente controladas por el kernel. Un proceso en estado
        WAITING no puede "saltar" a RUNNING directamente; primero debe
        pasar por READY (cuando se completa la I/O). Violar estas reglas
        indica un bug severo en el scheduler.

        Esta función actúa como una MÁQUINA DE ESTADOS FINITA (FSM)
        que rechaza cualquier transición no definida en el diagrama.

        Parámetros:
        -----------
        new_state : ProcessState
            El estado objetivo al que se quiere transicionar.

        Lanza:
        ------
        ValueError
            Si la transición no es válida según VALID_TRANSITIONS.
        """
        # Obtener el conjunto de estados permitidos desde el estado actual
        allowed: frozenset[ProcessState] = VALID_TRANSITIONS.get(
            self.state, frozenset()
        )

        if new_state not in allowed:
            raise ValueError(
                f"Transicion INVALIDA: {self.state.name} -> {new_state.name} "
                f"para el proceso PID={self.pid} ({self.name}). "
                f"Transiciones validas desde {self.state.name}: "
                f"{', '.join(s.name for s in allowed) if allowed else 'NINGUNA (estado terminal)'}."
            )

        # --- Transición válida: actualizar el estado ---
        self.state = new_state

    def __str__(self) -> str:
        """
        Representación legible del PCB para la interfaz de usuario.

        Muestra toda la información relevante del proceso de forma
        compacta y fácil de leer en la terminal.
        """
        exit_info: str = ""
        if self.exit_reason is not None:
            exit_info = f" | Razon: {self.exit_reason.name}"

        return (
            f"[PID {self.pid:>3}] {self.name:<15} | "
            f"Estado: {self.state.name:<10} | "
            f"Prioridad: {self.priority} | "
            f"CPU: {self.time_remaining}/{self.cpu_burst} ticks | "
            f"RAM: {self.mem_mb} MB{exit_info}"
        )

    # =========================================================================
    # Método de clase para resetear el contador de PIDs
    # =========================================================================
    @classmethod
    def reset_pid_counter(cls) -> None:
        """
        Reinicia el contador de PIDs a 1.

        Útil para pruebas unitarias o para reiniciar la simulación
        desde cero sin tener PIDs enormes.

        ¿POR QUÉ es un classmethod?
        Porque modifica un atributo de CLASE (_next_pid), no de instancia.
        """
        cls._next_pid = 1
