import threading
from controlador_trafico import ControladorTrafico
from cars_simulation import SimuladorVehiculos

if __name__ == "__main__":
    controlador = ControladorTrafico()
    simulador = SimuladorVehiculos(controlador)

    # Hilo para generar vehículos
    threading.Thread(target=simulador.generar_vehiculos, daemon=True).start()

    # Hilo para hacer que los vehículos avancen si el semáforo está en verde
    threading.Thread(target=simulador.procesar_vehiculos, daemon=True).start()

    # Inicia la simulación de los semáforos
    controlador.iniciar_simulacion(ciclos=1)

    # Muestra el reporte final
    simulador.reporte()
