import multiprocessing
import os
import threading
import time

from semaforo import Semaforo  # Importacion del script del semaforo


class ControladorTrafico:
    def __init__(self):

        # Cola para el controlador de los semaforos
        self.done_queue = multiprocessing.Queue()
        # Cola para el controlador del color de los semaforos
        self.estado_queue = multiprocessing.Queue()

        # Eventos individuales para activar semáforos
        self.events = {
            "Norte": multiprocessing.Event(),
            "Sur": multiprocessing.Event(),
            "Este": multiprocessing.Event(),
            "Oeste": multiprocessing.Event(),
        }

        # 2 barreras: una para Norte-Sur, otra para Este-Oeste
        self.barrera_NS = multiprocessing.Barrier(2)
        self.barrera_EO = multiprocessing.Barrier(2)

        # Procesos de semáforos con la barrera del grupo correspondiente (N-S)(E-O)
        self.semaforos = {
            "Norte": Semaforo(
                "Norte",
                self.events["Norte"],
                self.done_queue,
                self.estado_queue,
                self.barrera_NS,
            ),
            "Sur": Semaforo(
                "Sur",
                self.events["Sur"],
                self.done_queue,
                self.estado_queue,
                self.barrera_NS,
            ),
            "Este": Semaforo(
                "Este",
                self.events["Este"],
                self.done_queue,
                self.estado_queue,
                self.barrera_EO,
            ),
            "Oeste": Semaforo(
                "Oeste",
                self.events["Oeste"],
                self.done_queue,
                self.estado_queue,
                self.barrera_EO,
            ),
        }

        self.grupos = [["Norte", "Sur"], ["Este", "Oeste"]]

        # Estado visual de cada semáforo
        self.estado_semaforos = {
            "Norte": "rojo",
            "Sur": "rojo",
            "Este": "rojo",
            "Oeste": "rojo",
        }

    def iniciar_simulacion(self, ciclos=3):
        for s in self.semaforos.values():
            s.start()

        # print("\n--- Iniciando simulación de tráfico sincronizado por grupos ---\n")

        # Hilo para escuchar estados
        threading.Thread(target=self.actualizar_estado_visual, daemon=True).start()

        for i in range(ciclos):
            # print(f"\n>>> CICLO {i+1}")

            for grupo in self.grupos:
                # print(f"[CONTROLADOR] Activando grupo: {grupo}")
                for direccion in grupo:
                    self.events[direccion].set()

                # Esperar que ambos miembros del grupo terminen su ciclo
                for _ in grupo:
                    mensaje = self.done_queue.get()
                    # print(f"[CONTROLADOR] Recibido: {mensaje}")

                # Simulacion de tiempo entre cambio de color entre semaforos contrarios
                time.sleep(1)
        print("\n--- Simulación finalizada ---\n")
        self.detener()

    # --------------- Salida de la consola mejorada ---------------------
    def actualizar_estado_visual(self):
        while True:
            try:
                nombre, color = self.estado_queue.get(timeout=1)
                self.estado_semaforos[nombre] = color
                self.mostrar_tablero()
            except:
                continue

    def mostrar_tablero(self):
        os.system("cls" if os.name == "nt" else "clear")

        def pintar_lineas(nombre):
            color_actual = self.estado_semaforos[nombre]
            return [
                f"{nombre:^20}",
                f"ROJO     [{'O' if color_actual == 'rojo' else ' '}]",
                f"AMARILLO [{'O' if color_actual == 'amarillo' else ' '}]",
                f"VERDE    [{'O' if color_actual == 'verde' else ' '}]",
            ]

        norte = pintar_lineas("Norte")
        sur = pintar_lineas("Sur")
        este = pintar_lineas("Este")
        oeste = pintar_lineas("Oeste")

        print()
        for linea in norte:
            print(linea.center(60))

        print()
        for l_izq, l_der in zip(oeste, este):
            print(f"{l_izq:<30} {l_der:>30}")

        print()
        for linea in sur:
            print(linea.center(60))
    # ------------------------------------------------------------------------

    def detener(self):
        for s in self.semaforos.values():
            s.terminate()
            s.join()
