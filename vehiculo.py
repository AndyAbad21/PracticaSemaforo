import time

class Vehiculo:
    def __init__(self, id, direccion):
        self.id = id
        self.direccion = direccion
        self.tiempo_llegada = time.time()
        self.tiempo_salida = None

    def registrar_salida(self):
        self.tiempo_salida = time.time()

    def tiempo_espera(self):
        if self.tiempo_salida:
            return self.tiempo_salida - self.tiempo_llegada
        return 0
