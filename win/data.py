from pymavlink import mavutil
import serial.tools.list_ports
import sys
import csv
import json
import os
from datetime import datetime, timezone

BAUD_RATE = 57600
OUTPUT_DIR = "logs"


def scan_ports():
    """Scan semua port serial yang tersedia dan tampilkan ke user."""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("Tidak ada port serial terdeteksi. Pastikan radio telemetry sudah terpasang.")
        sys.exit(1)

    print("Port serial yang terdeteksi:")
    for i, port in enumerate(ports):
        print(f"  [{i}] {port.device} - {port.description}")

    return ports


def pilih_port(ports):
    """Minta user pilih port dari hasil scan."""
    if len(ports) == 1:
        pilihan = ports[0].device
        print(f"Hanya ada 1 port, otomatis pakai: {pilihan}")
        return pilihan

    while True:
        idx = input(f"Pilih index port (0-{len(ports)-1}): ").strip()
        if idx.isdigit() and 0 <= int(idx) < len(ports):
            return ports[int(idx)].device
        print("Input tidak valid, coba lagi.")


def request_battery_status(master, interval_hz=1):
    """Minta board mengirim BATTERY_STATUS secara eksplisit.

    Sebagian firmware/board tidak menyertakan BATTERY_STATUS di stream
    default, jadi perlu diminta manual lewat MAV_CMD_SET_MESSAGE_INTERVAL.
    Kalau board/firmware memang tidak mendukung message ini, request ini
    tidak akan memunculkan error — BATTERY_STATUS-nya tetap tidak akan
    pernah muncul, dan itu jadi konfirmasi bahwa SYS_STATUS satu-satunya
    sumber data baterai yang tersedia.
    """
    interval_us = int(1_000_000 / interval_hz)
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
        mavutil.mavlink.MAVLINK_MSG_ID_BATTERY_STATUS,
        interval_us,
        0, 0, 0, 0, 0
    )
    print(f"Request BATTERY_STATUS terkirim (target {interval_hz} Hz)...")


def main():
    ports = scan_ports()
    com_port = pilih_port(ports)  # <-- variabel COM port, dipakai buat koneksi

    print(f"\nMenghubungkan ke {com_port} @ {BAUD_RATE} baud...")
    master = mavutil.mavlink_connection(com_port, baud=BAUD_RATE)

    print("Menunggu heartbeat...")
    master.wait_heartbeat()
    print(f"Heartbeat OK (system {master.target_system}, component {master.target_component})")

    request_battery_status(master)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(OUTPUT_DIR, f"mavlink_log_{session_time}.csv")

    print(f"Mulai logging semua message ke '{output_csv}'... (Ctrl+C untuk berhenti)\n")

    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "msg_type", "data_json"])

        try:
            while True:
                msg = master.recv_match(blocking=True)
                if msg is None:
                    continue

                # BAD_DATA = paket korup/gagal parse, bukan data valid, dilewati saja
                if msg.get_type() == "BAD_DATA":
                    continue

                timestamp = datetime.now(timezone.utc).isoformat()
                msg_type = msg.get_type()
                data_json = json.dumps(msg.to_dict())

                writer.writerow([timestamp, msg_type, data_json])
                f.flush()  # langsung tulis ke disk, biar data nggak hilang kalau script crash/terhenti paksa

                print(timestamp, msg_type, data_json)
        except KeyboardInterrupt:
            print(f"\nDihentikan oleh user. Data tersimpan di '{output_csv}'.")


if __name__ == "__main__":
    main()