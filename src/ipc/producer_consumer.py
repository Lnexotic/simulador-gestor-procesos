"""
===============================================================================
  Módulo: producer_consumer.py — Problema Productor-Consumidor (IPC)
===============================================================================

  CONCEPTO PEDAGÓGICO:
  --------------------
  El problema Productor-Consumidor es uno de los problemas clásicos de
  sincronización en Sistemas Operativos, propuesto por Dijkstra en 1965.

  ESCENARIO:
    - Productores generan datos y los colocan en un buffer compartido.
    - Consumidores retiran datos del buffer para procesarlos.
    - El buffer tiene capacidad LIMITADA (en nuestro caso, 3 elementos).

  PROBLEMAS A RESOLVER:
    1. EXCLUSIÓN MUTUA: Solo un hilo puede acceder al buffer a la vez.
       → Solución: threading.Lock (mutex)
    2. SINCRONIZACIÓN: Los productores no deben escribir en un buffer
       lleno, ni los consumidores leer de uno vacío.
       → Solución: threading.Semaphore (empty y full)

  SEMÁFOROS:
    - empty (inicializado a BUFFER_SIZE=3): cuenta los espacios vacíos.
      Los productores hacen acquire() (decrementan). Si empty=0, se bloquean.
    - full (inicializado a 0): cuenta los elementos disponibles.
      Los consumidores hacen acquire() (decrementan). Si full=0, se bloquean.

  ¿POR QUÉ HILOS REALES?
    Este módulo usa threading.Thread REAL para demostrar concurrencia
    auténtica. A diferencia del scheduler (determinista por ticks),
    aquí los hilos se ejecutan de forma asíncrona y compiten por el
    buffer, mostrando condiciones de carrera y sincronización en acción.
===============================================================================
"""

import threading
import time
import random
from collections import deque


# Capacidad del buffer compartido (intencionalmente pequeña para forzar
# bloqueos observables entre productores y consumidores).
BUFFER_SIZE: int = 3

# Número de items que cada productor generará
ITEMS_PER_PRODUCER: int = 4


