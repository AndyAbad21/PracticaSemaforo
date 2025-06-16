import tkinter as tk
from controlador_trafico import ControladorTrafico
from cars_simulation import SimuladorVehiculos
from gui import TrafficGUIReal

if __name__ == "__main__":
    controlador = ControladorTrafico()
    simulador = SimuladorVehiculos(controlador)

    root = tk.Tk()

    # Lista de rutas a tus PNG reales:
    car_images = [
        "assets/coche-de-competicion.png",
        "assets/coche-de-competicion(1).png",
        "assets/coche-de-carreras.png",
        "assets/coche.png",
        "assets/auto.png",
        "assets/auto(1).png",
        "assets/vista-superior-del-coche.png",
        "assets/vehiculo.png",
        "assets/vehiculo(1).png"
    ]

    app = TrafficGUIReal(root, controlador, simulador, car_images, ciclos=5)
    root.mainloop()
