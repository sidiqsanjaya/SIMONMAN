import requests
import json

# URL API Netdata "allmetrics" yang akan digunakan
netdata_url = 'http://127.0.0.1:19999/api/v1/allmetrics?format=json&names=yes&data=as-collected'
chart_data = {}
chart_net = ['eth0','eth1','eth2']
chart_cpu = ['0','1','2','3']

def get_netdata():
    cpu_sum = 0
    try:
        # Lakukan permintaan HTTP GET ke URL Netdata "allmetrics"
        response = requests.get(netdata_url)
        
        # Periksa apakah permintaan berhasil (status code 200)
        if response.status_code == 200:
            # Parse response JSON ke dalam bentuk dictionary Python
            data = json.loads(response.text)
            for net in chart_net:
                if(data[f"net_carrier.{net}"]['dimensions']['carrier']['value'] == 1):
                    chart_data[f'{net}'] = {}
                    chart_data[f'{net}']['status'] = "Up"
                    chart_data[f'{net}']['speed'] = data[f'net_speed.{net}']['dimensions']['speed']['value']
                    chart_data[f'{net}']['send'] = data[f"net.{net}"]["dimensions"]["sent"]["value"]
                    chart_data[f'{net}']['recev'] = data[f"net.{net}"]["dimensions"]["received"]["value"]
                else:
                    chart_data[f'{net}'] = {}
                    chart_data[f'{net}']['status'] = "Down"
                    chart_data[f'{net}']['speed'] = 0
                    chart_data[f'{net}']['send'] = 0
                    chart_data[f'{net}']['recev'] = 0
                    
            for cpu in chart_cpu:
                cpu_sum = cpu_sum + data[f'cpu.cpu{cpu}']['dimensions']['idle']['value']
            chart_data['system'] = {}
            chart_data['system']['cpu_idle'] = cpu_sum/len(chart_cpu)
            chart_data['system']['ram_total'] = data['system.ram']['dimensions']['free']['value'] + data['system.ram']['dimensions']['used']['value'] + data['system.ram']['dimensions']['cached']['value'] + data['system.ram']['dimensions']['buffers']['value']
            chart_data['system']['ram_free'] = data['system.ram']['dimensions']['free']['value']
            chart_data['system']['conntrack'] = data['netfilter.conntrack_sockets']['dimensions']['connections']['value']
            # all_metrics berisi semua metrik yang tersedia dalam bentuk list
            
            
            return chart_data
            
            # Proses data sesuai kebutuhan Anda
        else:
            return 'fail'

    except requests.exceptions.RequestException as e:
        return 'fail'
