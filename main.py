import tkinter as tk
from controlador_trafico import ControladorTrafico
from cars_simulation import SimuladorVehiculos
from gui import TrafficGUIReal

if __name__ == "__main__":
    controlador = ControladorTrafico()
    simulador = SimuladorVehiculos(controlador)

    root = tk.Tk()

    # Lista agrupada por dirección:
    car_images = {
        "Norte": [
            "assets/sur-car.png",
            "assets/sur-car-2.png"
        ],
        "Sur": [
            "assets/norte-car.png",
            "assets/norte-car-1.png"
        ],
        "Este": [
            "assets/oeste-car.png",
            "assets/oeste-car-1.png"
        ],
        "Oeste": [
            "assets/este-car.png",
            "assets/este-car-1.png",
            "assets/este-car-2.png"
        ]
    }

    app = TrafficGUIReal(root, controlador, simulador, car_images, ciclos=5)
    root.mainloop()
