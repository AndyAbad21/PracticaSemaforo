import tkinter as tk
from tkinter import ttk
import threading
import random
from PIL import Image, ImageTk

WIN = 700
ICON_SIZE = 40
GAP = 5
CAR_SPEED = 3
SPAWN_OUT = 100

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
        dx, dy = {"Norte": (0, CAR_SPEED),
                  "Sur": (0, -CAR_SPEED),
                  "Este": (-CAR_SPEED, 0),
                  "Oeste": (CAR_SPEED, 0)}[self.d]
        self.cv.move(self.id, dx, dy)


class TrafficGUIReal:
    def __init__(self, root, ctrl, sim, pngs_by_dir, ciclos=5):
        self.ctrl, self.sim, self.ciclos = ctrl, sim, ciclos
        self.cars = []

        root.title("Simulación de Tráfico Realista")
        self.cv = tk.Canvas(root, width=WIN, height=WIN, bg="gray")
        self.cv.pack()

        # Pre-carga por dirección:
        self.pngs_by_dir = {
            dir: [ImageTk.PhotoImage(Image.open(p).resize((ICON_SIZE, ICON_SIZE)))
                  for p in pngs_by_dir[dir]]
            for dir in ["Norte", "Sur", "Este", "Oeste"]
        }

        self.sem_gui = {}
        self._draw_scene()

        self.btn = ttk.Button(root, text="Iniciar Simulación", command=self._start)
        self.btn.pack(pady=10)

        self.rep = tk.Label(root, bg="white", font=("Courier", 10),
                            anchor="w", justify="left")
        self.rep.pack(fill="x")

        self._loop()

    def _loop(self):
        self._paint_lights()
        self._spawn_cars()
        self._move_cars()
        
        # ---> ASEGURAR semáforos encima de todo
        for lights in self.sem_gui.values():
            for circle in lights.values():
                self.cv.tag_raise(circle)
                
        self.cv.after(30, self._loop)

    def _paint_lights(self):
        col_map = {"rojo": "red", "amarillo": "yellow", "verde": "green"}
        for d, lights in self.sem_gui.items():
            estado = self.ctrl.estado_semaforos[d]
            # Apaga todas primero
            for c in ["rojo", "amarillo", "verde"]:
                self.cv.itemconfig(lights[c], fill="gray")
            # Enciende solo la correcta
            self.cv.itemconfig(lights[estado], fill=col_map[estado])

    def _spawn_cars(self):
        for d, carriles in self.sim.colas.items():
            for lane_index, lane in enumerate(carriles):
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
        icon, gap = ICON_SIZE, GAP
        separation = icon + gap  # Espacio entre vehículos

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
                    ic.target_y = LANE_COORD[d]
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
        self.btn.config(state="disabled")
        threading.Thread(target=self.sim.generar_vehiculos, daemon=True).start()
        threading.Thread(target=self.sim.procesar_vehiculos, daemon=True).start()
        threading.Thread(target=self._run_ctrl, daemon=True).start()

    def _run_ctrl(self):
        self.ctrl.iniciar_simulacion(ciclos=self.ciclos)
        self.sim.detener()
        self.rep.config(text=self.sim.reporte())

    def _draw_scene(self):
        mid = WIN // 2
        road_w = 120

        # --- Fondo gris con vías ---
        self.cv.create_rectangle(mid - road_w // 2, 0, mid + road_w // 2, WIN, fill="dimgray")
        self.cv.create_rectangle(0, mid - road_w // 2, WIN, mid + road_w // 2, fill="dimgray")

        for i in range(0, WIN, 40):
            self.cv.create_line(mid, i, mid, i + 20, fill="white", width=2)
            self.cv.create_line(i, mid, i + 20, mid, fill="white", width=2)

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

        # ---- Semáforos ----
        radius = 10
        offset = 25

        self.sem_gui = {}

        nx = LANE_COORD["Norte"]
        ny = STOP_LINE["Norte"] - 40
        self.sem_gui["Norte"] = {
            "rojo": self.cv.create_oval(nx - offset - radius, ny - radius, nx - offset + radius, ny + radius, fill="gray"),
            "amarillo": self.cv.create_oval(nx - radius, ny - radius, nx + radius, ny + radius, fill="gray"),
            "verde": self.cv.create_oval(nx + offset - radius, ny - radius, nx + offset + radius, ny + radius, fill="gray"),
        }

        sx = LANE_COORD["Sur"]
        sy = STOP_LINE["Sur"] + 40
        self.sem_gui["Sur"] = {
            "rojo": self.cv.create_oval(sx - offset - radius, sy - radius, sx - offset + radius, sy + radius, fill="gray"),
            "amarillo": self.cv.create_oval(sx - radius, sy - radius, sx + radius, sy + radius, fill="gray"),
            "verde": self.cv.create_oval(sx + offset - radius, sy - radius, sx + offset + radius, sy + radius, fill="gray"),
        }

        wx = STOP_LINE["Oeste"] - 40
        wy = LANE_COORD["Oeste"]
        self.sem_gui["Oeste"] = {
            "rojo": self.cv.create_oval(wx - radius, wy - offset - radius, wx + radius, wy - offset + radius, fill="gray"),
            "amarillo": self.cv.create_oval(wx - radius, wy - radius, wx + radius, wy + radius, fill="gray"),
            "verde": self.cv.create_oval(wx - radius, wy + offset - radius, wx + radius, wy + offset + radius, fill="gray"),
        }

        ex = STOP_LINE["Este"] + 40
        ey = LANE_COORD["Este"]
        self.sem_gui["Este"] = {
            "rojo": self.cv.create_oval(ex - radius, ey - offset - radius, ex + radius, ey - offset + radius, fill="gray"),
            "amarillo": self.cv.create_oval(ex - radius, ey - radius, ex + radius, ey + radius, fill="gray"),
            "verde": self.cv.create_oval(ex - radius, ey + offset - radius, ex + radius, ey + offset + radius, fill="gray"),
        }

        # Carga base sin tamaño fijo
        forest1_img = Image.open("assets/forest-1.jpg")
        forest2_img = Image.open("assets/forest-2.jpg")

        # Cada bloque libre es: 0 a cruce (Norte/Oeste) o cruce a fin (Sur/Este)
        block_size = mid - road_w // 2

        # Redimensiona al tamaño de bloque
        self.forest1 = ImageTk.PhotoImage(forest1_img.resize((block_size, block_size)))
        self.forest2 = ImageTk.PhotoImage(forest2_img.resize((block_size, block_size)))

        # Superior izquierda
        self.cv.create_image(block_size // 2, block_size // 2, image=self.forest1)
        # Superior derecha
        self.cv.create_image(WIN - block_size // 2, block_size // 2, image=self.forest2)
        # Inferior izquierda
        self.cv.create_image(block_size // 2, WIN - block_size // 2, image=self.forest2)
        # Inferior derecha
        self.cv.create_image(WIN - block_size // 2, WIN - block_size // 2, image=self.forest1)
