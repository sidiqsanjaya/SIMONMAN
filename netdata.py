import time
import requests
import json
import os


# URL API Netdata "allmetrics" yang akan digunakan
netdata_url = 'http://127.0.0.1:19999/api/v1/allmetrics?format=json&names=yes&data=as-collected'
chart_data = {}
chart_net = []
chart_cpu = []

def init(app):
    cpu = app.config["DEV_CPU"]
    for a in cpu:
        chart_cpu.append(a)
    eth = app.config["DEV_ETHER"]
    for a in eth:
        chart_net.append(a)

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
                if f"net_carrier.{net}" in data and data[f"net_carrier.{net}"]['dimensions']['carrier']['value'] == 1:
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


import subprocess
from multiprocessing import Process, Queue, Event

def run_speedtest():
    result = subprocess.run(["speedtest", "--json", "--share"], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    
    data = json.loads(result.stdout)
    return data


def get_netdata_speed(queue, mon_ether, start_event):
    start_event.set()
    while True:
        try:
            chart_data_speed = {}
            response = requests.get(netdata_url)
            if response.status_code == 200:
                data = json.loads(response.text)
                for net in mon_ether:
                    chart_data_speed[f'{net}'] = {}
                    if(data[f"net_carrier.{net}"]['dimensions']['carrier']['value'] == 1):
                        
                        chart_data_speed[f'{net}']['send'] = data[f"net.{net}"]["dimensions"]["sent"]["value"]
                        chart_data_speed[f'{net}']['recev'] = data[f"net.{net}"]["dimensions"]["received"]["value"]
                    else:
                        chart_data_speed[f'{net}']['send'] = 0
                        chart_data_speed[f'{net}']['recev'] = 0

            queue.put(chart_data_speed)
            time.sleep(1.5)
        except requests.exceptions.RequestException as e:
            print('fail')
    
def run_speedtest_with_netdata(eth, mode):
    start_event = Event()
    mon_ether = []
    disable_wan = []
    if mode == 'all':
        for key, value in eth.items():
            mon_ether.append(value['option']['device'])
    else:
        for key, value in eth.items():
            if mode == key:
                mon_ether.append(value['option']['device'])
            else:
                disable_wan.append(key)
                subprocess.check_output(['mwan3', 'ifdown', key], text=True)

    queue = Queue()
    netdata_process = Process(target=get_netdata_speed, args=(queue, mon_ether, start_event))
    netdata_process.start()
    start_event.wait()

    speed = run_speedtest()

    netdata_process.terminate()
    netdata_process.join()

    netdata_speed = {}
    while not queue.empty():
        for key, value in queue.get().items():
            
            if key not in netdata_speed:
                netdata_speed[key] = {
                    'send': [],
                    'recev': []
                }
            netdata_speed[key]['send'].append(abs(value['send']))
            netdata_speed[key]['recev'].append(abs(value['recev']))

    if disable_wan:
        for item in disable_wan:
            subprocess.check_output(['mwan3', 'ifup', item], text=True)

    if speed:
        data = []
        data.append({'speedtest': speed, 'log_netdata': netdata_speed})
        
    else:
        data = []
        data.append({'speedtest': [], 'log_netdata': netdata_speed})
    return data

