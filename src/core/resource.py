"""
===============================================================================
  Módulo: resource.py — Pool de Recursos del Sistema
===============================================================================

  CONCEPTO PEDAGÓGICO:
  --------------------
  Un Sistema Operativo debe gestionar recursos FINITOS (CPU, memoria, disco,
  dispositivos de I/O). Cuando un proceso solicita recursos, el SO debe:

    1. VERIFICAR si hay suficientes recursos disponibles.
    2. ASIGNAR los recursos al proceso (decrementar el pool).
    3. LIBERAR los recursos cuando el proceso termina (incrementar el pool).

  Si el SO asigna más recursos de los que tiene, ocurre un error fatal
  (en el mundo real: kernel panic, blue screen of death, etc.).

  Este módulo implementa un ResourcePool simplificado con dos recursos:
    - cpu_cores: núcleos de CPU disponibles (default: 1, simula un sistema
      mono-procesador como los primeros PCs o sistemas embebidos).
    - ram_mb: megabytes de RAM disponibles (default: 4096 MB = 4 GB).

  ANALOGÍA:
  ---------
  Imagina un hotel con 1 habitación (cpu_core) y un estacionamiento de
  4096 cajones (ram_mb). Cada huésped (proceso) necesita una habitación
  y cierto número de cajones. El recepcionista (ResourcePool) debe
  verificar disponibilidad antes de asignar.
===============================================================================
"""


class ResourcePool:
    """
    Pool de recursos del sistema simulado.

    Gestiona la asignación y liberación de CPU y memoria RAM,
    garantizando que nunca se excedan los límites físicos del sistema.

    ¿POR QUÉ no usar un dataclass?
    --------------------------------
    Aunque podríamos usar un dataclass, esta clase tiene lógica de negocio
    significativa en sus métodos (request/release). Un dataclass es ideal
    para estructuras de datos pasivas (como PCB), pero para clases con
    comportamiento complejo es preferible una clase estándar con control
    explícito sobre el constructor.

    Atributos:
    ----------
    total_cpu : int
        Número total de núcleos de CPU del sistema.
    total_ram : int
        Cantidad total de RAM en MB.
    available_cpu : int
        Núcleos de CPU actualmente libres (no asignados a procesos).
    available_ram : int
        RAM en MB actualmente libre.
    """

    def __init__(self, cpu_cores: int = 1, ram_mb: int = 4096) -> None:
        """
        Inicializa el pool de recursos del sistema.

        Parámetros:
        -----------
        cpu_cores : int
            Número de núcleos de CPU. Default: 1 (sistema mono-procesador).
        ram_mb : int
            Megabytes de RAM. Default: 4096 (4 GB).

        Lanza:
        ------
        ValueError
            Si algún recurso es menor o igual a 0.
        """
        if cpu_cores < 1:
            raise ValueError(
                f"cpu_cores debe ser >= 1, recibido: {cpu_cores}. "
                "Un sistema necesita al menos un núcleo de CPU."
            )
        if ram_mb < 1:
            raise ValueError(
                f"ram_mb debe ser >= 1, recibido: {ram_mb}. "
                "Un sistema necesita al menos 1 MB de RAM."
            )

        # Guardamos los totales para poder mostrar estadísticas
        self.total_cpu: int = cpu_cores
        self.total_ram: int = ram_mb

        # Los recursos disponibles comienzan igual a los totales
        self.available_cpu: int = cpu_cores
        self.available_ram: int = ram_mb

    # =========================================================================
    # Solicitud de recursos
    # =========================================================================
    def request(self, cpu: int, ram: int) -> bool:
        """
        Intenta asignar recursos a un proceso.

        ¿POR QUÉ devolver bool en lugar de lanzar una excepción?
        ----------------------------------------------------------
        En un SO real, la falta de recursos NO es un error del sistema;
        es una condición esperada. El scheduler simplemente coloca al
        proceso en espera (WAITING) hasta que los recursos estén
        disponibles. Por eso, devolvemos False en lugar de lanzar
        una excepción: es un flujo de control normal.

        Parámetros:
        -----------
        cpu : int
            Núcleos de CPU solicitados.
        ram : int
            Megabytes de RAM solicitados.

        Retorna:
        --------
        bool
            True si los recursos fueron asignados exitosamente.
            False si no hay suficientes recursos disponibles.
        """
        # Validar que la solicitud tiene sentido
        if cpu < 0 or ram < 0:
            # Una solicitud negativa SÍ es un error del programador
            raise ValueError(
                f"No se pueden solicitar recursos negativos: cpu={cpu}, ram={ram}."
            )

        # Verificar que la solicitud no excede la capacidad TOTAL del sistema.
        # Esto es diferente a verificar la disponibilidad: un proceso que
        # pide 8 GB de RAM en un sistema de 4 GB NUNCA podrá ejecutarse.
        if cpu > self.total_cpu:
            return False
        if ram > self.total_ram:
            return False

        # Verificar disponibilidad ACTUAL
        if cpu > self.available_cpu or ram > self.available_ram:
            return False

        # --- Asignar recursos (operación atómica en nuestro modelo) ---
        # En un SO real con multi-core, esta sección sería una región
        # crítica protegida con un spinlock del kernel.
        self.available_cpu -= cpu
        self.available_ram -= ram
        return True

    # =========================================================================
    # Liberación de recursos
    # =========================================================================
    def release(self, cpu: int, ram: int) -> bool:
        """
        Devuelve recursos al pool después de que un proceso termina.

        ¿POR QUÉ verificar que no excedamos el total?
        -----------------------------------------------
        Si liberamos más recursos de los que el sistema tiene, algo
        salió terriblemente mal. Esto indicaría un "double free" —
        un bug clásico de gestión de memoria donde se libera un
        recurso que ya fue liberado. En C, esto causa corrupción de
        heap; aquí lo detectamos y reportamos.

        Parámetros:
        -----------
        cpu : int
            Núcleos de CPU a liberar.
        ram : int
            Megabytes de RAM a liberar.

        Retorna:
        --------
        bool
            True si los recursos fueron liberados correctamente.
            False si la liberación excedería los límites del sistema.
        """
        if cpu < 0 or ram < 0:
            raise ValueError(
                f"No se pueden liberar recursos negativos: cpu={cpu}, ram={ram}."
            )

        # Verificar que no excedemos el total (detección de double-free)
        if self.available_cpu + cpu > self.total_cpu:
            return False
        if self.available_ram + ram > self.total_ram:
            return False

        # --- Devolver recursos al pool ---
        self.available_cpu += cpu
        self.available_ram += ram
        return True

    def __str__(self) -> str:
        """
        Representación legible del estado actual de los recursos.

        Muestra tanto los recursos totales como los disponibles,
        similar a cómo 'htop' o 'Task Manager' muestran el uso
        de CPU y RAM en un sistema real.
        """
        cpu_used: int = self.total_cpu - self.available_cpu
        ram_used: int = self.total_ram - self.available_ram

        return (
            f"+======================================+\n"
            f"|        RECURSOS DEL SISTEMA          |\n"
            f"+======================================+\n"
            f"|  CPU: {cpu_used}/{self.total_cpu} nucleos en uso"
            f"{' ' * (13 - len(f'{cpu_used}/{self.total_cpu}'))}|\n"
            f"|  RAM: {ram_used}/{self.total_ram} MB en uso"
            f"{' ' * (15 - len(f'{ram_used}/{self.total_ram}'))}|\n"
            f"+======================================+"
        )
