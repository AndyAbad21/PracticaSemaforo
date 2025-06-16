import tkinter as tk
from tkinter import ttk
import threading
import random
import os

from PIL import Image, ImageTk


class CarIcon:
    def __init__(self, canvas, image, x, y, direction, speed):
        self.canvas = canvas
        self.image = image
        self.image_id = canvas.create_image(x, y, image=image)
        self.direction = direction
        self.speed = speed

    def move(self):
        dx, dy = {
            "Norte": (0, self.speed),
            "Sur": (0, -self.speed),
            "Este": (-self.speed, 0),
            "Oeste": (self.speed, 0)
        }[self.direction]

        self.canvas.move(self.image_id, dx, dy)

    def get_position(self):
        return self.canvas.coords(self.image_id)

    def destroy(self):
        self.canvas.delete(self.image_id)


class TrafficGUIReal:
    def __init__(self, root, controlador, simulador, car_images_paths, ciclos=5):
        self.root = root
        self.root.title("Simulación de Tráfico Realista")

        self.controlador = controlador
        self.simulador = simulador
        self.ciclos = ciclos

        self.canvas = tk.Canvas(self.root, width=800, height=800, bg="gray")
        self.canvas.pack()

        # Cargar imágenes PNG
        self.car_images = []
        for path in car_images_paths:
            img = Image.open(path).resize((30, 30))
            self.car_images.append(ImageTk.PhotoImage(img))

        # Semáforos GUI (círculos)
        self.semaforos_gui = {}
        self.draw_intersection()

        # Lista de autos visibles
        self.cars_icons = []

        # Botón para iniciar
        self.start_btn = ttk.Button(self.root, text="Iniciar Simulación", command=self.start_simulation)
        self.start_btn.pack(pady=10)

        # Loop de actualización
        self.update_gui()

    def draw_intersection(self):
        # Dibujar carriles (simplificado)
        # Vías verticales
        self.canvas.create_rectangle(350, 0, 450, 800, fill="dimgray")
        # Vías horizontales
        self.canvas.create_rectangle(0, 350, 800, 450, fill="dimgray")
        # Líneas blancas
        for i in range(0, 800, 40):
            self.canvas.create_line(400, i, 400, i+20, fill="white")
            self.canvas.create_line(i, 400, i+20, 400, fill="white")

        # Semáforos
        coords = {
            "Norte": (400, 300),
            "Sur": (400, 500),
            "Este": (500, 400),
            "Oeste": (300, 400)
        }
        for direccion, (x, y) in coords.items():
            circ = self.canvas.create_oval(x-15, y-15, x+15, y+15, fill="gray")
            self.semaforos_gui[direccion] = circ

    def update_gui(self):
        # Actualizar semáforos
        colores = {"rojo": "red", "amarillo": "yellow", "verde": "green"}
        for direccion, circ in self.semaforos_gui.items():
            estado = self.controlador.estado_semaforos.get(direccion, "rojo")
            self.canvas.itemconfig(circ, fill=colores[estado])

        # Actualizar autos
        self.update_cars()

        self.root.after(30, self.update_gui)

    def update_cars(self):
        # Crear nuevos autos si hay en colas
        for direccion, carriles in self.simulador.colas.items():
            for carril_index, cola in enumerate(carriles):
                for vehiculo in cola:
                    if not hasattr(vehiculo, 'icon'):
                        # Nueva posición inicial
                        if direccion == "Norte":
                            x = 380 + carril_index*30
                            y = 0
                        elif direccion == "Sur":
                            x = 420 + carril_index*30
                            y = 800
                        elif direccion == "Este":
                            x = 800
                            y = 420 + carril_index*30
                        elif direccion == "Oeste":
                            x = 0
                            y = 380 + carril_index*30

                        image = random.choice(self.car_images)
                        vehiculo.icon = CarIcon(self.canvas, image, x, y, direccion, speed=5)
                        self.cars_icons.append(vehiculo.icon)

        # Mover autos existentes
        for car_icon in self.cars_icons[:]:
            car_icon.move()
            x, y = car_icon.get_position()
            # Si sale del canvas, borrarlo
            if x < -50 or x > 850 or y < -50 or y > 850:
                car_icon.destroy()
                self.cars_icons.remove(car_icon)

    def start_simulation(self):
        self.start_btn.config(state="disabled")
        threading.Thread(target=self.simulador.generar_vehiculos, daemon=True).start()
        threading.Thread(target=self.simulador.procesar_vehiculos, daemon=True).start()
        threading.Thread(target=self.run_controller, daemon=True).start()

    def run_controller(self):
        self.controlador.iniciar_simulacion(ciclos=self.ciclos)
        self.simulador.reporte()
