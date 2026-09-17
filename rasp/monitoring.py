#!/usr/bin/env python3
"""
RPi5 System Monitor
====================
Menampilkan status sistem Raspberry Pi 5 secara real-time di terminal:
suhu CPU, clock, voltase, throttle status, CPU usage per-core, RAM, swap,
disk, network I/O, uptime, dan load average.

Dependency:
    pip3 install psutil --break-system-packages

Cara pakai:
    python3 rpi5_monitor.py            # dashboard live (refresh tiap 2 detik)
    python3 rpi5_monitor.py --once     # cetak sekali lalu keluar
    python3 rpi5_monitor.py --interval 5   # ubah interval refresh
    python3 rpi5_monitor.py --log data.csv # sekaligus logging ke CSV
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

try:
    import psutil
except ImportError:
    sys.exit("psutil belum terinstall. Jalankan: pip3 install psutil --break-system-packages")


# ---------- Helper baca data RPi ----------

def run_vcgencmd(args):
    """Jalankan vcgencmd, return None kalau gagal (misal bukan di RPi)."""
    try:
        out = subprocess.check_output(["vcgencmd"] + args, stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def get_cpu_temp():
    # coba vcgencmd dulu, fallback ke thermal_zone
    raw = run_vcgencmd(["measure_temp"])
    if raw:
        try:
            return float(raw.replace("temp=", "").replace("'C", ""))
        except ValueError:
            pass
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000.0
    except FileNotFoundError:
        return None


def get_clock_freqs():
    result = {}
    for src in ["arm", "core", "v3d"]:
        raw = run_vcgencmd(["measure_clock", src])
        if raw and "=" in raw:
            try:
                hz = int(raw.split("=")[1])
                result[src] = hz / 1_000_000  # MHz
            except ValueError:
                pass
    return result


def get_voltage():
    raw = run_vcgencmd(["measure_volts", "core"])
    if raw:
        try:
            return float(raw.replace("volt=", "").replace("V", ""))
        except ValueError:
            pass
    return None


THROTTLE_BITS = {
    0: "Under-voltage terdeteksi (sekarang)",
    1: "ARM frequency capped (sekarang)",
    2: "Throttling aktif (sekarang)",
    3: "Soft temperature limit aktif (sekarang)",
    16: "Under-voltage pernah terjadi",
    17: "ARM frequency capping pernah terjadi",
    18: "Throttling pernah terjadi",
    19: "Soft temperature limit pernah tercapai",
}


def get_throttle_status():
    raw = run_vcgencmd(["get_throttled"])
    if not raw or "=" not in raw:
        return None
    try:
        val = int(raw.split("=")[1], 16)
    except ValueError:
        return None
    active = [msg for bit, msg in THROTTLE_BITS.items() if val & (1 << bit)]
    return val, active


def get_disk_usage(path="/"):
    total, used, free = shutil.disk_usage(path)
    return {
        "total_gb": total / (1024 ** 3),
        "used_gb": used / (1024 ** 3),
        "free_gb": free / (1024 ** 3),
        "percent": used / total * 100,
    }


def bytes_to_human(n):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def get_uptime():
    boot = psutil.boot_time()
    delta = time.time() - boot
    days, rem = divmod(int(delta), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}h {hours}j {minutes}m"


# ---------- Kumpulkan semua data jadi satu dict ----------

def collect_stats(net_prev, t_prev):
    now = time.time()
    net = psutil.net_io_counters()
    dt = max(now - t_prev, 1e-6)
    net_speed = {
        "up_bps": (net.bytes_sent - net_prev.bytes_sent) / dt,
        "down_bps": (net.bytes_recv - net_prev.bytes_recv) / dt,
    }

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    throttle = get_throttle_status()

    stats = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_temp_c": get_cpu_temp(),
        "cpu_percent_total": psutil.cpu_percent(interval=None),
        "cpu_percent_per_core": psutil.cpu_percent(interval=None, percpu=True),
        "clocks_mhz": get_clock_freqs(),
        "voltage_v": get_voltage(),
        "throttle_raw": throttle[0] if throttle else None,
        "throttle_flags": throttle[1] if throttle else [],
        "ram_total_gb": mem.total / (1024 ** 3),
        "ram_used_gb": mem.used / (1024 ** 3),
        "ram_percent": mem.percent,
        "swap_total_gb": swap.total / (1024 ** 3),
        "swap_used_gb": swap.used / (1024 ** 3),
        "swap_percent": swap.percent,
        "disk": get_disk_usage("/"),
        "net_up": net_speed["up_bps"],
        "net_down": net_speed["down_bps"],
        "load_avg": os.getloadavg(),
        "uptime": get_uptime(),
        "process_count": len(psutil.pids()),
    }
    return stats, net, now


# ---------- Tampilan ----------

def render(stats):
    lines = []
    lines.append("=" * 52)
    lines.append(f" RPi5 Monitor — {stats['timestamp']}")
    lines.append("=" * 52)

    temp = stats["cpu_temp_c"]
    if temp is not None:
        warn = " ⚠ PANAS" if temp >= 75 else ""
        lines.append(f"Suhu CPU     : {temp:.1f}°C{warn}")
    else:
        lines.append("Suhu CPU     : tidak terbaca (bukan di RPi?)")

    if stats["voltage_v"] is not None:
        lines.append(f"Voltase Core : {stats['voltage_v']:.4f} V")

    if stats["clocks_mhz"]:
        clk = ", ".join(f"{k}={v:.0f}MHz" for k, v in stats["clocks_mhz"].items())
        lines.append(f"Clock        : {clk}")

    if stats["throttle_raw"] is not None:
        flags = stats["throttle_flags"]
        status = "Normal" if not flags else " | ".join(flags)
        lines.append(f"Throttle     : {status} (raw=0x{stats['throttle_raw']:x})")

    lines.append("-" * 52)
    lines.append(f"CPU Total    : {stats['cpu_percent_total']:.1f}%")
    per_core = " ".join(f"C{i}:{p:4.0f}%" for i, p in enumerate(stats["cpu_percent_per_core"]))
    lines.append(f"Per-core     : {per_core}")
    la = stats["load_avg"]
    lines.append(f"Load Avg     : {la[0]:.2f}, {la[1]:.2f}, {la[2]:.2f} (1/5/15 min)")

    lines.append("-" * 52)
    lines.append(
        f"RAM          : {stats['ram_used_gb']:.2f}/{stats['ram_total_gb']:.2f} GB "
        f"({stats['ram_percent']:.1f}%)"
    )
    lines.append(
        f"Swap         : {stats['swap_used_gb']:.2f}/{stats['swap_total_gb']:.2f} GB "
        f"({stats['swap_percent']:.1f}%)"
    )

    d = stats["disk"]
    lines.append(
        f"Disk (/)     : {d['used_gb']:.1f}/{d['total_gb']:.1f} GB "
        f"({d['percent']:.1f}%), free {d['free_gb']:.1f} GB"
    )

    lines.append("-" * 52)
    lines.append(
        f"Network      : ↑ {bytes_to_human(stats['net_up'])}/s   "
        f"↓ {bytes_to_human(stats['net_down'])}/s"
    )
    lines.append(f"Uptime       : {stats['uptime']}")
    lines.append(f"Processes    : {stats['process_count']}")
    lines.append("=" * 52)
    return "\n".join(lines)


# ---------- CSV logging ----------

def init_csv(path):
    exists = os.path.isfile(path)
    f = open(path, "a", newline="")
    writer = csv.writer(f)
    if not exists:
        writer.writerow([
            "timestamp", "cpu_temp_c", "cpu_percent_total", "voltage_v",
            "throttle_raw", "ram_percent", "swap_percent", "disk_percent",
            "net_up_bps", "net_down_bps", "load1", "load5", "load15",
        ])
    return f, writer


def log_row(writer, stats):
    la = stats["load_avg"]
    writer.writerow([
        stats["timestamp"], stats["cpu_temp_c"], stats["cpu_percent_total"],
        stats["voltage_v"], stats["throttle_raw"], stats["ram_percent"],
        stats["swap_percent"], stats["disk"]["percent"],
        f"{stats['net_up']:.0f}", f"{stats['net_down']:.0f}",
        la[0], la[1], la[2],
    ])


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description="Monitor sistem Raspberry Pi 5")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval refresh (detik), default 2")
    parser.add_argument("--once", action="store_true", help="Cetak sekali lalu keluar (cocok untuk cron)")
    parser.add_argument("--log", metavar="FILE.csv", help="Simpan tiap sample ke file CSV")
    args = parser.parse_args()

    csv_file, csv_writer = (None, None)
    if args.log:
        csv_file, csv_writer = init_csv(args.log)

    net_prev = psutil.net_io_counters()
    t_prev = time.time()
    psutil.cpu_percent(percpu=True)  # warm-up, sample pertama selalu 0

    try:
        while True:
            time.sleep(args.interval if not args.once else 0.2)
            stats, net_prev, t_prev = collect_stats(net_prev, t_prev)

            if not args.once:
                os.system("clear")
            print(render(stats))

            if csv_writer:
                log_row(csv_writer, stats)
                csv_file.flush()

            if args.once:
                break
    except KeyboardInterrupt:
        print("\nDihentikan.")
    finally:
        if csv_file:
            csv_file.close()


if __name__ == "__main__":
    main()
