import tkinter as tk
from tkinter import ttk
import threading
import random
from PIL import Image, ImageTk

WIN = 1000
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
        self.cv.after(30, self._loop)

    def _paint_lights(self):
        col = {"rojo": "red", "amarillo": "yellow", "verde": "green"}
        for d, circ in self.sem_gui.items():
            self.cv.itemconfig(circ, fill=col[self.ctrl.estado_semaforos[d]])

    def _spawn_cars(self):
        for d, carriles in self.sim.colas.items():
            cola = [v for lane in carriles for v in lane]
            recent = [c for c in self.cars if c.d == d and not c.has_crossed]
            allow_spawn = True
            if recent:
                last = sorted(recent, key=lambda c: c.slot)[-1]
                lx, ly = last.pos()
                ref = -SPAWN_OUT if d in ("Norte", "Oeste") else WIN + SPAWN_OUT
                if d in ("Norte", "Sur"):
                    if abs(ly - ref) < ICON_SIZE + GAP * 2:
                        allow_spawn = False
                else:
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
                # → Usa la imagen correcta:
                v.icon = CarIcon(self.cv, random.choice(self.pngs_by_dir[d]), x, y, d)
                self.cars.append(v.icon)
                break

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
                    if d == "Norte" and y < STOP_LINE[d] and y + CAR_SPEED >= ic.target_y:
                        stop = True
                    elif d == "Sur" and y > STOP_LINE[d] and y - CAR_SPEED <= ic.target_y:
                        stop = True
                    elif d == "Este" and x > STOP_LINE[d] and x - CAR_SPEED <= ic.target_x:
                        stop = True
                    elif d == "Oeste" and x < STOP_LINE[d] and x + CAR_SPEED >= ic.target_x:
                        stop = True

                elif ic.slot > 0:
                    same_dir = [c for c in self.cars if c.d == d and not c.has_crossed and c.slot == ic.slot - 1]
                    if same_dir:
                        front = same_dir[0]
                        fx, fy = front.pos()
                        dist = abs(y - fy) if d in ("Norte", "Sur") else abs(x - fx)
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
        mid = WIN // 2
        road_w = 120

        self.cv.create_rectangle(mid - road_w // 2, 0, mid + road_w // 2, WIN, fill="dimgray")
        self.cv.create_rectangle(0, mid - road_w // 2, WIN, mid + road_w // 2, fill="dimgray")

        for i in range(0, WIN, 40):
            self.cv.create_line(mid, i, mid, i + 20, fill="white", width=2)
            self.cv.create_line(i, mid, i + 20, mid, fill="white", width=2)

        zebra_w = 60
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

        coord = {
            "Norte": (mid, STOP_LINE["Norte"] - 40),
            "Sur": (mid, STOP_LINE["Sur"] + 40),
            "Oeste": (STOP_LINE["Oeste"] - 40, mid),
            "Este": (STOP_LINE["Este"] + 40, mid)
        }
        for d, (x, y) in coord.items():
            self.sem_gui[d] = self.cv.create_oval(x - 15, y - 15, x + 15, y + 15, fill="gray")
