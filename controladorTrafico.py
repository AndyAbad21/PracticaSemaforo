import multiprocessing
import time

from semaforo import Semaforo  # Importacion del script del semaforo


class ControladorTrafico:
    def __init__(self):

        # Cola para el controlador de los semaforos
        self.done_queue = multiprocessing.Queue()

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
                "Semaforo Norte", self.events["Norte"], self.done_queue, self.barrera_NS
            ),
            "Sur": Semaforo(
                "Semaforo Sur", self.events["Sur"], self.done_queue, self.barrera_NS
            ),
            "Este": Semaforo(
                "Semaforo Este", self.events["Este"], self.done_queue, self.barrera_EO
            ),
            "Oeste": Semaforo(
                "Semaforo Oeste", self.events["Oeste"], self.done_queue, self.barrera_EO
            ),
        }

        self.grupos = [["Norte", "Sur"], ["Este", "Oeste"]]

    def iniciar_simulacion(self, ciclos=3):
        for s in self.semaforos.values():
            s.start()

        print("\n--- Iniciando simulación de tráfico sincronizado por grupos ---\n")

        for i in range(ciclos):
            print(f"\n>>> CICLO {i+1}")

            for grupo in self.grupos:
                print(f"[CONTROLADOR] Activando grupo: {grupo}")
                for direccion in grupo:
                    self.events[direccion].set()

                # Esperar que ambos miembros del grupo terminen su ciclo
                for _ in grupo:
                    mensaje = self.done_queue.get()
                    print(f"[CONTROLADOR] Recibido: {mensaje}")

                time.sleep(1) # Simulacion de tiempo entre cambio de color entre semaforos contrarios

        print("\n--- Simulación finalizada ---\n")
        self.detener()

    def detener(self):
        for s in self.semaforos.values():
            s.terminate()
            s.join()
