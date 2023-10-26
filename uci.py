import base64
from datetime import datetime
import subprocess
import re
import json
from urllib.parse import unquote
import multiprocessing

def install_ipk(dir):
    configurations = [
        "opkg update",
        "opkg install netdata",
        "opkg remove dnsmasq",
        "opkg install dnsmasq-full",
        "opkg install opennds",
        "opkg install luci-app-mwan3",
        "chmod +x "f"{dir}""/bash_script/client_params.sh",
        "rm /etc/config/opennds",
        "cp "f"{dir}""/bash_script/opennds /etc/config",
        "cp "f"{dir}""/static/image/cover.jpg /etc/opennds/htdocs",
        "cp "f"{dir}""/static/vendor/bootstrap/css/bootstrap.css /etc/opennds/htdocs",
        "cp "f"{dir}""/static/vendor/bootstrap/js/bootstrap.bundle.min.js /etc/opennds/htdocs",
        "cp "f"{dir}""/static/css/style.css /etc/opennds/htdocs",
        "cp "f"{dir}""/static/js/main.js /etc/opennds/htdocs",
        "uci set dhcp.@dnsmasq[0].logfacility=/tmp/dnsmasq.log",
        "uci set dhcp.@dnsmasq[0].logqueries=1",
        "uci commit dhcp"
    ]

    for config_key in configurations:
        try:
            result = subprocess.run(config_key, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(result.stderr)
        except Exception as e:
            print(str(e))

def convert_unix_timestamp(unix_timestamp):
    # Ubah timestamp UNIX menjadi format datetime yang lebih mudah dibaca
    return datetime.utcfromtimestamp(int(unix_timestamp)).strftime('%Y-%m-%d %H:%M:%S')

def convert_speed(speed):
    if speed == "null":
        return "Unlimited"
    
    try:
        speed = int(speed)
        if speed >= 1000000:
            return f"{speed / 1000} Mbps"
        elif speed >= 1000:
            return f"{speed} Kbps"
        else:
            return f"{speed} bps"
    except ValueError:
        return "Unlimited"
    
def get_leased():
    leases_file = "/var/dhcp.leases"
    with open(leases_file, "r") as f:
        leases_data = f.readlines()
    num_allocated_ips = len(leases_data)
    return num_allocated_ips

def get_mwan_status():
    output = subprocess.check_output(['mwan3', 'status'], text=True)

    interface_status_pattern = r'interface (\w+) is (\w+)(?: (\S+), uptime (\S+))?(?: and tracking is (\w+))?'
    interface_status_matches = re.findall(interface_status_pattern, output)

    result = {}
    for match in interface_status_matches:
        interface_name, status, _, uptime, tracking = match
        interface_info = {"status": status}
        if uptime:
            interface_info["uptime"] = uptime
        if tracking:
            interface_info["tracking"] = tracking
        result[interface_name] = interface_info

    for interface_name, interface_info in result.items():
        if "status" in interface_info and interface_info["status"] == "offline":
            interface_info["percentage"] = 0

    ipv4_policies_pattern = r'balanced:(.*?)(?:_only:|$)'
    ipv4_policies_match = re.search(ipv4_policies_pattern, output, re.DOTALL)
    if ipv4_policies_match:
        ipv4_policies_text = ipv4_policies_match.group(1).strip()

        policy_entries = re.findall(r'(\w+)\s\((\d+)%\)', ipv4_policies_text)

        percentages = {}

        for entry in policy_entries:
            interface_name, percentage = entry
            percentages[interface_name] = int(percentage)

        for interface_name, percentage in percentages.items():
            if interface_name in result:
                result[interface_name]["percentage"] = percentage

    return result

def board():
    with open('/etc/board.json', 'r') as file:
        data = json.load(file)
    with open('/etc/openwrt_release', 'r') as file:
        lines = file.readlines()
    for line in lines:
        if line.startswith('DISTRIB_DESCRIPTION='):
            DD = line.split('=')[1].strip().strip().strip("'")
        elif line.startswith('DISTRIB_ARCH='):
            DA = line.split('=')[1].strip().strip().strip("'")

    MN = data['model']['name']
    return MN, DD, DA

def get_interface():
    output = subprocess.check_output(["uci", "show", "network"], universal_newlines=True)
    lines = output.split('\n')
    network_data = {}
    current_section = None
    for line in lines:
        if line != '':
            line = line.strip().replace("'", "")
            sp = re.split(r'(?<!\')\.',line)
            section, key = sp[0], sp[1]
            sp2 = sp[1].split('=')

            if sp2[0] not in network_data:
                network_data[sp2[0]] = {}
            if '=' in sp[1]:
                # network_data[sp2[0]][sp2[0]] = {}
                network_data[sp2[0]]['section'] = sp2[1]
            elif len(sp) >2 :
                sp3 = sp[2].split('=')
                if 'option' not in network_data[sp[1]]:
                    network_data[sp[1]]['option'] = {}
                if len(sp) > 4:
                    network_data[sp[1]]['option'][sp3[0]] = sp[2]+'.'+sp[3]+'.'+sp[4]+'.'+sp[5]
                else:
                    if len(sp) > 3:
                        network_data[sp[1]]['option'][sp3[0]] = sp3[1]+'.'+sp[3]
                    else:
                        network_data[sp[1]]['option'][sp3[0]] = sp3[1]

    return network_data

def get_opennds_config():
    output = subprocess.check_output(["uci", "show", "opennds"], universal_newlines=True)
    opennds_data = {}

    for line in output.splitlines():
        if line.startswith("opennds.@opennds[0]."):
            name = line[len("opennds.@opennds[0]."):]
            _, value = name.split("=")

            value = value.strip('\'')
            
            name = _.strip('\'')
            
            opennds_data[name] = value

    organized_data = {
        "opennds": opennds_data
    }
    return organized_data

def set_opennds_config(enable, GWname, GWport, GWinterf, GWurl, passthrought, Mclient, Drate, Urate, Dqouta, Uqouta, FasRemoteIp, FasRemotePort, cd):
    if enable == 'on':
        enable = 1
    else:
        enable = 0
    if passthrought == 'on':
        passthrought = 1
    else:
        passthrought = 0
    configurations = [
        ("opennds.@opennds[0].enabled=" f"{enable}"),
        ("opennds.@opennds[0].debuglevel=1"),
        ("opennds.@opennds[0].login_option_enabled=0"),
        ("opennds.@opennds[0].fasport=" f"{FasRemotePort}"),
        ("opennds.@opennds[0].faspath=/hotspot/login"),
        ("opennds.@opennds[0].fasremoteip="f"{FasRemoteIp}"),
        ("opennds.@opennds[0].secure_enabled=1"),
        ("opennds.@opennds[0].faskey=abcd123141"),
        ("opennds.@opennds[0].gatewayname="f"{GWname}"),
        ("opennds.@opennds[0].gatewayinterface="f"{GWinterf}"),
        ("opennds.@opennds[0].gatewayport="f"{GWport}"),
        ("opennds.@opennds[0].gatewayfqdn="f"{GWurl}"),
        ("opennds.@opennds[0].users_to_router_passthrough="f"{passthrought}"),
        ("opennds.@opennds[0].maxclients="f"{Mclient}"),
        ("opennds.@opennds[0].downloadrate="f"{Drate}"),
        ("opennds.@opennds[0].downloadquota="f"{Dqouta}"),
        ("opennds.@opennds[0].uploadrate="f"{Urate}"),
        ("opennds.@opennds[0].uploadquota="f"{Uqouta}"),
        ("opennds.@opennds[0].statuspath="f"{cd}""/bash_script/client_params.sh")
    ]
    for config_key in configurations:
        subprocess.run(["uci", "set", f"{config_key}"], check=True)

    subprocess.run(["uci", "commit", "opennds"], check=True)
    subprocess.run(["/etc/init.d/opennds", "restart"], check=True)

def set_opennds_config_WG(url, port):
    configurations = [
        ("opennds.@opennds[0].walledgarden_fqdn_list=" f"{url}"),
        ("opennds.@opennds[0].walledgarden_port_list=" f"{port}"),
    ]
    for config_key in configurations:
        subprocess.run(["uci", "set", f"{config_key}"], check=True)

    subprocess.run(["uci", "commit", "opennds"], check=True)
    subprocess.run(["/etc/init.d/opennds", "restart"], check=True)

def HS_active(token, session=0, Up_rate=0, Down_rate=0, Up_qouta=0, Down_qouta=0, costum=None):
    command = ['ndsctl', 'auth', str(token), str(session), str(Up_rate), str(Down_rate), str(Up_qouta), str(Down_qouta), costum]
    try:
        output = subprocess.check_output(command, text=True)
        return 'Active Auth'
    except subprocess.CalledProcessError as e:
        return "Already Active"

def HS_death(token):
    command = ['ndsctl', 'deauth', token]
    try:
        output = subprocess.check_output(command, text=True)
        return 'Deauth Done'
    except subprocess.CalledProcessError as e:
        return "Already Deauth"

def HS_status():
    command = ['ndsctl', 'json']
    try: 
        output = subprocess.check_output(command, text=True)
        output = output.strip()
        data_dict = json.loads(output)
        
        for mac, client_data in data_dict['clients'].items():
            if client_data['session_start'] != '0':
                start = int(client_data.get('session_start', ''))
                client_data['session_start'] = datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S')
            else:
                client_data['session_start'] = '-'
            if client_data['session_end'] != 'null':
                end = int(client_data.get('session_end', ''))
                client_data['session_end'] = datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S')
            else:
                client_data['session_end'] = '-'
            if client_data['last_active'] != 'null':
                last = int(client_data.get('last_active', ''))
                client_data['last_active'] = datetime.fromtimestamp(last).strftime('%Y-%m-%d %H:%M:%S')
            else:
                client_data['last_active'] = '-'
            if client_data['custom'] != 'none':
                encoded_custom = client_data.get('custom', '')
                decoded_custom = base64.b64decode(encoded_custom).decode('utf-8')
                if decoded_custom != 'na':

                    custom_attributes = {}
                    for attribute in decoded_custom.split('&'):
                        key, value = attribute.split('=')
                        custom_attributes[key] = value
                    client_data['custom'] = custom_attributes
                else:
                    client_data['custom'] = {'username':'-'}
        return data_dict
    except subprocess.CalledProcessError as e:
        return "none"

def HS_count_qouta():
    # data = HS_status()
    data = {'client_list_length': '3', 'clients': {'ea:d4:54:e7:28:d0': {'gatewayname': 'test%20bang%20Node%3a0800273f409f%20', 'gatewayaddress': '192.168.1.1:2050', 'gatewayfqdn': 'status.client', 'version': '10.1.3', 'client_type': 'preemptive', 'mac': 'ea:d4:54:e7:28:d0', 'ip': '192.168.1.229', 'clientif': 'br-lan', 'session_start': '2023-10-17 13:41:50', 'session_end': '2023-10-18 12:40:50', 'last_active': '2023-10-17 14:02:10', 'token': 'b43812c4', 'state': 'Authenticated', 'custom': {'username': '-'}, 'download_rate_limit_threshold': 'null', 'download_packet_rate': 'null', 'download_bucket_size': 'null', 'upload_rate_limit_threshold': 'null', 'upload_packet_rate': 'null', 'upload_bucket_size': 'null', 'download_quota': 'null', 'upload_quota': 'null', 'download_this_session': '1847', 'download_session_avg': '12.41', 'upload_this_session': '718', 'upload_session_avg': '4.82'}, '8c:18:d9:ae:40:55': {'gatewayname': 'test%20bang%20Node%3a0800273f409f%20', 'gatewayaddress': '192.168.1.1:2050', 'gatewayfqdn': 'status.client', 'version': '10.1.3', 'client_type': 'preemptive', 'mac': '8c:18:d9:ae:40:55', 'ip': '192.168.1.232', 'clientif': 'br-lan', 'session_start': '2023-10-17 13:41:51', 'session_end': '2023-10-18 13:24:51', 'last_active': '2023-10-17 14:01:35', 'token': '9526d459', 'state': 'Authenticated', 'custom': {'username': '-'}, 'download_rate_limit_threshold': 'null', 'download_packet_rate': 'null', 'download_bucket_size': 'null', 'upload_rate_limit_threshold': 'null', 'upload_packet_rate': 'null', 'upload_bucket_size': 'null', 'download_quota': 'null', 'upload_quota': 'null', 'download_this_session': '103', 'download_session_avg': '0.69', 'upload_this_session': '73', 'upload_session_avg': '0.50'}, '08:00:27:e9:5f:bb': {'gatewayname': 'test%20bang%20Node%3a0800273f409f%20', 'gatewayaddress': '192.168.1.1:2050', 'gatewayfqdn': 'status.client', 'version': '10.1.3', 'client_type': 'preemptive', 'mac': '08:00:27:e9:5f:bb', 'ip': '192.168.1.148', 'clientif': 'br-lan', 'session_start': '2023-10-17 13:41:51', 'session_end': '2023-10-18 13:28:51', 'last_active': '2023-10-17 14:02:05', 'token': 'dc20fffc', 'state': 'Authenticated', 'custom': {'username': '-'}, 'download_rate_limit_threshold': 'null', 'download_packet_rate': 'null', 'download_bucket_size': 'null', 'upload_rate_limit_threshold': 'null', 'upload_packet_rate': 'null', 'upload_bucket_size': 'null', 'download_quota': 'null', 'upload_quota': 'null', 'download_this_session': '31', 'download_session_avg': '0.21', 'upload_this_session': '27', 'upload_session_avg': '0.18'}}}

def dhcp_lease():
    dhcp_lease_data = []
    leases_file = "/var/dhcp.leases"
    with open(leases_file, "r") as file:
        for line in file:
            elements = line.split()
            if len(elements) >= 4:
                timestamp = int(elements[0])
                mac_address = elements[1]
                ip_address = elements[2]
                hostname = elements[3]
                timestamp_datetime = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                dhcp_lease_data.append({
                    'timestamp': timestamp_datetime,
                    'mac_address': mac_address,
                    'ip_address': ip_address,
                    'hostname': hostname
                })
    return dhcp_lease_data

def DNS_tracker():
    log_file = '/tmp/dnsmasq.log'
    accessed_domains = set()  # Set untuk menyimpan nama domain yang diakses

    with open(log_file, 'r') as file:
        for line in file:
            query_match = re.search(r'query\[A\] (.+) from (\d+\.\d+\.\d+\.\d+)', line)
            if query_match:
                requested_domain = query_match.group(1)
                accessed_domains.add(requested_domain)

    with open(log_file, 'w') as file:
        file.truncate()

    return list(accessed_domains)

def get_hardware_interface(mode):
    with open('/proc/net/dev', 'r') as file:
        lines = file.readlines()
    data = lines[2:]
    data_array = []
    for line in data:
        fields = line.split()
        interface = fields[0].rstrip(':')

        if mode == 'name':
            if interface != 'lo':
                if interface.startswith('eth'):
                    data_array.append(interface)
                else:
                    break
        else:
            bytes_in = int(fields[1])
            packet_in = int(fields[2])
            errs_in = int(fields[3])
            drop_in = int(fields[4])
            fifo_in = int(fields[5])
            frame_in = int(fields[6])
            comp_in = int(fields[7])
            multi_in = int(fields[8])
            bytes_out = int(fields[9])
            packet_out = int(fields[10])
            errs_out = int(fields[11])
            drop_out = int(fields[12])
            fifo_out = int(fields[13])
            colls_out = int(fields[14])
            carrier_out = int(fields[15])
            comp_out = int(fields[16])

            data_array.append({
                'interface': interface,
                'bytes_in': bytes_in,
                'packet_in': packet_in,
                'errs_in': errs_in,
                'drop_in': drop_in,
                'fifo_in': fifo_in,
                'frame_in': frame_in,
                'comp_in': comp_in,
                'multi_in': multi_in,
                'bytes_out': bytes_out,
                'packet_out': packet_out,
                'errs_out': errs_out,
                'drop_out': drop_out,
                'fifo_out': fifo_out,
                'colls_out': colls_out,
                'carrier_out': carrier_out,
                'comp_out': comp_out

            })
    return data_array

def get_cpu_cores():
    data_array =[]
    no = 0
    data = multiprocessing.cpu_count()
    for i in range(data):
        data_array.append(no)
        no = no + 1
    return data_array
