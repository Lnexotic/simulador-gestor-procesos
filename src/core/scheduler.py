"""
===============================================================================
  Módulo: scheduler.py — Planificador de Procesos (CPU Scheduler)
===============================================================================

  El Scheduler decide QUÉ proceso se ejecuta y CUÁNTO tiempo se le permite.
  Es el "cerebro" de la multitarea.

  ALGORITMOS IMPLEMENTADOS:
    1. FCFS  — First Come, First Served (FIFO, no-preemptive)
    2. SJF   — Shortest Job First (selecciona menor burst restante)
    3. RR    — Round Robin (quantum configurable, preemptive)
    4. PRIO  — Prioridades (menor número = mayor prioridad, preemptive)

  MODELO: Determinista por ticks. Cada llamada a execute_cycle() = 1 tick.
===============================================================================
"""

from collections import deque
from enum import Enum, auto

from src.core.process import PCB, ProcessState, ExitReason
from src.core.resource import ResourcePool
from src.ui.logger import Logger


class SchedulingAlgorithm(Enum):
    """Algoritmos de scheduling disponibles."""
    FCFS = auto()
    SJF = auto()
    ROUND_ROBIN = auto()
    PRIORITY = auto()


class Scheduler:
    """
    Planificador de procesos del SO simulado.

    Usa collections.deque como cola de listos (O(1) para append/popleft).
    """

    def __init__(
        self,
        resources: ResourcePool,
        logger: Logger,
        algorithm: SchedulingAlgorithm = SchedulingAlgorithm.FCFS,
        quantum: int = 3,
    ) -> None:
        self.ready_queue: deque[PCB] = deque()
        self.waiting_queue: list[PCB] = []
        self.all_processes: list[PCB] = []
        self.resources: ResourcePool = resources
        self.algorithm: SchedulingAlgorithm = algorithm
        self.quantum: int = max(1, quantum)
        self.current_process: PCB | None = None
        self.current_quantum_used: int = 0
        self.clock: int = 0
        self.logger: Logger = logger

    # === Admisión: NEW → READY ===
    def admit_process(self, pcb: PCB) -> bool:
        """Admite un proceso (NEW→READY), verificando RAM disponible."""
        if pcb.state != ProcessState.NEW:
            self.logger.log(
                f"ERROR: PID {pcb.pid} no esta en NEW ({pcb.state.name}).",
                self.clock,
            )
            return False

        if not self.resources.request(cpu=0, ram=pcb.mem_mb):
            self.logger.log(
                f"RECHAZADO: PID {pcb.pid} ({pcb.name}) necesita "
                f"{pcb.mem_mb} MB, disponible: {self.resources.available_ram} MB.",
                self.clock,
            )
            return False

        pcb.transition(ProcessState.READY)
        self.ready_queue.append(pcb)
        self.all_processes.append(pcb)

        self.logger.log(
            f"ADMITIDO: PID {pcb.pid} ({pcb.name}) -> READY | "
            f"Burst={pcb.cpu_burst} | RAM={pcb.mem_mb}MB | Pri={pcb.priority}",
            self.clock,
        )
        return True

    # === Selección según algoritmo ===
    def _select_next(self) -> PCB | None:
        """Selecciona el próximo proceso según el algoritmo activo."""
        if not self.ready_queue:
            return None

        match self.algorithm:
            case SchedulingAlgorithm.FCFS:
                return self.ready_queue.popleft()
            case SchedulingAlgorithm.SJF:
                shortest = min(self.ready_queue, key=lambda p: p.time_remaining)
                self.ready_queue.remove(shortest)
                return shortest
            case SchedulingAlgorithm.ROUND_ROBIN:
                return self.ready_queue.popleft()
            case SchedulingAlgorithm.PRIORITY:
                highest = min(self.ready_queue, key=lambda p: p.priority)
                self.ready_queue.remove(highest)
                return highest

        return self.ready_queue.popleft()

    # === Ejecución de un tick ===
    def _execute_quantum(self, pcb: PCB) -> None:
        """Simula UN tick de reloj: decrementa time_remaining."""
        pcb.time_remaining -= 1
        self.logger.log(
            f"TICK: PID {pcb.pid} ({pcb.name}) | "
            f"Restante: {pcb.time_remaining}/{pcb.cpu_burst}",
            self.clock,
        )

    # === Ciclo principal ===
    def execute_cycle(self) -> str:
        """
        Ejecuta UN ciclo del scheduler (1 tick).

        Flujo:
          1. Si CPU libre → despachar proceso (READY→RUNNING)
          2. Ejecutar tick del proceso actual
          3. ¿Terminó? → TERMINATED, liberar recursos
          4. ¿Quantum expirado? (RR) → READY (preemption)
          5. ¿Mayor prioridad en cola? (PRIO) → preemption
        """
        self.clock += 1

        # Paso 1: Despachar si CPU libre
        if self.current_process is None:
            next_pcb = self._select_next()
            if next_pcb is None:
                self.logger.log("IDLE: Cola vacia, CPU ociosa.", self.clock)
                return f"[Tick {self.clock}] CPU ociosa -- cola vacia."

            if not self.resources.request(cpu=1, ram=0):
                self.ready_queue.appendleft(next_pcb)
                return f"[Tick {self.clock}] No hay CPU disponible."

            next_pcb.transition(ProcessState.RUNNING)
            self.current_process = next_pcb
            self.current_quantum_used = 0
            self.logger.log(
                f"DISPATCH: PID {next_pcb.pid} ({next_pcb.name}) -> RUNNING "
                f"[{self.algorithm.name}]",
                self.clock,
            )

        # Paso 2: Ejecutar tick
        assert self.current_process is not None
        self._execute_quantum(self.current_process)
        self.current_quantum_used += 1

        # Paso 3: ¿Terminó?
        if self.current_process.time_remaining <= 0:
            finished = self.current_process
            finished.transition(ProcessState.TERMINATED)
            finished.exit_reason = ExitReason.NORMAL
            self.resources.release(cpu=1, ram=finished.mem_mb)
            self.logger.log(
                f"TERMINADO: PID {finished.pid} ({finished.name}) "
                f"completo {finished.cpu_burst} ticks.",
                self.clock,
            )
            self.current_process = None
            self.current_quantum_used = 0
            return (
                f"[Tick {self.clock}] PID {finished.pid} ({finished.name}) "
                f"TERMINADO (Normal)."
            )

        # Paso 4: ¿Quantum expirado? (Round Robin)
        if (
            self.algorithm == SchedulingAlgorithm.ROUND_ROBIN
            and self.current_quantum_used >= self.quantum
        ):
            preempted = self.current_process
            preempted.transition(ProcessState.READY)
            self.resources.release(cpu=1, ram=0)
            self.ready_queue.append(preempted)
            self.current_process = None
            self.current_quantum_used = 0
            self.logger.log(
                f"PREEMPTION: PID {preempted.pid} ({preempted.name}) -> READY "
                f"(quantum={self.quantum} expirado) | "
                f"Restante: {preempted.time_remaining}",
                self.clock,
            )
            return (
                f"[Tick {self.clock}] PID {preempted.pid} interrumpido "
                f"(quantum). Vuelve a READY."
            )

        # Paso 5: Preemption por prioridad
        if (
            self.algorithm == SchedulingAlgorithm.PRIORITY
            and self.ready_queue
        ):
            best = min(self.ready_queue, key=lambda p: p.priority)
            if best.priority < self.current_process.priority:
                preempted_p = self.current_process
                preempted_p.transition(ProcessState.READY)
                self.resources.release(cpu=1, ram=0)
                self.ready_queue.append(preempted_p)
                self.current_process = None
                self.current_quantum_used = 0
                self.logger.log(
                    f"PREEMPTION(Pri): PID {preempted_p.pid} desplazado por "
                    f"PID {best.pid} (pri={best.priority}).",
                    self.clock,
                )
                return (
                    f"[Tick {self.clock}] PID {preempted_p.pid} desplazado "
                    f"por mayor prioridad."
                )

        return (
            f"[Tick {self.clock}] PID {self.current_process.pid} "
            f"({self.current_process.name}) ejecutandose. "
            f"Restante: {self.current_process.time_remaining}."
        )

    # === Suspender y Reanudar (I/O simulado) ===
    def suspend_running_process(self) -> bool:
        """Suspende el proceso actualmente en ejecución (pasa a WAITING)."""
        if self.current_process is None:
            self.logger.log("SUSPEND FALLIDO: No hay proceso en CPU.", self.clock)
            return False

        target = self.current_process
        target.transition(ProcessState.WAITING)
        self.resources.release(cpu=1, ram=0)
        self.waiting_queue.append(target)
        self.current_process = None
        self.current_quantum_used = 0
        self.logger.log(f"SUSPEND: PID {target.pid} ({target.name}) -> WAITING", self.clock)
        return True

    def resume_process(self, pid: int) -> bool:
        """Despierta un proceso suspendido (WAITING -> READY)."""
        target = None
        for p in self.waiting_queue:
            if p.pid == pid:
                target = p
                break

        if target is None:
            self.logger.log(f"RESUME FALLIDO: PID {pid} no está en WAITING.", self.clock)
            return False

        self.waiting_queue.remove(target)
        target.transition(ProcessState.READY)
        self.ready_queue.append(target)
        self.logger.log(f"RESUME: PID {target.pid} ({target.name}) -> READY", self.clock)
        return True

    # === Cambiar algoritmo ===
    def set_algorithm(
        self, algorithm: SchedulingAlgorithm, quantum: int | None = None
    ) -> None:
        """Cambia el algoritmo de scheduling en caliente."""
        self.algorithm = algorithm
        if quantum is not None:
            self.quantum = max(1, quantum)
        self.logger.log(
            f"ALGORITMO: {algorithm.name}"
            + (f" (quantum={self.quantum})"
               if algorithm == SchedulingAlgorithm.ROUND_ROBIN else ""),
            self.clock,
        )

    # === Kill ===
    def kill_process(self, pid: int) -> bool:
        """Termina forzadamente un proceso por PID (simula kill -9)."""
        target: PCB | None = None
        for p in self.all_processes:
            if p.pid == pid and p.state != ProcessState.TERMINATED:
                target = p
                break

        if target is None:
            self.logger.log(f"KILL FALLIDO: PID {pid} no encontrado.", self.clock)
            return False

        # En CPU
        if self.current_process and self.current_process.pid == pid:
            self.current_process.transition(ProcessState.TERMINATED)
            self.current_process.exit_reason = ExitReason.USER_KILL
            self.resources.release(cpu=1, ram=self.current_process.mem_mb)
            self.logger.log(
                f"KILL: PID {pid} ({self.current_process.name}) desde RUNNING.",
                self.clock,
            )
            self.current_process = None
            self.current_quantum_used = 0
            return True

        # En cola READY
        if target.state == ProcessState.READY:
            self.ready_queue.remove(target)
            target.transition(ProcessState.RUNNING)
            target.transition(ProcessState.TERMINATED)
            target.exit_reason = ExitReason.USER_KILL
            self.resources.release(cpu=0, ram=target.mem_mb)
            self.logger.log(
                f"KILL: PID {pid} ({target.name}) desde READY.", self.clock
            )
            return True

        # WAITING
        if target.state == ProcessState.WAITING:
            if target in self.waiting_queue:
                self.waiting_queue.remove(target)
            target.transition(ProcessState.READY)
            target.transition(ProcessState.RUNNING)
            target.transition(ProcessState.TERMINATED)
            target.exit_reason = ExitReason.USER_KILL
            self.resources.release(cpu=0, ram=target.mem_mb)
            self.logger.log(
                f"KILL: PID {pid} ({target.name}) desde WAITING.", self.clock
            )
            return True

        return False

    # === Reporte de estado ===
    def get_system_status(self) -> str:
        """Genera reporte completo del estado del sistema."""
        lines: list[str] = []
        lines.append("=" * 65)
        lines.append("          ESTADO DEL SISTEMA OPERATIVO SIMULADO")
        lines.append("=" * 65)
        lines.append(f"  Reloj   : Tick {self.clock}")
        lines.append(f"  Algoritmo: {self.algorithm.name}")
        if self.algorithm == SchedulingAlgorithm.ROUND_ROBIN:
            lines.append(f"  Quantum  : {self.quantum} ticks")
        lines.append("")
        lines.append(str(self.resources))
        lines.append("")

        lines.append("--- PROCESO EN CPU ---")
        if self.current_process:
            lines.append(f"  {self.current_process}")
            if self.algorithm == SchedulingAlgorithm.ROUND_ROBIN:
                lines.append(
                    f"  Quantum usado: {self.current_quantum_used}/{self.quantum}"
                )
        else:
            lines.append("  (CPU ociosa)")
        lines.append("")

        lines.append(f"--- COLA DE LISTOS ({len(self.ready_queue)}) ---")
        if self.ready_queue:
            for i, pcb in enumerate(self.ready_queue, 1):
                lines.append(f"  {i}. {pcb}")
        else:
            lines.append("  (vacia)")
        lines.append("")

        lines.append(f"--- COLA DE SUSPENDIDOS (WAITING) ({len(self.waiting_queue)}) ---")
        if self.waiting_queue:
            for pcb in self.waiting_queue:
                lines.append(f"  {pcb}")
        else:
            lines.append("  (ninguno)")
        lines.append("")

        terminated = [p for p in self.all_processes
                      if p.state == ProcessState.TERMINATED]
        lines.append(f"--- TERMINADOS ({len(terminated)}) ---")
        for pcb in terminated:
            lines.append(f"  {pcb}")
        if not terminated:
            lines.append("  (ninguno)")

        lines.append("=" * 65)
        return "\n".join(lines)
