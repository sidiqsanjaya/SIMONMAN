from datetime import datetime
import signal
import sys
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from models import *
import uci_cmd as uci
import netdata as net
from databases import db
import socket
import os
import subprocess
import concurrent.futures
max_threads = 5

def get_latest_bandwidth_data():
    latest_data = db.session.query(
        BandwidthStatus.eth_type,
        BandwidthStatus.speed_send,
        BandwidthStatus.speed_recv,
        func.max(BandwidthStatus.timestamp).label('latest_timestamp')
    ).group_by(BandwidthStatus.eth_type).all()

    latest_bandwidth_data = []
    for data in latest_data:
        latest_bandwidth_data.append({
            'eth_type': data.eth_type,
            'speed_send': data.speed_send,
            'speed_recv': data.speed_recv,
            'timestamp': data.latest_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    for item in latest_bandwidth_data:
        item['speed_send'] = abs(item['speed_send'])
    return latest_bandwidth_data

def get_latest_system_data():
    latest_data = db.session.query(
        System.cpu_idle,
        System.ram_total,
        System.ram_free,
        System.conntrack,
        System.userol,
        System.userhs,
        func.max(System.timestamp).label('latest_timestamp')
    ).all()

    latest_System_data = []
    for data in latest_data:
        latest_System_data.append({
            'cpu_idle': data.cpu_idle,
            'ram_total': data.ram_total,
            'ram_free': data.ram_free,
            'conntrack': data.conntrack,
            'userol': data.userol,
            'userhs': data.userhs,
            'uptime': uci.boardstatus('uptime'),
            'load': uci.boardstatus('load'),
            'mem': uci.boardstatus('mem'),
            'cpu_detail': uci.boardstatus('cpu'),
            'timestamp': data.latest_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    return latest_System_data

def get_latest_mwan_status():
    latest_data = db.session.query(
        LoadBalance.interface,
        LoadBalance.status,
        LoadBalance.tracking,
        LoadBalance.percentage,
        func.max(LoadBalance.timestamp).label('latest_timestamp')
    ).group_by(LoadBalance.interface).all()

    latest_mwan_data = []
    for data in latest_data:
        latest_mwan_data.append({
            'interface': data.interface,
            'status': data.status,
            'tracking': data.tracking,
            'percentage': data.percentage,
            'timestamp': data.latest_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    return latest_mwan_data

def get_history(time):
    final = {}
    # Buat kueri untuk masing-masing tabel dengan kolom dummy

    split = time.split(" - ")
    start_date = datetime.strptime(split[0], '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(split[1], '%Y-%m-%d %H:%M:%S')
    time_difference = (end_date - start_date).total_seconds()
    if time_difference < 300:
        mode = '%Y-%m-%d %H:%M:%S'
    elif time_difference < 600:
        mode = '%Y-%m-%d %H:%M'
    elif time_difference < 3700:
        mode = '%Y-%m-%d %H:%M'
    elif time_difference < 86400:
        mode = '%Y-%m-%d %H'
    elif time_difference < 2592000:
        mode = '%Y-%m-%d'
    else:
        mode = '%Y-%m'
    conn = db.engine.connect()
    query_status = text(f"SELECT eth_type, round(abs(avg(speed_send/1000)),2) as 'speed_send', round(avg(speed_recv/1000),2) as 'speed_recv', strftime('%Y-%m-%d %H:%M:%S', timestamp) as 'timestamp' FROM bandwidth_status WHERE timestamp BETWEEN '{split[0]}' AND '{split[1]}' GROUP BY strftime('{mode}', timestamp), eth_type ORDER BY strftime('{mode}', timestamp);")
    query_system = text(f"select round(avg(100-cpu_idle),2) as 'cpu_idle', round(max(ram_total),2) as 'ram_total', round(avg(ram_free),2) as 'ram_free', round(avg(conntrack),2) as 'conntrack', max(userol) as 'userol', max(userhs) as userhs, strftime('%Y-%m-%d %H:%M:%S', timestamp) as 'timestamp' from system WHERE timestamp BETWEEN '{split[0]}' AND '{split[1]}' GROUP BY strftime('{mode}', timestamp) ORDER BY strftime('{mode}', timestamp);")
    query_mwan   = text(f"SELECT interface, round(case when status == 'online' then 1 else 0 end) as 'status', round(case when tracking == 'active' then 1 else 0 end) as 'tracking', percentage, strftime('%Y-%m-%d %H:%M:%S', timestamp) as 'timestamp' FROM load_balance WHERE timestamp BETWEEN '{split[0]}' AND '{split[1]}' GROUP BY strftime('{mode}', timestamp), interface ORDER BY strftime('{mode}', timestamp);")
    all_status = conn.execute(query_status)
    all_system = conn.execute(query_system)
    all_mwan = conn.execute(query_mwan)
   
    mwan3Data = {}
    def add_data_to_mwan3(interface, percentage, status, tracking, time):
        if interface not in mwan3Data:
            mwan3Data[interface] = {
                'percentage': [],
                'tracking': [],
                'status': [],
                'time': []
            }
        mwan3Data[interface]['percentage'].append(percentage)
        mwan3Data[interface]['tracking'].append(status)
        mwan3Data[interface]['status'].append(tracking)
        mwan3Data[interface]['time'].append(time)

    for data in all_mwan:
        add_data_to_mwan3(data.interface, data.percentage, data.status, data.tracking, data.timestamp)
        
    

    no2 = 1
    system = {}
    def add_data_to_system(data, cpu, ram_total, ram_free, conntrack, userol, userhs, timestamp):
        if data not in system:
            system[data] = {
                'cpu-idle': [],
                'ram-free': [],
                'session': [],
                'user-online': [],
                'user-hotspot': [],
                'timestamp': []
            }
        system[data]['cpu-idle'].append(cpu)
        # system[data]['ram_total'].append(ram_total)
        system[data]['ram-free'].append(ram_free)
        system[data]['session'].append(conntrack)
        system[data]['user-online'].append(userol)
        system[data]['user-hotspot'].append(userhs)
        system[data]['timestamp'].append(timestamp)   

    for data in all_system:
        add_data_to_system('data', data.cpu_idle, data.ram_total, data.ram_free, data.conntrack, data.userol, data.userhs, data.timestamp)
    
    interfaceData = {}
    def add_data_to_interface(ethType, eth_down, eth_upload, time):
        if ethType not in interfaceData:
            interfaceData[ethType] = {
                'eth_down': [],
                'eth_upload': [],
                'time': []
            }
        interfaceData[ethType]['eth_down'].append(eth_down)
        interfaceData[ethType]['eth_upload'].append(eth_upload)
        interfaceData[ethType]['time'].append(time)

    for data in all_status:
        add_data_to_interface(data.eth_type, data.speed_send, data.speed_recv, data.timestamp)


    final['bandwidthstatus'] = interfaceData
    final['system'] = system
    final['loadbalance'] = mwan3Data
    return final

def HS_add_profile(tipe, st, session, dr, ur, dq, uq):
    db_sent = HS_profile(tipe=tipe, mode=st, session=session, down_rate=dr, up_rate=ur, down_qouta=dq, up_qouta=uq)
    db.session.add(db_sent)
    db.session.commit()
    
def HS_get_profile():
    conn = db.engine.connect()
    query = text(f"SELECT * FROM hs_profile")
    query = conn.execute(query)
    conn.close()
    data = []
    for item in query:
        data.append({
            'tipe': item.tipe,
            'session': item.session,
            'status': item.mode,
            'down_rate': item.down_rate,
            'up_rate': item.up_rate,
            'down_qouta': item.down_qouta,
            'up_qouta': item.up_qouta
        })
    return data

def HS_update_profile(LP, tipe, st, session, dr, ur, dq, uq):
    conn = db.engine.connect()
    query = text(f"UPDATE hs_profile SET tipe = '{tipe}', mode ='{st}', session = '{session}', down_rate = '{dr}', down_qouta = '{dq}', up_qouta = '{uq}', up_rate = '{ur}' WHERE tipe = '{LP}';")
    conn.execute(query)
    conn.commit()
    conn.close()

def HS_delete_profile(tipe):
    conn = db.engine.connect()
    query = text(f"DELETE FROM hs_profile WHERE tipe = '{tipe}';")
    conn.execute(query)
    conn.commit()
    conn.close()
    
def HS_add_user(username, password, tipe=''):
    db_sent = HS_user(username=username, qoutaused=0, uptime=0, password=password, tipe=tipe)
    db.session.add(db_sent)
    db.session.commit()

def HS_get_user():
    conn = db.engine.connect()
    query = text(f"SELECT * FROM hs_user")
    query = conn.execute(query)
    data = []
    for item in query:
        data.append({
            'username': item.username,
            'password': item.password,
            'tipe': item.tipe,
            'qoutaused': item.qoutaused,
            'lastlogin': item.lastlogin,
            'uptime': item.uptime
        })
    return data

def HS_update_user(LP, user, ps, tipe):
    conn = db.engine.connect()
    query = text(f"UPDATE hs_user SET username = '{user}', password = '{ps}', tipe = '{tipe}' WHERE username = '{LP}';")
    conn.execute(query)
    conn.commit()
    conn.close()

def HS_delete_user(user):
    conn = db.engine.connect()
    query = text(f"DELETE FROM hs_user where username = '{user}';")
    conn.execute(query)
    conn.commit()
    conn.close()

def HS_user_onlogin(user, passw):
    conn = db.engine.connect()
    query = text(f"SELECT hu.username, hu.password, hp.* FROM hs_user hu INNER JOIN hs_profile hp ON hp.tipe = hu.tipe WHERE hu.username = '{user}' AND hu.password = '{passw}'")
    result = conn.execute(query)
    row = result.fetchone()  # Mengambil satu baris hasil query

    if row is None:
        return False, 'Account Not Active Or not Have User Profile', 0, 0, 0, 0, 0, 0, 0
    else:
        username, password, tipe, mode, session, down_rate, up_rate, down_qouta, up_qouta = row
        if mode == "Enable":
            return True, tipe, username, password, session, down_rate, up_rate, down_qouta, up_qouta
        else:
            return False, 'User profile Disable', 0, 0, 0, 0, 0, 0, 0

def HS_get_profile_data(tipe):
    conn = db.engine.connect()
    query = text(f"SELECT * FROM hs_profile WHERE tipe = '{tipe}'")
    query = conn.execute(query)
    conn.close()
    data = []
    for item in query:
        data.append({
            'tipe': item.tipe,
            'session': item.session,
            'status': item.mode,
            'down_rate': item.down_rate,
            'up_rate': item.up_rate,
            'down_qouta': item.down_qouta,
            'up_qouta': item.up_qouta
        })
    return data

memory_HS_user = {}
def HS_memory(token, user, dt, ut, mod=0):
    if mod == 0 :
        if token not in memory_HS_user:
            memory_HS_user[token] = {
                'user': user,
                'down_ses': dt,
                'up_ses': ut,
                'uptime': 0,
                'dl': dt,
                'ul': ut,
                'last': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            if memory_HS_user[token]['ul'] != ut or memory_HS_user[token]['dl'] != dt:
                memory_HS_user[token]['dl'] = dt
                memory_HS_user[token]['ul'] = ut
                memory_HS_user[token]['down_ses'] += (dt - memory_HS_user[token]['down_ses'])
                memory_HS_user[token]['up_ses'] += (ut - memory_HS_user[token]['up_ses'])
                memory_HS_user[token]['last'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            memory_HS_user[token]['uptime'] = 5
    elif mod == 'del':
        del memory_HS_user[token]
    else:
        return memory_HS_user

def HS_get_user_qouta():
    HS = uci.HS_status()
    if HS != 'none':
        HSC = HS['clients']
        for item in HSC:
            if  HSC[item]['state'] == 'Authenticated':
                user = HSC[item]['custom']['username']
                token = HSC[item]['token']
                dt = int(HSC[item]['download_this_session'])
                ut = int(HSC[item]['upload_this_session'])
                HS_memory(token, user, dt, ut)
    

# masih blm jadi ini njir
def HS_save_user_qouta():
    if len(memory_HS_user) != 0:
        for token, value in memory_HS_user.items():
            # print(value)
            if value['user'] != '-':
                exits_users = HS_user.query.get(value['user'])
                if exits_users:
                    exits_users.qoutaused += int(value['down_ses']) + int(value['up_ses'])
                    # exits_users.lastlogin = datetime.strptime(value['last'], "%Y-%m-%d %H:%M:%S")
                    # exits_users.uptime += int(value['uptime'])
                    db.session.commit()
                    HS_memory(token, 0, 0, 0, mod='del')
                    print(datetime.strptime(value['last'], "%Y-%m-%d %H:%M:%S"))
                else:
                   uci.HS_death(token) 
            else:
                uci.HS_death(token)
    return memory_HS_user  

def insert_domains_to_database(domains):
    for domain in domains:
        existing_domain = DNS_access.query.get(domain)
        if existing_domain:
            existing_domain.num_access += 1
        else:
            new_domain = DNS_access(url=domain, num_access=1, mode='Unblock')
            db.session.add(new_domain)
    db.session.commit()

def get_dns_access():
    dns_entries = DNS_access.query.order_by(DNS_access.num_access.desc()).all()
    
    result = []
    for entry in dns_entries:
        result.append({
            'url': entry.url,
            'num_access': entry.num_access,
            'mode': entry.mode
        })
    return result

def purge_dns_data():
    dns_entries = DNS_access.query.all()
    for entry in dns_entries:
        entry.num_access = 0
    db.session.commit()

def update_mode_for_url(url, new_mode):
    entry = DNS_access.query.filter_by(url=url).first()
    if entry:
        entry.mode = new_mode
        db.session.commit()

def resolve_domain_to_ip(domain):
    try:
        ip_address = socket.gethostbyname_ex(domain)[2]
        return ip_address
    except socket.gaierror:
        return None
    except socket.herror:
        return None

def dns_block_mode(mode, url):
    if mode == 'Block':
        os.system("nft 'add chain ip block_DNS "f'{url}'" { type filter hook forward priority filter; policy accept; }'")
        resolve = resolve_domain_to_ip(url)
        if resolve != None:
            for ip in resolve:
                os.system("nft 'add rule ip block_DNS "f'{url}'" ip saddr "f'{ip}'" counter drop'")
        else:
            pass
        
    elif mode == 'Unblock':
        os.system("nft 'delete chain ip block_DNS "f'{url}'"'")

def dns_block_load():
    os.system("nft 'add table ip block_DNS'")
    os.system("nft 'add chain ip block_DNS filter { type filter hook input priority 0; }'")
    blocked_urls = [entry.url for entry in DNS_access.query.filter_by(mode="Block").all()]
    for item in blocked_urls:
        dns_block_mode('Block', item)

def dns_block_first(mode):
    if mode == 'del':
        os.system('nft delete table ip block_DNS')
    elif mode == 'load':
        dns_block_load()

def filter_interface_ips_block(url):
    print()      

def filter_interface_ips_load():
    cd = sys.path[0]
    url_allow_exam = cd + '/instance/url_exam_allow.txt'
    try:
        with open(url_allow_exam, 'r') as file:
            isi_file = [line.strip() for line in file.readlines()]

        line1 = isi_file[0].split('=')[1] #mode
        line2 = isi_file[1].split('=')[1] #interface
        line3 = isi_file[2].split('=')[1] #url
        if line1 == 'true':   
            os.system('nft delete table inet filter_interface_ips')             
            os.system("nft 'add table inet filter_interface_ips'")
            os.system("nft 'add set inet filter_interface_ips allowed_ips { type ipv4_addr; }'")
            os.system("nft 'add element inet filter_interface_ips allowed_ips { 8.8.8.8, 8.8.4.4, 1.1.1.1, 1.1.0.0, 192.168.1.1 }'")
            for item in line3.split(', '):
                domain_ips = resolve_domain_to_ip(item)
                if domain_ips != None:
                    for I_domain_ips in domain_ips:
                        os.system("nft 'add element inet filter_interface_ips allowed_ips { "f'{I_domain_ips}'" }'")

            os.system("nft 'add chain inet filter_interface_ips input { type filter hook input priority 0; }'")
            os.system("nft 'add chain inet filter_interface_ips forward { type filter hook forward priority 0; }'")
            
            # must udp > icmp > tcp
            os.system("nft 'add rule inet filter_interface_ips input ip saddr @allowed_ips counter udp sport {53} accept'")
            os.system("nft 'add rule inet filter_interface_ips input ip saddr @allowed_ips counter ip protocol icmp accept'")
            os.system("nft 'add rule inet filter_interface_ips input ip saddr @allowed_ips counter tcp sport {icmp, http, https} accept'")

            os.system("nft 'add rule inet filter_interface_ips forward ip saddr @allowed_ips counter udp sport {53} accept'")
            os.system("nft 'add rule inet filter_interface_ips forward ip saddr @allowed_ips counter ip protocol icmp accept'")
            os.system("nft 'add rule inet filter_interface_ips forward ip saddr @allowed_ips counter tcp sport {icmp, http, https} accept'")

            # interface =  uci.get_interface()
            for item in line2.split(', '):
                if item != '':
                    os.system("nft 'add rule inet filter_interface_ips input iifname "f'{item}'" ip saddr 192.168.1.0/24 counter drop'")

        else:
            os.system('nft delete table inet filter_interface_ips')

    except FileNotFoundError:
        with open(url_allow_exam, 'w') as file:
            file.write("enabled=false\nInterface=\nUrl=\n")

def scan_ports(host, InRange, ToRange):
    open_ports = {}

    def scan_port(port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))

                if result == 0:
                    service = socket.getservbyport(port, 'tcp')
                    open_ports[port] = service
                    # print(f"Port {port} is open ({service})")
        except (socket.timeout, ConnectionRefusedError):
            pass
        except socket.error as e:
            return f"Error: {e}"

    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        return False

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        results = [executor.submit(scan_port, port) for port in range(InRange, ToRange)]
    return open_ports

def ping_ips(ip_list):
    results = {}
    def ping_ip(ip):
        try:
            result = subprocess.run(['ping', '-c', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1)
            if result.returncode == 0:
                output = result.stdout
                lines = output.split('\n')
                latency = "N/A"
                for line in lines:
                    if "time=" in line:
                        latency = line.split("time=")[1].split(" ")[0]
                results[ip] = {}
                results[ip]['latency'] = latency
                results[ip]['status'] = 'reachable'
            else:
                results[ip] = {}
                results[ip]['latency'] = latency
                results[ip]['status'] = 'unreachable'
        except subprocess.TimeoutExpired:
            results[ip] = {}
            results[ip]['latency'] = 'N/A'
            results[ip]['status'] = 'timed out'

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        executor.map(ping_ip, ip_list)

    return results

def allowed_file(filename, ALLOWED_EXTENSIONS):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def shutdown_flask():
    os.kill(os.getpid(), signal.SIGINT)

def restart_server():
    os.system('reboot')
def shutdown_server():
    os.system('poweroff')

class system:
    def rebootorshut(request):
        if  'checkreb' in request.form and request.form['checkreb'] == 'on':
            if request.form['mode'] == 'reboot':
                restart_server()
                shutdown_flask()
                return 'reboot'
        elif 'checkshut' in request.form and request.form['checkshut'] == 'on':
            if request.form['mode'] == 'shutdown':
                shutdown_server()
                shutdown_flask()
                return 'shutdown flask'
    def sytem_password(request):
        print()
    def system(request):
        print()
