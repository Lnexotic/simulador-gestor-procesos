# Simulador Gestor de Procesos

Un simulador híbrido de Sistema Operativo enfocado en la gestión de procesos, algoritmos de planificación y comunicación entre procesos (IPC).

## Estructura del Proyecto

```text
simulador-gestor-procesos/
├── README.md
├── .gitignore
├── LICENSE
├── src/
│   ├── main.py                # Interfaz gráfica principal (GUI)
│   ├── core/                  # Núcleo del sistema operativo simulado
│   │   ├── process.py         # PDB, estados, PID
│   │   ├── scheduler.py       # Algoritmos FCFS, SJF
│   │   └── resource.py        # Gestión de CPU y memoria
│   ├── ipc/                   # Comunicación entre procesos (IPC)
│   │   └── producer_consumer.py
│   └── ui/                    # Interfaz y registros auxiliares
│       └── logger.py          # Sistema de logs
├── tests/                     # Tests unitarios y de integración
├── examples/                  # Scripts de demostración de componentes aislados
├── docs/                      # Documentación y diagramas
├── capturas/                  # Capturas de pantalla de la interfaz
├── benches/                   # Pruebas de rendimiento
└── .github/                   # Configuración para integración continua (CI)
```

## Requisitos

- Python 3.x
- `tkinter` (usualmente incluido en la instalación estándar de Python).

## Ejecución

Para iniciar la interfaz gráfica del simulador:

```bash
python main.py
```
