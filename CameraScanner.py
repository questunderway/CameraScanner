import socket
import threading
from queue import Queue
import ipaddress
import time
import os
from tqdm import tqdm

socket.setdefaulttimeout(0.25)

def scan(ip, port, results_file=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, port))
            sock.send(b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n')
            response = sock.recv(4096).decode(errors='ignore')
            if 'HTTP' in response and '<title>WEB SERVICE</title>' in response:
                brand = None
                server_header = None
                for line in response.split('\r\n'):
                    if line.lower().startswith('server:'):
                        server_header = line.split(':', 1)[1].strip()
                        break
                auth_header = None
                for line in response.split('\r\n'):
                    if line.lower().startswith('www-authenticate:'):
                        auth_header = line.split(':', 1)[1].strip()
                        break
                patterns = [
                    ("Dahua", ["dahua", "DH-", "DVRDVS-Webs"], [server_header, auth_header, response]),
                    ("Hikvision", ["hikvision", "HIKVISION", "App-webs"], [server_header, auth_header, response]),
                    ("Axis", ["axis", "AXIS"], [server_header, auth_header, response]),
                    ("TP-Link", ["tp-link", "TP-LINK"], [server_header, auth_header, response]),
                    ("Foscam", ["foscam", "FOSCAM"], [server_header, auth_header, response]),
                    ("Provision", ["provision", "Provision"], [server_header, auth_header, response]),
                    ("Milesight", ["milesight", "Milesight"], [server_header, auth_header, response]),
                    ("UNV", ["uniview", "UNV"], [server_header, auth_header, response]),
                    ("Generic", ["webcam", "ip camera", "network camera"], [response]),
                ]
                for brand_name, keywords, sources in patterns:
                    for src in sources:
                        if src:
                            for kw in keywords:
                                if kw.lower() in src.lower():
                                    brand = brand_name
                                    break
                        if brand:
                            break
                    if brand:
                        break
                if port == 8080:
                    cam_url = f"http://{ip}:{port}"
                else:
                    cam_url = f"http://{ip}"
                if brand:
                    output_line = f"{cam_url} | Brand: {brand}"
                else:
                    output_line = f"{cam_url}"
                try:
                    with open('cameras_found.txt', 'r') as f:
                        if cam_url in f.read():
                            return True
                except FileNotFoundError:
                    pass
                with open('cameras_found.txt', 'a') as f:
                    f.write(output_line + "\n")
                return True
    except Exception as e:
        pass
    return False

def execute(queue, results_file=None, pbar=None):
    while True:
        ip, port = queue.get()
        scan(ip, port, results_file)
        if pbar:
            pbar.update(1)
        queue.task_done()

def generate_ip_range(start_ip, end_ip):
    start = int(ipaddress.IPv4Address(start_ip))
    end = int(ipaddress.IPv4Address(end_ip))
    for ip_int in range(start, end + 1):
        yield str(ipaddress.IPv4Address(ip_int))

def run_tool(start_ip=None, end_ip=None, ip_list=None, fast_mode=False, single_ip=None, results_file_path=None, max_threads=None, custom_targets=None):
    if max_threads is not None:
        thread_count = max_threads
    elif fast_mode:
        thread_count = 300
        socket.setdefaulttimeout(0.1)
    else:
        thread_count = 100
        socket.setdefaulttimeout(0.25)
    if fast_mode:
        socket.setdefaulttimeout(0.1)
    else:
        socket.setdefaulttimeout(0.25)
    queue = Queue()
    start_time = time.time()
    results_file = open(results_file_path, 'a') if results_file_path else None
    if custom_targets is not None:
        targets = custom_targets
    else:
        targets = []
        if single_ip:
            targets.append((single_ip, 80))
            targets.append((single_ip, 8080))
        elif ip_list:
            for ip in ip_list:
                targets.append((ip, 80))
                targets.append((ip, 8080))
        elif start_ip and end_ip:
            for ip in generate_ip_range(start_ip, end_ip):
                targets.append((ip, 80))
                targets.append((ip, 8080))
        else:
            print("No valid IP input provided.")
            if results_file:
                results_file.close()
            return
    pbar = tqdm(
        total=len(targets),
        desc="Scanning",
        ncols=100,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    )
    for _ in range(thread_count):
        thread = threading.Thread(target=execute, args=(queue, results_file, pbar))
        thread.daemon = True
        thread.start()
    for t in targets:
        queue.put(t)
    queue.join()
    pbar.close()
    elapsed_time = time.time() - start_time
    print(f'Time taken: {elapsed_time:.2f} seconds')
    if results_file:
        results_file.close()
        print(f"Results saved to {results_file_path}")

def main_menu():
    while True:
        try:
            max_threads = int(input("Enter max threads (default 300): ") or "300")
            if max_threads < 1:
                print("Max threads must be at least 1. Using default 300.")
                max_threads = 300
        except Exception:
            print("Invalid input. Using default 300.")
            max_threads = 300
        print("\nSelect scan mode:")
        print("1. Fast Scan (IP Range, more threads)")
        print("2. IPs from StartIP.txt to EndIP.txt")
        print("0. Exit")
        choice = input("Enter your choice: ").strip()
        if choice == '1':
            start_ip = input('Start IP Address: ')
            end_ip = input('End IP Address: ')
            run_tool(start_ip=start_ip, end_ip=end_ip, fast_mode=True, results_file_path='cameras_found.txt', max_threads=max_threads)
        elif choice == '2':
            start_ip_file = 'StartIP.txt'
            end_ip_file = 'EndIP.txt'
            created = False
            if not os.path.exists(start_ip_file):
                with open(start_ip_file, 'w') as f:
                    f.write('')
                print(f"Created {start_ip_file}. Please enter the start IP in this file and rerun the scan.")
                created = True
            if not os.path.exists(end_ip_file):
                with open(end_ip_file, 'w') as f:
                    f.write('')
                print(f"Created {end_ip_file}. Please enter the end IP in this file and rerun the scan.")
                created = True
            if created:
                return
            with open(start_ip_file, 'r') as f:
                start_ips = [line.strip() for line in f if line.strip()]
            with open(end_ip_file, 'r') as f:
                end_ips = [line.strip() for line in f if line.strip()]
            if not start_ips or not end_ips:
                print(f"Please make sure both {start_ip_file} and {end_ip_file} contain valid IP addresses.")
                return
            if len(start_ips) != len(end_ips):
                print(f"Error: {start_ip_file} and {end_ip_file} must have the same number of lines (ranges).")
                return
            all_targets = []
            for start_ip, end_ip in zip(start_ips, end_ips):
                for ip in generate_ip_range(start_ip, end_ip):
                    all_targets.append((ip, 80))
                    all_targets.append((ip, 8080))
            print(f"Scanning {len(all_targets)//2} IPs across {len(start_ips)} ranges...")
            run_tool(ip_list=None, fast_mode=True, results_file_path='cameras_found.txt', max_threads=max_threads, custom_targets=all_targets)
        elif choice == '0':
            print('Exiting.')
            break
        else:
            print('Invalid choice. Try again.')

if __name__ == "__main__":
    try:
        main_menu()
    except (KeyboardInterrupt, SystemExit):
        print('\nExiting.')
        exit(0)
