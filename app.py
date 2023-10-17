from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import subprocess
import time
import urllib.request
import uuid
import datetime



app = Flask(__name__)

# Fungsi untuk membaca data dari file JSON
def load_data():
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []
    return data

# Fungsi untuk menulis data ke file JSON
def write_data(data):
    with open("data.json", "w") as file:
        json.dump(data, file, indent=4)

# Fungsi untuk cek koneksi internet
def cek_koneksi_internet():
    try:
        urllib.request.urlopen('http://www.google.com', timeout=1)
        return True
    except urllib.request.URLError:
        return False

# Fungsi untuk membaca alamat IP dari file JSON
def baca_alamat_ip(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data



# Fungsi untuk memantau alamat IP dari file JSON
# Fungsi untuk memantau alamat IP dari file JSON dan menyimpan data ke dalam log.json
def monitor_ip(file_path):
    alamat_ip = baca_alamat_ip(file_path)
    status_devices = {}  # Dictionary untuk menyimpan status setiap perangkat
    while True:
        for device in alamat_ip:
            ip_address = device.get("ip_addresses", [])[0]
            device_name = device.get("name", "Unknown Device")
            status = cek_ping(ip_address)

            # Periksa apakah alamat IP berada dalam dictionary status_devices
            if ip_address not in status_devices:
                # Jika tidak ada, inisialisasi dictionary untuk alamat IP tersebut
                status_devices[ip_address] = {
                    "name": device_name,
                    "status": None,
                    "uptime": None,
                    "downtime": None
                }

            if status:
                # Jika alamat IP sebelumnya dalam status "down", catat waktu uptime
                if status_devices[ip_address]["status"] == "down":
                    status_devices[ip_address]["uptime"] = time.time()
                    # Jika terdapat waktu downtime sebelumnya, hitung durasi downtime
                    if status_devices[ip_address]["downtime"]:
                        downtime_start = status_devices[ip_address]["downtime"]
                        downtime_end = status_devices[ip_address]["uptime"]
                        downtime_duration = downtime_end - downtime_start
                        status_devices[ip_address]["downtime"] = None
                        # Simpan data downtime ke dalam log.json
                        save_downtime_to_log(ip_address, device_name, downtime_start, downtime_end, downtime_duration)
                status_devices[ip_address]["status"] = "up"
            else:
                # Jika alamat IP sebelumnya dalam status "up", catat waktu downtime
                if status_devices[ip_address]["status"] == "up":
                    status_devices[ip_address]["downtime"] = time.time()

                status_devices[ip_address]["status"] = "down"

            print(f"Device {status_devices[ip_address]['name']} with IP address {ip_address} is {status_devices[ip_address]['status']}.")

        time.sleep(10)  # Periksa setiap 10 detik

# Fungsi untuk menyimpan data downtime ke dalam log.json dengan format tanggal, jam, menit, detik
def save_downtime_to_log(ip_address, device_name, start_time, end_time, duration):
    # Menghitung durasi dalam format jam, menit, detik
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Mendapatkan tanggal dan waktu dalam format yang diinginkan
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "ip_address": ip_address,
        "device_name": device_name,
        "start_time": time.strftime("%H:%M:%S", time.gmtime(start_time)),  # Format jam, menit, detik
        "end_time": time.strftime("%H:%M:%S", time.gmtime(end_time)),      # Format jam, menit, detik
        "duration": f"{int(hours)} jam {int(minutes)} menit {int(seconds)} detik",
        "date": current_datetime  # Tambahkan tanggal ke dalam log
    }
    
    try:
        with open("log.json", "r") as log_file:
            log_data = json.load(log_file)
    except FileNotFoundError:
        log_data = []
    
    log_data.append(log_entry)

    with open("log.json", "w") as log_file:
        json.dump(log_data, log_file, indent=4)

# Fungsi untuk melakukan ping ke alamat IP dan mengembalikan hasilnya
def cek_ping(ip):
    try:
        result = subprocess.run(['ping', '-c', '3', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if "3 packets transmitted, 3 received, 0% packet loss" in result.stdout:
            return True
        else:
            return False
    except subprocess.TimeoutExpired:
        print("Ping timeout expired.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/clear_log', methods=['DELETE'])
def clear_log():
    try:
        # Mengosongkan file log.json
        with open("log.json", "w") as log_file:
            log_file.write("[]")
        return jsonify({"message": "Log cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
# Fungsi untuk menghapus perangkat berdasarkan ID
@app.route('/delete/<string:id>', methods=['DELETE'])
def delete_device(id):
    devices = load_data()
    device_to_delete = None
    for device in devices:
        if device["id"] == id:
            device_to_delete = device
            break
    if device_to_delete:
        devices.remove(device_to_delete)
        write_data(devices)  # Tulis kembali data ke file JSON setelah menghapus perangkat
    return jsonify({"message": "Device deleted successfully"})  # Menyertakan respons JSON yang memberi tahu bahwa perangkat telah dihapus

# Fungsi untuk mendapatkan status perangkat dalam format JSON
@app.route('/status')
def get_status():
    devices = load_data()
    status_devices = {}
    for device in devices:
        ip_address = device.get("ip_addresses", [])[0]
        device_name = device.get("name", "Unknown Device")
        status = "up" if cek_ping(ip_address) else "down"
        status_devices[ip_address] = {
            "name": device_name,
            "status": status
        }
    return jsonify(status_devices)

@app.route('/')
def index():
    devices = load_data()
    # Baca data dari log.json
    try:
        with open("log.json", "r") as log_file:
            log_data = json.load(log_file)
    except FileNotFoundError:
        log_data = []
    # Kirim data dari data.json dan log.json sebagai konteks ke template index.html
    return render_template('index.html', devices=devices, log_data=log_data)

# Fungsi untuk menambahkan perangkat baru
@app.route('/add', methods=['POST'])
def add_device():
    ip_address = request.form['ip_address']
    name = request.form['name']
    new_device = {
        "id": str(uuid.uuid4()),  # Membuat ID unik menggunakan UUID
        "ip_addresses": [ip_address],
        "name": name
    }
    devices = load_data()
    devices.append(new_device)
    write_data(devices)
    return redirect(url_for('index'))

# Jalankan fungsi monitor_ip dalam thread terpisah agar tidak memblokir aplikasi Flask
import threading
monitor_thread = threading.Thread(target=monitor_ip, args=("data.json",))
monitor_thread.start()

# Jalankan aplikasi Flask
if __name__ == '__main__':
    app.run(host="10.10.10.4", port=8000, debug=True)
