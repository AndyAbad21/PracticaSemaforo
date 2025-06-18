import tkinter as tk
from tkinter import ttk
import threading
import random
from PIL import Image, ImageTk

# --- Parámetros globales ---
WIN = 1000           # Tamaño de ventana
ICON_SIZE = 40       # Tamaño de íconos de autos
GAP = 5              # Espacio entre autos en cola
CAR_SPEED = 3        # Velocidad de desplazamiento de autos
SPAWN_OUT = 100      # Punto fuera de la pantalla para spawnear autos

# Coordenadas y líneas de referencia del cruce
mid = WIN // 2
offset = 70

CROSS_LINE = {
    "Norte": mid - offset,
    "Sur":   mid + offset,
    "Oeste": mid - offset,
    "Este":  mid + offset
}

STOP_LINE = {
    "Norte": CROSS_LINE["Norte"] - 40,
    "Sur":   CROSS_LINE["Sur"] + 40,
    "Oeste": CROSS_LINE["Oeste"] - 40,
    "Este":  CROSS_LINE["Este"] + 40
}

LANE_OFFSET = 30

LANE_COORD = {
    "Norte": mid - LANE_OFFSET,
    "Sur":   mid + LANE_OFFSET,
    "Oeste": mid - LANE_OFFSET,
    "Este":  mid + LANE_OFFSET
}

SIGN = {"Norte": -1, "Sur": 1, "Oeste": -1, "Este": 1}


class CarIcon:
    """
    Representa gráficamente un auto en la simulación.

    Métodos:
    - pos(): Devuelve la posición (x,y) actual.
    - destroy(): Elimina el ícono del canvas.
    - move(): Mueve el auto según su dirección, a menos que esté detenido.
    """

    def __init__(self, cv, img, x, y, d):
        self.cv = cv
        self.id = cv.create_image(x, y, image=img)
        self.d = d
        self.stopped = False
        self.has_crossed = False
        self.slot = None  # ← ← ← ¡ESTA LÍNEA FALTABA!

    def pos(self):
        return self.cv.coords(self.id)

    def destroy(self):
        self.cv.delete(self.id)

    def move(self):
        if self.stopped:
            return
        dx, dy = {
            "Norte": (0, CAR_SPEED),
            "Sur":   (0, -CAR_SPEED),
            "Este":  (-CAR_SPEED, 0),
            "Oeste": (CAR_SPEED, 0)
        }[self.d]
        self.cv.move(self.id, dx, dy)


