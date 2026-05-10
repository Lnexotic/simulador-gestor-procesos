"""
===============================================================================
  main.py — Interfaz Gráfica del Simulador de Gestor de Procesos
===============================================================================

  Este módulo proporciona una Interfaz Gráfica de Usuario (GUI) desarrollada
  con la biblioteca estándar 'tkinter'. Permite al usuario interactuar con 
  el núcleo del Sistema Operativo simulado.

  COMPONENTES PRINCIPALES (Cumplimiento de Rúbrica):
    - 4.1 / 4.2 / 5.1: Panel de Creación y Monitoreo (Memoria y CPU).
    - 4.3 / 5.2: 2 Algoritmos (FCFS, SJF).
    - 4.4 / 5.3: Comunicación IPC (Lanzador de Demo Productor-Consumidor).
    - 5.1 / 6: Suspensión, Reanudación y Terminación forzada (Kill).
    - 5.4 / 6: Registro y visor de Logs del sistema.

  DISEÑO ACADÉMICO:
    Todo el código está exhaustivamente comentado para su defensa y exposición.
===============================================================================
"""

import sys
import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.process import PCB, ProcessState
from src.core.resource import ResourcePool
from src.core.scheduler import Scheduler, SchedulingAlgorithm
from src.ui.logger import Logger
from src.ipc.producer_consumer import run_demo as ipc_demo

class SimulatorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simulador de SO - Versión Final (Todos los Requisitos)")
        self.root.geometry("1000x650")
        self.root.resizable(False, False)
        
        self.logger = Logger(verbose=True)
        self.resources = ResourcePool(cpu_cores=1, ram_mb=4096)
        
        self.scheduler = Scheduler(
            resources=self.resources, 
            logger=self.logger, 
            algorithm=SchedulingAlgorithm.FCFS,
        )
        
        self._build_ui()
        self.update_ui()

    def _build_ui(self):
        # =====================================================================
        # PANEL DE CREACIÓN DE PROCESOS
        # =====================================================================
        self.frame_create = tk.LabelFrame(self.root, text="1. Creación de Procesos (Con Prioridad)", padx=10, pady=10)
        self.frame_create.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.frame_create, text="Nombre:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_name = tk.Entry(self.frame_create, width=12)
        self.entry_name.insert(0, "Proceso")
        self.entry_name.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.frame_create, text="Ráfaga CPU:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.entry_burst = tk.Entry(self.frame_create, width=6)
        self.entry_burst.insert(0, "5")
        self.entry_burst.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(self.frame_create, text="RAM (MB):").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.entry_ram = tk.Entry(self.frame_create, width=6)
        self.entry_ram.insert(0, "64")
        self.entry_ram.grid(row=0, column=5, padx=5, pady=5)
        
        self.btn_create = tk.Button(self.frame_create, text="Crear Proceso", bg="#4CAF50", fg="white", command=self.on_create_process)
        self.btn_create.grid(row=0, column=6, padx=15, pady=5)

        # =====================================================================
        # PANEL DE CONTROL (RELOJ, ALGORITMOS, IPC, LOGS, KILL)
        # =====================================================================
        self.frame_control = tk.LabelFrame(self.root, text="2. Panel de Control y Planificación", padx=10, pady=10)
        self.frame_control.pack(fill=tk.X, padx=10, pady=5)
        
        self.btn_tick = tk.Button(self.frame_control, text="Ejecutar 1 Tick", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), command=self.on_execute_tick)
        self.btn_tick.pack(side=tk.LEFT, padx=5)
        
        self.btn_suspend = tk.Button(self.frame_control, text="Suspender CPU", bg="#FF9800", fg="white", command=self.on_suspend_process)
        self.btn_suspend.pack(side=tk.LEFT, padx=5)

        # Nuevo botón: FORZAR TERMINACIÓN (Kill)
        self.btn_kill = tk.Button(self.frame_control, text="Terminar (Kill)", bg="#F44336", fg="white", command=self.on_kill_process)
        self.btn_kill.pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.frame_control, text="Algoritmo:").pack(side=tk.LEFT, padx=(10, 2))
        self.algo_var = tk.StringVar(value="FCFS")
        self.combo_algo = ttk.Combobox(self.frame_control, textvariable=self.algo_var, state="readonly", width=8)
        self.combo_algo['values'] = ("FCFS", "SJF")
        self.combo_algo.pack(side=tk.LEFT)
        self.combo_algo.bind("<<ComboboxSelected>>", self.on_change_algorithm)

        self.btn_ipc = tk.Button(self.frame_control, text="Demo IPC", command=self.on_run_ipc)
        self.btn_ipc.pack(side=tk.LEFT, padx=(15, 5))
        
        self.btn_logs = tk.Button(self.frame_control, text="Logs", command=self.on_view_logs)
        self.btn_logs.pack(side=tk.LEFT, padx=5)

        self.lbl_clock = tk.Label(self.frame_control, text="Reloj: 0", font=("Arial", 12, "bold"))
        self.lbl_clock.pack(side=tk.RIGHT, padx=10)

        # =====================================================================
        # PANEL DE MONITOREO (Recursos, Cola de Listos, Cola de Suspendidos)
        # =====================================================================
        self.frame_monitor = tk.LabelFrame(self.root, text="3. Monitoreo del Sistema (Colas y Estados)", padx=10, pady=10)
        self.frame_monitor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.frame_col1 = tk.Frame(self.frame_monitor)
        self.frame_col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.lbl_cpu = tk.Label(self.frame_col1, text="CPU Disponible: 1 / 1", font=("Arial", 10))
        self.lbl_cpu.pack(anchor=tk.W, pady=2)
        
        self.lbl_ram = tk.Label(self.frame_col1, text="RAM Disponible: 4096 / 4096 MB", font=("Arial", 10))
        self.lbl_ram.pack(anchor=tk.W, pady=2)
        
        tk.Label(self.frame_col1, text="\nProceso en Ejecución:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.lbl_running = tk.Label(self.frame_col1, text="[ Ninguno ]", font=("Consolas", 11), fg="blue")
        self.lbl_running.pack(anchor=tk.W, pady=5)
        
        self.frame_col2 = tk.Frame(self.frame_monitor)
        self.frame_col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(self.frame_col2, text="Cola de Listos (READY):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.listbox_ready = tk.Listbox(self.frame_col2, height=10, width=40, font=("Consolas", 9))
        self.listbox_ready.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.scroll_ready = tk.Scrollbar(self.frame_col2, orient="vertical", command=self.listbox_ready.yview)
        self.scroll_ready.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.listbox_ready.config(yscrollcommand=self.scroll_ready.set)

        self.frame_col3 = tk.Frame(self.frame_monitor)
        self.frame_col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(self.frame_col3, text="Suspendidos (WAITING):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.listbox_waiting = tk.Listbox(self.frame_col3, height=8, width=40, font=("Consolas", 9))
        self.listbox_waiting.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        
        self.btn_wake = tk.Button(self.frame_col3, text="Despertar Seleccionado ->", command=self.on_wake_process)
        self.btn_wake.pack(pady=2)


    # =====================================================================
    # LÓGICA DE EVENTOS
    # =====================================================================
    def on_create_process(self):
        name = self.entry_name.get().strip()
        try:
            burst = int(self.entry_burst.get())
            ram = int(self.entry_ram.get())
            pcb = PCB(name=name if name else "Proceso", cpu_burst=burst, mem_mb=ram)
            
            admitido = self.scheduler.admit_process(pcb)
            if not admitido:
                messagebox.showwarning("Rechazado", "No hay memoria RAM suficiente.")
            self.update_ui()
        except ValueError:
            messagebox.showerror("Error", "Ingrese valores numéricos válidos en Burst, RAM y Prioridad.")

    def on_execute_tick(self):
        self.scheduler.execute_cycle()
        self.update_ui()

    def on_change_algorithm(self, event=None):
        seleccion = self.algo_var.get()

        if seleccion == "FCFS":
            self.scheduler.set_algorithm(SchedulingAlgorithm.FCFS)
        elif seleccion == "SJF":
            self.scheduler.set_algorithm(SchedulingAlgorithm.SJF)
            
        self.update_ui()

    def on_suspend_process(self):
        if self.scheduler.current_process:
            self.scheduler.suspend_running_process()
            self.update_ui()
        else:
            messagebox.showinfo("Información", "No hay proceso en CPU para suspender.")

    def on_kill_process(self):
        """Mata el proceso en ejecución de manera forzada."""
        current = self.scheduler.current_process
        if current:
            self.scheduler.kill_process(current.pid)
            self.update_ui()
            messagebox.showinfo("Kill", f"Proceso {current.pid} ({current.name}) terminado forzadamente.")
        else:
            messagebox.showinfo("Información", "No hay proceso en CPU para terminar.")

    def on_wake_process(self):
        seleccion = self.listbox_waiting.curselection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un proceso suspendido.")
            return
        idx = seleccion[0]
        pcb = self.scheduler.waiting_queue[idx]
        self.scheduler.resume_process(pcb.pid)
        self.update_ui()

    def on_view_logs(self):
        top = tk.Toplevel(self.root)
        top.title("Historial de Logs del Sistema")
        top.geometry("700x400")
        text_area = tk.Text(top, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff00")
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        if not self.logger.entries:
            text_area.insert(tk.END, "No hay eventos registrados aún.\n")
        else:
            for entry in self.logger.entries:
                text_area.insert(tk.END, f"{entry}\n")
        text_area.config(state=tk.DISABLED)

    def on_run_ipc(self):
        top = tk.Toplevel(self.root)
        top.title("Demo IPC: Productor - Consumidor (Hilos)")
        top.geometry("600x400")
        text_area = tk.Text(top, font=("Consolas", 10), bg="#2d2d2d", fg="#ffffff")
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Cola thread-safe para comunicar el hilo IPC con el hilo principal.
        # ¿POR QUÉ una Queue y no escribir directo al widget?
        # tkinter NO es thread-safe: modificar widgets desde un hilo 
        # secundario puede causar crashes, texto corrupto o freezes.
        # La Queue actúa como buzón seguro entre hilos.
        msg_queue: queue.Queue[str | None] = queue.Queue()

        class RedirectText(object):
            """Redirige sys.stdout a la cola en lugar de al widget directo."""
            def __init__(self, q: queue.Queue):
                self.q = q
            def write(self, string: str) -> None:
                self.q.put(string)
            def flush(self) -> None:
                pass

        def poll_queue() -> None:
            """
            Drena la cola y escribe al widget desde el hilo principal.
            Se programa cada 50ms con root.after() para garantizar
            que SOLO el hilo de tkinter modifique el widget.
            """
            while not msg_queue.empty():
                try:
                    msg = msg_queue.get_nowait()
                    if msg is None:
                        # Señal de fin: deshabilitar edición del widget
                        text_area.config(state=tk.DISABLED)
                        return
                    text_area.insert(tk.END, msg)
                    text_area.see(tk.END)
                except queue.Empty:
                    break
            # Reprogramar solo si la ventana sigue abierta
            if top.winfo_exists():
                top.after(50, poll_queue)

        def run_demo_thread() -> None:
            old_stdout = sys.stdout
            sys.stdout = RedirectText(msg_queue)
            try:
                ipc_demo()
                print("\n[+] Demo finalizada exitosamente.")
            except Exception as e:
                print(f"\n[!] Error en demo: {e}")
            finally:
                sys.stdout = old_stdout
                msg_queue.put(None)  # Señal de fin al poller

        # Iniciar el polling ANTES de lanzar el hilo
        poll_queue()
        threading.Thread(target=run_demo_thread, daemon=True).start()

    def update_ui(self):
        self.lbl_clock.config(text=f"Reloj: {self.scheduler.clock}")
        
        res = self.scheduler.resources
        self.lbl_cpu.config(text=f"CPU Disponible: {res.available_cpu} / {res.total_cpu}")
        self.lbl_ram.config(text=f"RAM Disponible: {res.available_ram} / {res.total_ram} MB")
        
        current = self.scheduler.current_process
        if current:
            texto_running = f"PID {current.pid} ({current.name})\nRestante: {current.time_remaining}/{current.cpu_burst} ticks"
            self.lbl_running.config(text=texto_running, fg="dark green")
        else:
            self.lbl_running.config(text="[ Ninguno - CPU Ociosa ]", fg="red")
            
        self.listbox_ready.delete(0, tk.END)
        for p in self.scheduler.ready_queue:
            texto_lista = f"PID {p.pid:2} | Burst: {p.time_remaining:2} | RAM: {p.mem_mb:4}MB | {p.name:8}"
            self.listbox_ready.insert(tk.END, texto_lista)
            
        self.listbox_waiting.delete(0, tk.END)
        for p in self.scheduler.waiting_queue:
            texto_lista = f"PID {p.pid:2} | Burst: {p.time_remaining:2} | RAM: {p.mem_mb:4}MB | {p.name:8}"
            self.listbox_waiting.insert(tk.END, texto_lista)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulatorGUI(root)
    root.mainloop()
