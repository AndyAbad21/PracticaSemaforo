import multiprocessing
import time

class Semaforo(multiprocessing.Process):
    def __init__(self, name, green_event, done_queue, green_duration=5, yellow_duration=3):
        super().__init__(name=name)
        self.green_event = green_event      # Señal para ponerse en verde
        self.done_queue = done_queue        # Cola para notificar al controlador
        self.green_duration = green_duration
        self.yellow_duration = yellow_duration

    def run(self):
        while True: # Ciclo completo del semaforo 
            print(f"[{self.name}] Esperando permiso para verde...")
            self.green_event.wait()  # Espera que el controlador active el evento
            self._cambiar_color("verde", self.green_duration)

            self._cambiar_color("amarillo", self.yellow_duration)
            self._cambiar_color("rojo")  # Vuelve a rojo automáticamente

            # Avisar al controlador que terminó su turno
            self.done_queue.put(f"{self.name} terminó su ciclo")

            # Reinicia el evento para esperar el siguiente turno
            self.green_event.clear()

    def _cambiar_color(self, color, duracion=None):
        print(f"[{self.name}] Cambiando a {color.upper()}")
        if duracion:
            time.sleep(duracion)
        else:
            print(f"[{self.name}] Esperando nuevo turno...")

if __name__ == "__main__":
    green_event = multiprocessing.Event()
    done_queue = multiprocessing.Queue()

    semaforo_norte = Semaforo("Semaforo Norte", green_event, done_queue)
    semaforo_norte.start()

    # Simular encender verde manualmente
    time.sleep(2)
    print("\n>> Activando verde")
    green_event.set()

    # Esperar la notificación del semáforo
    mensaje = done_queue.get()
    print(f"\n>> Controlador recibió: {mensaje}")

    # Terminar la prueba (proceso infinito, forzamos a cerrar)
    semaforo_norte.terminate()
    semaforo_norte.join()