class TrafficGUIReal:
    """
    GUI principal que maneja la simulación gráfica de tráfico.

    Componentes:
    - Canvas principal con calles, intersección, semáforos y autos.
    - Botón para iniciar la simulación.
    - Label para mostrar reporte final.
    """

    def __init__(self, root, ctrl, sim, pngs_by_dir, ciclos=5):
        self.ctrl = ctrl
        self.sim = sim
        self.ciclos = ciclos
        self.cars = []  # Lista de íconos de autos visibles

        root.title("Simulación de Tráfico Realista")
        self.cv = tk.Canvas(root, width=WIN, height=WIN, bg="gray")
        self.cv.pack()

        # Precargar imágenes de autos por dirección
        self.pngs_by_dir = {
            dir: [ImageTk.PhotoImage(Image.open(p).resize((ICON_SIZE, ICON_SIZE)))
                  for p in pngs_by_dir[dir]]
            for dir in ["Norte", "Sur", "Este", "Oeste"]
        }

        self.sem_gui = {}  # Contendrá los elementos gráficos de los semáforos
        self._draw_scene()

        # Botón para iniciar
        self.btn = ttk.Button(root, text="Iniciar Simulación", command=self._start)
        self.btn.pack(pady=10)

        # Label para mostrar reporte final
        self.rep = tk.Label(root, bg="white", font=("Courier", 10),
                            anchor="w", justify="left")
        self.rep.pack(fill="x")

        # Iniciar loop de actualización gráfica
        self._loop()

    def _loop(self):
        """
        Bucle principal de refresco de GUI:
        - Actualiza semáforos.
        - Spawnea autos.
        - Mueve autos.
        """
        self._paint_lights()
        self._spawn_cars()
        self._move_cars()

        # Asegura que semáforos queden visibles por encima de los autos
        for lights in self.sem_gui.values():
            for circle in lights.values():
                self.cv.tag_raise(circle)

        self.cv.after(30, self._loop)

    def _paint_lights(self):
        """
        Cambia el color de los óvalos de semáforo según estado real.
        """
        col_map = {"rojo": "red", "amarillo": "yellow", "verde": "green"}
        for d, lights in self.sem_gui.items():
            estado = self.ctrl.estado_semaforos[d]
            for c in ["rojo", "amarillo", "verde"]:
                self.cv.itemconfig(lights[c], fill="gray")
            self.cv.itemconfig(lights[estado], fill=col_map[estado])

    def _spawn_cars(self):
        """
        Crea íconos de autos cuando hay vehículos nuevos en la cola lógica.
        Controla la distancia entre autos al aparecer.
        """
        for d, carriles in self.sim.colas.items():
            for lane_index, lane in enumerate(carriles):
                # Revisa si ya hay un auto reciente
                recent = [c for c in self.cars if c.d == d and c.lane == lane_index and not c.has_crossed]
                allow_spawn = True
                if recent:
                    last = sorted(recent, key=lambda c: c.slot)[-1]
                    lx, ly = last.pos()
                    ref = -SPAWN_OUT if d in ("Norte", "Oeste") else WIN + SPAWN_OUT
                    dist = abs(ly - ref) if d in ("Norte", "Sur") else abs(lx - ref)
                    if dist < ICON_SIZE + GAP * 2:
                        allow_spawn = False
                if not allow_spawn:
                    continue

                # Crea un ícono para el primer vehículo que no tenga ícono
                for v in lane:
                    if hasattr(v, "icon"):
                        continue
                    if d == "Norte":
                        x, y = LANE_COORD[d], -SPAWN_OUT
                    elif d == "Sur":
                        x, y = LANE_COORD[d], WIN + SPAWN_OUT
                    elif d == "Este":
                        x, y = WIN + SPAWN_OUT, LANE_COORD[d]
                    else:
                        x, y = -SPAWN_OUT, LANE_COORD[d]
                    v.icon = CarIcon(self.cv, random.choice(self.pngs_by_dir[d]), x, y, d)
                    v.icon.lane = lane_index
                    self.cars.append(v.icon)
                    break

    def _move_cars(self):
        """
        Mueve todos los autos en pantalla:
        - Controla paradas en semáforo rojo.
        - Controla distancia de seguridad entre autos.
        - Detecta cuando cruzan y elimina los que salen de pantalla.
        """
        icon, gap = ICON_SIZE, GAP
        separation = icon + gap  # Espacio entre vehículos

        # Actualiza posición objetivo para cada auto
        for d, carriles in self.sim.colas.items():
            cola = [v for lane in carriles for v in lane if hasattr(v, "icon") and not v.icon.has_crossed]
            for i, v in enumerate(cola):
                ic = v.icon
                base = STOP_LINE[d]
                offset = SIGN[d] * i * separation

                if d in ("Norte", "Sur"):
                    ic.target_x = LANE_COORD[d]
                    ic.target_y = base + offset
                else:
                    ic.target_x = base + offset
                ic.slot = i  # Asignación correcta del slot
        # Este slot se usa luego para detener por distancia

            dead = []
            for ic in self.cars:
                x, y = ic.pos()
                d = ic.d

                # Detectar si cruzó completamente
                crossed = {
                    "Norte": y >= CROSS_LINE[d] + icon,
                    "Sur":   y <= CROSS_LINE[d] - icon,
                    "Este":  x <= CROSS_LINE[d] - icon,
                    "Oeste": x >= CROSS_LINE[d] + icon,
                }
                if crossed[d]:
                    ic.has_crossed = True

                # Determinar si debe detenerse (si no ha cruzado todavía)
                stop = False
                if not ic.has_crossed:
                    semaforo_rojo = self.ctrl.estado_semaforos[d] != "verde"

                    # Primer vehículo, se detiene en STOP_LINE si semáforo está rojo
                    if ic.slot is not None and ic.slot == 0 and semaforo_rojo:
                        if d == "Norte" and y < ic.target_y and y + CAR_SPEED >= ic.target_y:
                            stop = True
                        elif d == "Sur" and y > ic.target_y and y - CAR_SPEED <= ic.target_y:
                            stop = True
                        elif d == "Este" and x > ic.target_x and x - CAR_SPEED <= ic.target_x:
                            stop = True
                        elif d == "Oeste" and x < ic.target_x and x + CAR_SPEED >= ic.target_x:
                            stop = True
                    # Vehículos detrás: se detienen si están demasiado cerca del anterior
                    # Vehículos detrás: se detienen si están demasiado cerca del anterior
                    elif ic.slot is not None and ic.slot > 0:
                        prev = [c for c in self.cars if c.d == d and not c.has_crossed and c.slot == ic.slot - 1]
                        if prev:
                            front = prev[0]
                            fx, fy = front.pos()
                            dist = abs(y - fy) if d in ("Norte", "Sur") else abs(x - fx)
                            if dist < separation:
                                stop = True


                ic.stopped = stop
                ic.move()

                nx, ny = ic.pos()
                if nx < -SPAWN_OUT or nx > WIN + SPAWN_OUT or ny < -SPAWN_OUT or ny > WIN + SPAWN_OUT:
                    ic.destroy()
                    dead.append(ic)
            for ic in dead:
                self.cars.remove(ic)


    def _start(self):
        """
        Inicia:
        - Generación de autos.
        - Proceso de cruce de autos.
        - Controlador de semáforos.
        """
        self.btn.config(state="disabled")
        threading.Thread(target=self.sim.generar_vehiculos, daemon=True).start()
        threading.Thread(target=self.sim.procesar_vehiculos, daemon=True).start()
        threading.Thread(target=self._run_ctrl, daemon=True).start()

    def _run_ctrl(self):
        """
        Corre el controlador en ciclos y muestra el reporte al finalizar.
        """
        self.ctrl.iniciar_simulacion(ciclos=self.ciclos)
        self.sim.detener()
        self.rep.config(text=self.sim.reporte())

    def _draw_scene(self):
        """
        Dibuja:
        - Calles grises.
        - Líneas blancas.
        - Semáforos en cada dirección.
        - Fondos decorativos (bosques).
        """
        mid = WIN // 2
        road_w = 120

        # Calles principales
        self.cv.create_rectangle(mid - road_w // 2, 0, mid + road_w // 2, WIN, fill="dimgray")
        self.cv.create_rectangle(0, mid - road_w // 2, WIN, mid + road_w // 2, fill="dimgray")

        # Líneas punteadas
        for i in range(0, WIN, 40):
            self.cv.create_line(mid, i, mid, i + 20, fill="white", width=2)
            self.cv.create_line(i, mid, i + 20, mid, fill="white", width=2)

        # Franjas de cruce peatonal
        stripe_h = 5
        gap = 10
        for i in range(3):
            yN = CROSS_LINE["Norte"] - (i + 1) * (stripe_h + gap)
            self.cv.create_rectangle(mid - road_w // 2, yN, mid + road_w // 2, yN + stripe_h, fill="white")
            yS = CROSS_LINE["Sur"] + i * (stripe_h + gap)
            self.cv.create_rectangle(mid - road_w // 2, yS, mid + road_w // 2, yS + stripe_h, fill="white")
        for i in range(3):
            xW = CROSS_LINE["Oeste"] - (i + 1) * (stripe_h + gap)
            self.cv.create_rectangle(xW, mid - road_w // 2, xW + stripe_h, mid + road_w // 2, fill="white")
            xE = CROSS_LINE["Este"] + i * (stripe_h + gap)
            self.cv.create_rectangle(xE, mid - road_w // 2, xE + stripe_h, mid + road_w // 2, fill="white")

        # Semáforos (círculos)
        radius = 10
        offset = 25

        # Crea semáforos por dirección
        coords = {
            "Norte": (LANE_COORD["Norte"], STOP_LINE["Norte"] - 40),
            "Sur":   (LANE_COORD["Sur"],   STOP_LINE["Sur"] + 40),
            "Oeste": (STOP_LINE["Oeste"] - 40, LANE_COORD["Oeste"]),
            "Este":  (STOP_LINE["Este"] + 40,  LANE_COORD["Este"]),
        }

        for dir, (x, y) in coords.items():
            if dir in ["Norte", "Sur"]:
                self.sem_gui[dir] = {
                    "rojo": self.cv.create_oval(x - offset - radius, y - radius, x - offset + radius, y + radius, fill="gray"),
                    "amarillo": self.cv.create_oval(x - radius, y - radius, x + radius, y + radius, fill="gray"),
                    "verde": self.cv.create_oval(x + offset - radius, y - radius, x + offset + radius, y + radius, fill="gray"),
                }
            else:
                self.sem_gui[dir] = {
                    "rojo": self.cv.create_oval(x - radius, y - offset - radius, x + radius, y - offset + radius, fill="gray"),
                    "amarillo": self.cv.create_oval(x - radius, y - radius, x + radius, y + radius, fill="gray"),
                    "verde": self.cv.create_oval(x - radius, y + offset - radius, x + radius, y + offset + radius, fill="gray"),
                }

        # Fondo decorativo (bosques)
        forest1_img = Image.open("assets/forest-1.jpg")
        forest2_img = Image.open("assets/forest-2.jpg")

        block_size = mid - road_w // 2

        self.forest1 = ImageTk.PhotoImage(forest1_img.resize((block_size, block_size)))
        self.forest2 = ImageTk.PhotoImage(forest2_img.resize((block_size, block_size)))

        # Cuatro esquinas de la intersección
        self.cv.create_image(block_size // 2, block_size // 2, image=self.forest1)
        self.cv.create_image(WIN - block_size // 2, block_size // 2, image=self.forest2)
        self.cv.create_image(block_size // 2, WIN - block_size // 2, image=self.forest2)
        self.cv.create_image(WIN - block_size // 2, WIN - block_size // 2, image=self.forest1)
