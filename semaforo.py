import multiprocessing
import time

class Semaforo(multiprocessing.Process):

    def __init__(self, name, green_event, done_queue,
                 green_duration=10, yellow_duration=3):
        super().__init__(name=name)
        self.green_event   = green_event
        self.done_queue    = done_queue
        self.green_duration  = green_duration
        self.yellow_duration = yellow_duration

    def _cambiar_color(self, color: str):
        print(f"[{self.name}] → {color}")

    def run(self):
        while True:
            # Estado ROJO: a la espera de permiso para ponerse en VERDE
            self._cambiar_color('ROJO')
            self.green_event.wait()
            self.green_event.clear()
            # Ciclo VERDE
            self._cambiar_color('VERDE')
            time.sleep(self.green_duration)
            # Ciclo AMARILLO
            self._cambiar_color('AMARILLO')
            time.sleep(self.yellow_duration)
            # Notificar al controlador fin de ciclo
            self.done_queue.put(self.name)
            
if __name__ == '__main__':
    # Crear un Event y una Queue por semáforo
    nombres = ['Norte', 'Sur', 'Este', 'Oeste']
    eventos = {n: multiprocessing.Event() for n in nombres}
    cola_done = multiprocessing.Queue()
    # Instanciar y arrancar los procesos Semaforo
    semaforos = [
        Semaforo(name=n,
                 green_event=eventos[n],
                 done_queue=cola_done,
                 green_duration=5,    
                 yellow_duration=2)   
        for n in nombres
    ]
    for s in semaforos:
        s.start()
    for turno in nombres:
        print(f"\n[Controlador] Activando semáforo {turno}")
        eventos[turno].set()
        terminado = cola_done.get()
        print(f"[Controlador] Semáforo {terminado} completó su ciclo")

    # Termina todos los procesos (PRUEBA)
    for s in semaforos:
        s.terminate()
        s.join()