def run_demo() -> None:
    """
    Ejecuta la demostración completa del problema Productor-Consumidor.

    Crea 2 productores y 2 consumidores que comparten un buffer de
    capacidad 3, sincronizados con Lock y Semaphores.
    """
    print("\n" + "=" * 65)
    print("    DEMO IPC: PROBLEMA PRODUCTOR-CONSUMIDOR")
    print("    (2 Productores, 2 Consumidores, Buffer de 3)")
    print("=" * 65)

    # -----------------------------------------------------------------
    # Estructuras compartidas
    # -----------------------------------------------------------------

    # Buffer compartido (deque actúa como cola FIFO)
    buffer: deque[str] = deque()

    # Mutex: garantiza exclusión mutua al acceder al buffer.
    # Solo un hilo puede modificar el buffer a la vez.
    mutex: threading.Lock = threading.Lock()

    # Semáforo 'empty': cuenta los espacios VACÍOS en el buffer.
    # Inicializado a BUFFER_SIZE porque al inicio todo está vacío.
    # Los productores lo decrementan (acquire) antes de escribir.
    empty: threading.Semaphore = threading.Semaphore(BUFFER_SIZE)

    # Semáforo 'full': cuenta los elementos LLENOS en el buffer.
    # Inicializado a 0 porque al inicio no hay nada que consumir.
    # Los consumidores lo decrementan (acquire) antes de leer.
    full: threading.Semaphore = threading.Semaphore(0)

    # Contador de items producidos (para tracking)
    produced_count: list[int] = [0]  # Lista para mutabilidad en closures
    consumed_count: list[int] = [0]
    count_lock: threading.Lock = threading.Lock()

    # Total de items que se producirán (2 productores × 4 items cada uno)
    total_items: int = 2 * ITEMS_PER_PRODUCER

    # -----------------------------------------------------------------
    # Función del Productor
    # -----------------------------------------------------------------
    def producer(producer_id: int) -> None:
        """
        Función ejecutada por cada hilo productor.

        Protocolo del productor (Dijkstra):
          1. Producir el item (fuera de la sección crítica)
          2. empty.acquire()   — esperar si buffer lleno
          3. mutex.acquire()   — entrar a sección crítica
          4. Insertar item en buffer
          5. mutex.release()   — salir de sección crítica
          6. full.release()    — notificar a consumidores
        """
        for i in range(ITEMS_PER_PRODUCER):
            # Paso 1: Producir item (simular tiempo de producción)
            item: str = f"Item-P{producer_id}-{i}"
            time.sleep(random.uniform(0.1, 0.5))

            # Paso 2: Esperar espacio vacío en el buffer
            # Si empty=0, este hilo se BLOQUEA hasta que un consumidor
            # libere un espacio.
            empty.acquire()

            # Paso 3: Sección crítica — acceso exclusivo al buffer
            mutex.acquire()
            try:
                buffer.append(item)
                with count_lock:
                    produced_count[0] += 1
                    seq = produced_count[0]
                print(
                    f"  [Productor {producer_id}] Produjo: {item:20s} "
                    f"| Buffer: {list(buffer)} "
                    f"({len(buffer)}/{BUFFER_SIZE}) "
                    f"[{seq}/{total_items}]"
                )
            finally:
                # Paso 5: Salir de sección crítica
                mutex.release()

            # Paso 6: Notificar que hay un nuevo elemento disponible
            full.release()

    # -----------------------------------------------------------------
    # Función del Consumidor
    # -----------------------------------------------------------------
    def consumer(consumer_id: int) -> None:
        """
        Función ejecutada por cada hilo consumidor.

        Protocolo del consumidor (Dijkstra):
          1. full.acquire()    — esperar si buffer vacío
          2. mutex.acquire()   — entrar a sección crítica
          3. Retirar item del buffer
          4. mutex.release()   — salir de sección crítica
          5. empty.release()   — notificar a productores
          6. Consumir el item (fuera de la sección crítica)
        """
        while True:
            # Verificar si ya se consumieron todos los items
            with count_lock:
                if consumed_count[0] >= total_items:
                    break

            # Paso 1: Esperar elemento disponible
            # Si full=0, este hilo se BLOQUEA hasta que un productor
            # deposite un item.
            acquired = full.acquire(timeout=1.0)
            if not acquired:
                # Timeout: verificar si la demo terminó
                with count_lock:
                    if consumed_count[0] >= total_items:
                        break
                continue

            # Paso 2: Sección crítica — acceso exclusivo al buffer
            mutex.acquire()
            try:
                if buffer:
                    item = buffer.popleft()
                    with count_lock:
                        consumed_count[0] += 1
                        seq = consumed_count[0]
                    print(
                        f"  [Consumidor {consumer_id}] Consumió: {item:20s} "
                        f"| Buffer: {list(buffer)} "
                        f"({len(buffer)}/{BUFFER_SIZE}) "
                        f"[{seq}/{total_items}]"
                    )
                else:
                    # Buffer vacío (no debería ocurrir con semáforos correctos)
                    empty.release()
                    mutex.release()
                    continue
            finally:
                # Paso 4: Salir de sección crítica
                if mutex.locked():
                    mutex.release()

            # Paso 5: Notificar que hay un espacio libre
            empty.release()

            # Paso 6: Consumir (simular procesamiento)
            time.sleep(random.uniform(0.1, 0.3))

    # -----------------------------------------------------------------
    # Crear y lanzar hilos
    # -----------------------------------------------------------------
    print("\n  Iniciando hilos...\n")

    threads: list[threading.Thread] = []

    # Crear 2 productores
    for pid in range(1, 3):
        t = threading.Thread(
            target=producer,
            args=(pid,),
            name=f"Productor-{pid}",
            daemon=True,
        )
        threads.append(t)

    # Crear 2 consumidores
    for cid in range(1, 3):
        t = threading.Thread(
            target=consumer,
            args=(cid,),
            name=f"Consumidor-{cid}",
            daemon=True,
        )
        threads.append(t)

    # Iniciar todos los hilos
    for t in threads:
        t.start()

    # Esperar a que todos terminen (con timeout de seguridad)
    for t in threads:
        t.join(timeout=30.0)

    print(f"\n  [OK] Demo completada: {consumed_count[0]} items procesados.")
    print("=" * 65)
