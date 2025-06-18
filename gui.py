import tkinter as tk
from tkinter import ttk
import threading
import random
import time
from PIL import Image, ImageTk

ICON_SIZE = 30
GAP = 5
CAR_SPEED = 3
WIN = 800
SPAWN_OUT = 100

LANE_COORD = {
    "Norte": 380,
    "Sur":   420,
    "Oeste": 390,
    "Este":  410,
}

STOP_LINE = {"Norte": 340, "Sur": 460, "Oeste": 340, "Este": 460}
CROSS_LINE = {"Norte": 350, "Sur": 450, "Oeste": 350, "Este": 450}
SIGN = {"Norte": -1, "Sur": 1, "Oeste": -1, "Este": 1}


class CarIcon:
    def __init__(self, cv, img, x, y, d):
        self.cv = cv
        self.id = cv.create_image(x, y, image=img)
        self.d = d
        self.stopped = False
        self.has_crossed = False

    def pos(self): return self.cv.coords(self.id)
    def destroy(self): self.cv.delete(self.id)

    def move(self):
        if self.stopped: return
        dx, dy = {"Norte": (0, CAR_SPEED),
                  "Sur": (0, -CAR_SPEED),
                  "Este": (-CAR_SPEED, 0),
                  "Oeste": (CAR_SPEED, 0)}[self.d]
        self.cv.move(self.id, dx, dy)


class TrafficGUIReal:
    def __init__(self, root, ctrl, sim, png_paths, ciclos=5):
        self.ctrl, self.sim, self.ciclos = ctrl, sim, ciclos
        self.cars = []

        root.title("Simulación de Tráfico Realista")
        self.cv = tk.Canvas(root, width=WIN, height=WIN, bg="gray")
        self.cv.pack()

        self.pngs = [ImageTk.PhotoImage(Image.open(p).resize((ICON_SIZE, ICON_SIZE)))
                     for p in png_paths]

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
        self.cv.after(30, self._loop)

    def _paint_lights(self):
        col = {"rojo": "red", "amarillo": "yellow", "verde": "green"}
        for d, circ in self.sem_gui.items():
            self.cv.itemconfig(circ, fill=col[self.ctrl.estado_semaforos[d]])

    def _spawn_cars(self):
        for d, carriles in self.sim.colas.items():
            cola = [v for lane in carriles for v in lane]
            # validación: si último coche muy cerca del spawn point, no spawnear otro todavía
            recent = [c for c in self.cars if c.d == d and not c.has_crossed]
            allow_spawn = True
            if recent:
                last = sorted(recent, key=lambda c: c.slot)[-1]
                lx, ly = last.pos()
                if d in ("Norte", "Sur"):
                    ref = -SPAWN_OUT if d == "Norte" else WIN + SPAWN_OUT
                    if abs(ly - ref) < ICON_SIZE + GAP * 2:
                        allow_spawn = False
                else:
                    ref = -SPAWN_OUT if d == "Oeste" else WIN + SPAWN_OUT
                    if abs(lx - ref) < ICON_SIZE + GAP * 2:
                        allow_spawn = False

            if not allow_spawn:
                continue

            for v in cola:
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
                v.icon = CarIcon(self.cv, random.choice(self.pngs), x, y, d)
                self.cars.append(v.icon)
                break  # solo uno por tick

    def _move_cars(self):
        icon, gap = ICON_SIZE, GAP

        for d, carriles in self.sim.colas.items():
            cola = [v for lane in carriles for v in lane if not v.icon.has_crossed]
            for i, v in enumerate(cola):
                ic = v.icon
                base = STOP_LINE[d]
                offset = SIGN[d] * i * (icon + gap)
                if d in ("Norte", "Sur"):
                    ic.target_x = LANE_COORD[d]
                    ic.target_y = base + offset
                else:
                    ic.target_x = base + offset
                    ic.target_y = LANE_COORD[d]
                ic.slot = i

        dead = []
        for ic in self.cars:
            x, y = ic.pos()
            d = ic.d

            if d == "Norte" and y >= CROSS_LINE[d] + icon:
                ic.has_crossed = True
            elif d == "Sur" and y <= CROSS_LINE[d] - icon:
                ic.has_crossed = True
            elif d == "Este" and x <= CROSS_LINE[d] - icon:
                ic.has_crossed = True
            elif d == "Oeste" and x >= CROSS_LINE[d] + icon:
                ic.has_crossed = True

            stop = False
            if not ic.has_crossed:
                red = self.ctrl.estado_semaforos[d] != "verde"
                if ic.slot == 0 and red:
                    if d == "Norte" and y + CAR_SPEED >= ic.target_y: stop = True
                    elif d == "Sur" and y - CAR_SPEED <= ic.target_y: stop = True
                    elif d == "Este" and x - CAR_SPEED <= ic.target_x: stop = True
                    elif d == "Oeste" and x + CAR_SPEED >= ic.target_x: stop = True
                elif ic.slot > 0:
                    same_dir = [c for c in self.cars if c.d == d and not c.has_crossed and c.slot == ic.slot - 1]
                    if same_dir:
                        front = same_dir[0]
                        fx, fy = front.pos()
                        if d in ("Norte", "Sur"):
                            dist = abs(y - fy)
                        else:
                            dist = abs(x - fx)
                        if dist < icon + gap:
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
        self.cv.create_rectangle(350, 0, 450, WIN, fill="dimgray")
        self.cv.create_rectangle(0, 350, WIN, 450, fill="dimgray")
        for i in range(0, WIN, 40):
            self.cv.create_line(400, i, 400, i + 20, fill="white")
            self.cv.create_line(i, 400, i + 20, 400, fill="white")
        self.cv.create_rectangle(350, 340, 450, 350, fill="white")
        self.cv.create_rectangle(350, 450, 450, 460, fill="white")
        self.cv.create_rectangle(340, 350, 350, 450, fill="white")
        self.cv.create_rectangle(450, 350, 460, 450, fill="white")
        for y in (340, 460):
            self.cv.create_line(350, y, 450, y, fill="green")
        for x in (340, 460):
            self.cv.create_line(x, 350, x, 450, fill="green")
        coord = {"Norte": (400, 300), "Sur": (400, 500),
                 "Este": (500, 400), "Oeste": (300, 400)}
        for d, (x, y) in coord.items():
            self.sem_gui[d] = self.cv.create_oval(
                x - 15, y - 15, x + 15, y + 15, fill="gray")
