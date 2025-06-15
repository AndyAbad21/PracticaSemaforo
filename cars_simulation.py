import threading
import time
import random
from vehiculo import Vehiculo

class SimuladorVehiculos:
    def __init__(self, controlador):
        self.controlador = controlador
        # Cola de los vehiculos en cada uno de las direcciones
        self.colas = {d: [] for d in ["Norte", "Sur", "Este", "Oeste"]}
        # Para evitar que los procesos accedan al mismo tiempo a la variable compartida
        self.lock = threading.Lock()
        self.direcciones = list(self.colas.keys())
        self.vehiculos_cruzados = {d: 0 for d in self.direcciones}
        self.tiempos_espera = {d: [] for d in self.direcciones}
        self.id_counter = 1

    #se le puede añadir un numero de vehiculos a la simulacion
    def generar_vehiculos(self):#, cant=5):
        #contador = 0
        while True:
            direccion = random.choice(self.direcciones)
            with self.lock:
                vehiculo = Vehiculo(self.id_counter, direccion)
                self.colas[direccion].append(vehiculo)
                print(f"[GENERADOR] Vehículo {self.id_counter} llegó a {direccion}")
                #contador += 1
                self.id_counter += 1
            time.sleep(random.uniform(0.5, 2))  # Generación aleatoria 
        #self.generando = False

    def procesar_vehiculos(self):
        while True:
            time.sleep(1)
            with self.lock:
                self.mostrar_estado_vehiculos()  # ← mostrar el tablero de vehículos
                for direccion, cola in self.colas.items():
                    estado = self.controlador.estado_semaforos[direccion]
                    if estado == "verde" and cola:
                        vehiculo = cola.pop(0)
                        vehiculo.registrar_salida()
                        self.vehiculos_cruzados[direccion] += 1
                        self.tiempos_espera[direccion].append(vehiculo.tiempo_espera())
                        print(f"🟢 [{direccion}] Vehículo {vehiculo.id} cruzó. Esperó {vehiculo.tiempo_espera():.2f} segundos.")

    def reporte(self):
        print("\n--- REPORTE FINAL ---")
        for direccion in self.direcciones:
            total = self.vehiculos_cruzados[direccion]
            promedio = (sum(self.tiempos_espera[direccion]) / total) if total > 0 else 0
            print(f"{direccion}: {total} vehículos cruzaron. Tiempo promedio de espera: {promedio:.2f}s")

    def mostrar_estado_vehiculos(self):
        #os.system("cls" if os.name == "nt" else "clear") #actualiza el tablero y los prints de los vehiculos que llegan
        print("🚦 ESTADO DE LOS SEMÁFOROS Y VEHÍCULOS 🚗\n")

        for direccion in self.direcciones:
            color = self.controlador.estado_semaforos[direccion]
            color_icono = {"rojo": "🟥", "amarillo": "🟡", "verde": "🟢"}.get(color, "❓")

            print(f"{color_icono} [{direccion}] Semáforo en {color.upper()}")
            if self.colas[direccion]:
                cola_ids = [str(v.id) for v in self.colas[direccion]]
                print(f"   🕐 Esperando: Vehículos {', '.join(cola_ids)}")
            else:
                print("   ✅ Sin vehículos esperando")
