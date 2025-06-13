import multiprocessing
import time

class Semaforo(multiprocessing.Process):
    def __init__(self, name, green_event, done_queue, estado_queue, barrier, green_duration=3, yellow_duration=1):
        super().__init__(name=name)
        self.green_event = green_event # El que permite iniciar el evento desde el controlador
        self.done_queue = done_queue # Cola para notificar al controlador que el semaforo termino su ciclo
        self.estado_queue = estado_queue # Cola para notificar al controlador el color actual de semaforo 
        self.barrier = barrier # Barrera para que semaforos contrarios se esperen para notificar
        self.green_duration = green_duration # Tiempo de encendido del color verde
        self.yellow_duration = yellow_duration # Tiempo de encendido del color amarillo

    def run(self):
        while True:
            # print(f"[{self.name}] Esperando permiso para verde...")
            self.estado_queue.put((self.name, "rojo"))

            # Espera que el controlador le active el evento
            self.green_event.wait()

            self._cambiar_color("verde", self.green_duration)
            self._cambiar_color("amarillo", self.yellow_duration)
            self._cambiar_color("rojo", 0.5)

            # print(f"[{self.name}] Esperando en la barrera...")
            self.barrier.wait()  # Espera que el semaforo contrario termine (N-S)(E-O)

            self.done_queue.put(f"{self.name} terminó su ciclo")
            
            self.green_event.clear() # Limpiar todo para que el proceso no siga en ejecucion

    def _cambiar_color(self, color, duracion=None):
        # print(f"[{self.name}] Cambiando a {color.upper()}")
        self.estado_queue.put((self.name, color))
        if duracion:
            time.sleep(duracion)
        # else:
        #     print(f"[{self.name}] Esperando nuevo turno...")