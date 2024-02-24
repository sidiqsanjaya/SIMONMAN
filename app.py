#!/usr/bin/env python

import crypt
import codecs
import os
import re
import signal
import threading
from flask import Flask, jsonify, request, redirect, render_template, session, url_for
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import urllib.parse
from databases import db
import base64
import uci_cmd as uci
import netdata as net
from helpers import *
from models import *
import logging
import sys
import time
import requests


app = Flask(__name__)
app.app_context()
app.url_map.strict_slashes = False
limiter = Limiter(
    get_remote_address, 
    app=app, 
    default_limits=["10 per minute"],
    storage_uri="memory://",
)

# logging.getLogger('session_logger').setLevel(logging.DEBUG)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
# logging.getLogger('werkzeug').setLevel(logging.ERROR)
# logging.basicConfig(filename=app.root_path +'/logfile.log', level=logging.ERROR)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///cloud.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['URL_APP'] = "0.0.0.0"
app.config['URL_APP_PORT'] = "8089"
app.config['DEV_ETHER'] = []
app.config['DEV_CPU'] = []
app.secret_key = "E753BD1E469A7139A35A81EB55C69"

db.init_app(app)


@app.route('/homepage')
def homepage():
    if not checklogin():
        return redirect(f'/login?redirect={request.path}')
    model, dd, da, cpu = uci.board()
    return render_template('homepage.html', model=model, arch=da, cpu=cpu, desc=dd)


@app.route('/Online-client', methods=['GET', 'POST'])
def user_online():
    if not checklogin():
        return redirect(f'/login?redirect={request.path}')
    if request.method == 'POST':
        ip = request.form['ip']
        mac= request.form['mac']
        name= request.form['name']
        uci.set_static_dhcp(name, ip, mac)
        return redirect(url_for('user_online'))
    return render_template('online-user.html', data=uci.dhcp_lease(), static=uci.get_static_dhcp())
    

@app.route('/dns-access', defaults={'mode': None},  methods=['GET', 'POST'])
@app.route('/dns-access/<mode>', methods=['GET', 'POST'])
def route_dns(mode):
    if not checklogin():
        return redirect(f'/login?redirect={request.path}')
    if mode == None:
        return dns_access(request)
    elif mode == 'logs':
        return dns_logs(request)
    else:
        return jsonify({'error': 'Invalid request method'}), 405

def dns_access(request):
    if request.args.get('purge') == 'yes':
        purge_dns_data()
        return redirect(request.url)
    if request.args.get('reenable') == 'yes':
        dns_block_first('del')
        dns_block_first('load')
        return redirect(request.url)

    if request.args.get('state')  == 'unblock':
        urls = request.args.getlist('urls')
        for url in urls:
            update_mode_for_url(url, 'Unblock')
            dns_block_mode('Unblock', url)
        return redirect(request.url)

    if request.args.get('state')  == 'block':
        urls = request.args.getlist('urls')
        urls = request.args.getlist('urls')
        for url in urls:
            update_mode_for_url(url, 'Block')
            dns_block_mode('Block', url)
        return redirect(request.url)

    if request.method == 'POST':
        url = request.form['url']
        mode= request.form['mode']
        update_mode_for_url(url, mode)
        dns_block_mode(mode, url)
        return redirect(request.url)
    return render_template('dns-access.html')

def dns_logs(request):
    if not checklogin():
        return redirect('/login')
    draw = int(request.args.get('draw'))
    start = int(request.args.get('start'))
    length = int(request.args.get('length'))
    search = request.args.get('search')

    query = DNS_access.query.order_by(DNS_access.num_access.desc())

    if search:  # Jika ada kata kunci pencarian
        query = query.filter(
            (DNS_access.url.like(f"%{search}%")) |
            (DNS_access.mode == search)
        )

    total_items = query.count()
    end = min(start + length, total_items)

    paginated_logs = query.slice(start, end)

    response = {
        "draw": draw,
        "recordsTotal": total_items,
        "recordsFiltered": total_items,
        "data": [log.to_dict() for log in paginated_logs]
    }

    return jsonify(response)

  
@app.route('/services/monitoring', defaults={'mode': None},  methods=['GET'])
@app.route('/services/monitoring<mode>',  methods=['GET', 'POST'])
def monitoring(mode):
    if not checklogin():
        return redirect(f'/login?redirect={request.path}')
    if mode == None:
        return render_template('/services/monitor.html', data1=uci.get_static_dhcp())
    elif mode == 'api':
        if request.args.get('type') == 'local':
            fm = request.args.get('ip')
            data = ping_ips([fm])

        elif request.args.get('type') == 'ping':
            data = uci.get_static_dhcp()
        else:
            return jsonify({'error': 'Invalid request method'}), 405
        return jsonify(data)
    else:
        return jsonify({'error': 'Invalid request method'}), 405


@app.route('/services/exam', methods=['GET'])
def allow_specific_web():
    return render_template('/services/allow_web_exam.html')


@app.route('/network/speedtest', defaults={'mode': None}, methods=['GET'])
@app.route('/network/speedtest/<mode>', methods=['GET'])
def route_network(mode):
    if not checklogin():
        return redirect(f'/login?redirect={request.path}')
    if mode == None:
        return network_web_speedtest()
    elif mode == 'api':
        return network_web_api_speedtest()
    else:
        return jsonify({'error': 'Invalid request method'}), 405

def network_web_speedtest():
    relevant_data = {key: value for key, value in uci.get_interface().items() if key.startswith('wan')}
    return render_template('/network/speedtest.html', interface=relevant_data)

def network_web_api_speedtest():
    relevant_data = {key: value for key, value in uci.get_interface().items() if key.startswith('wan')}
    if not checklogin():
        return redirect('/login')
    if request.args.get('available') != 'All':
        data = net.run_speedtest_with_netdata(relevant_data, request.args.get('available'))
    else:
        data = net.run_speedtest_with_netdata(relevant_data, 'all')
    return jsonify(data)


@app.route('/hotspot', defaults={'mode': None}, methods=['GET','POST'])
@app.route('/hotspot/<mode>', methods=['GET','POST'])
def route_hotspot(mode):
    if not checklogin():
        if mode == 'login':
            return hotspot_login(request)
        else:
            return redirect(f'/login?redirect={request.path}')
    if mode == None:
        return hotspot(request)
    elif mode == 'user':
        return hotspot_user(request)
    elif mode == 'profile':
        return hotspot_profile(request)
    elif mode == 'active':
        return hotspot_active(request)
    elif mode == 'walled-garden':
        return hotspot_walled_garden(request)
    elif mode == 'editor-login':
        return hotspot_editor(request)
    else:
        return jsonify({'error': 'Invalid request method'}), 405

def hotspot(request):
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        enable = request.form['enable']
        GWname = request.form['gwname']
        GWport = request.form['gwport']
        GWinterf = request.form['gwinterface'].split('|')
        passthrought=request.form['passthrought']
        Mclient= request.form['Mclient']
        GWurl  = request.form['gwurl']
        Drate  = request.form['Drate']
        Urate  = request.form['Urate']
        Dqouta = request.form['Dquota']
        Uqouta = request.form['Uquota']
        ssourl = request.form['ssourl']
        cd = sys.path[0]
        uci.set_opennds_config(enable, GWname, GWport, GWinterf[0], GWurl, passthrought, Mclient, Drate, Urate, Dqouta, Uqouta, GWinterf[1], app.config['URL_APP_PORT'], cd, ssourl)
        return redirect(request.url)
    return render_template('/hotspot/hs_homepage.html', interface=uci.get_interface(), data=uci.get_opennds_config())
    
def hotspot_user(request):
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        mode = request.form['mode']
        user = request.form['username']
        pss = request.form['password']
        tipe = request.form['tipe']
        tipe2 = request.form['username2']

        if mode == 'add':
            HS_add_user(user, pss, tipe)
        elif mode == 'edit':
            HS_update_user(tipe2, user, pss, tipe)
        elif mode == 'delete':
            HS_delete_user(user)
    return render_template('/hotspot/hs_user.html', data=HS_get_user(), UP=HS_get_profile())

def hotspot_profile(request):
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        mode = request.form['mode']
        ss = request.form['session']
        st = request.form['status']
        tipe = request.form['tipe']
        tipe2 = request.form['tipe2']
        dr = request.form['down_rate']
        dq = request.form['down_qouta']
        ur = request.form['up_rate']
        uq = request.form['up_qouta']
        if mode == 'add':
            HS_add_profile(tipe, st, ss, dr, ur, dq, uq)
        elif mode == 'edit':
            HS_update_profile(tipe2, tipe, st, ss, dr, ur, dq, uq)
        elif mode == 'delete':
            HS_delete_profile(tipe)
    return render_template('/hotspot/hs_user_profile.html', data=HS_get_profile())

def hotspot_active(request):
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        token = request.form['mac']
        uci.HS_death(token)
    return render_template('/hotspot/hs_active.html', data=uci.HS_status())

def hotspot_walled_garden(request):
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        url = request.form['url']
        port = request.form['port']
        uci.set_opennds_config_WG(url, port)
    return render_template('/hotspot/hs_wallet_garden.html', data=uci.get_opennds_config())

def hotspot_login(request):
    tipe = True
    config_nds = uci.get_opennds_config()
    ssourl = config_nds['opennds']['sso_url']
    fas =  request.args.get('fas')
    if fas:
        if request.method == 'GET':
            decoded_data = base64.b64decode(fas).decode('utf-8')
            data_array = decoded_data.split(', ')
            data_dict = {}
            for item in data_array:
                if '=' in item:
                    key, value = item.split('=')
                    data_dict[key] = value
                else:
                    data_dict[item] = None
            sp = urllib.parse.unquote(data_dict['gatewayname']).split('Node:')
            return render_template('/hotspot/hs_login.html', fas=fas, name=sp, ssourl=ssourl, error=tipe)
    elif request.method == 'POST':
        username = str(request.form['username'])
        password = str(request.form['password'])
        fas = request.form['fas']
        if not fas:
            return jsonify({'error': 'Invalid request method'}), 405
        else:
            fas = fas
            decoded_data = base64.b64decode(fas).decode('utf-8')
            data_array = decoded_data.split(', ')
            data_dict = {}
            for item in data_array:
                if '=' in item:
                    key, value = item.split('=')
                    data_dict[key] = value
                else:
                    data_dict[item] = None

            if data_dict['originurl'] is not None:
                gatewayurl = urllib.parse.unquote(data_dict['originurl'])
            else:
                gatewayurl = 'http://'+data_dict['gatewayaddress']+'/'

            mode = 'mac'
            sp = urllib.parse.unquote(data_dict['gatewayname']).split('Node:')
            
            if  ssourl != '-':
                params_data = {
                    'username': username,
                    'password': password,
                    'service' : 'moodle_mobile_app'
                }
 
                ssourl_token = f"{ssourl}/login/token.php"
                get_token_uid = requests.get(ssourl_token, params=params_data)
                if get_token_uid.status_code == 200:
                    get_token = get_token_uid.json()
                    if 'errorcode' in get_token:
                        status = False
                        tipe = get_token['error']
                    elif 'token' in get_token:
                        params_data_2 = {
                            'wstoken' : get_token['token'],
                            'moodlewsrestformat' : 'json',
                            'wsfunction' : 'core_user_get_users_by_field',
                            'field' : 'username',
                            'values[0]': username.lower()
                        }
                        ssourl_server = f"{ssourl}/webservice/rest/server.php"
                        get_usertipe = requests.get(ssourl_server, params=params_data_2)
                        get_usertipe = get_usertipe.json()

                        string = get_usertipe[0]['fullname']
                        pattern = re.compile(r'^X')

                        if get_usertipe[0]['department'] != '':
                            typeuser = get_usertipe[0]['department']
                        elif pattern.search(string):
                            typeuser = 'siswa'
                        else:
                            typeuser = 'guru'
                        sett = HS_get_profile_data(typeuser)
                        if len(sett) != 0:
                            if sett[0]['status'] == 'Enable':
                                status = True
                                session = sett[0]['session']
                                tipe = typeuser
                                username = f"SSO ({get_usertipe[0]['fullname']})"
                                down_rate = sett[0]['down_rate']
                                down_qouta= sett[0]['down_qouta']
                                up_rate   = sett[0]['up_rate']
                                up_qouta  = sett[0]['up_qouta']
                            else:
                                status = False
                                tipe = 'User profile Disable'
                        else:
                            status = False
                            tipe = f"User profile not found for user {get_usertipe[0]['department']}"
                        # return get_usertipe
                    else:
                        status, tipe, uname, passw,  session, down_rate, up_rate, down_qouta, up_qouta  =HS_user_onlogin(username, password)   
            else:    
                status, tipe, uname, passw,  session, down_rate, up_rate, down_qouta, up_qouta  =HS_user_onlogin(username, password)
            if status:
                if mode == "mac":
                    token = data_dict['clientmac']
                elif mode == "ip":
                    token = data_dict['clientip']    

                data = 'username='+username+'&tipe='+tipe+'&password='+password
                uci.HS_active(token, session, down_rate, up_rate, down_qouta, up_qouta, base64.b64encode(data.encode('utf-8')))
                return redirect(gatewayurl, code=302)
            else:
                return render_template('/hotspot/hs_login.html', fas=fas, name=sp, error=tipe)
    else:
        return jsonify({'error': 'Request tidak dapat ditemukan'}), 405

def hotspot_editor(request):
    if not checklogin():
        return redirect('/login')

    if request.method == 'POST':
        if request.form['btn'] == 'save':
            if 'logo' in request.files:
                logo = request.files['logo']
                if logo.filename != '':
                    if logo and allowed_file(logo.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                        name = 'hs_cover.jpg'
                        filepath = os.path.join(app.root_path + '/static/image/', name)
                        logo.save(filepath)

            if 'background' in request.files:
                background = request.files['background']
                if background.filename != '':
                    if background and allowed_file(background.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                        name = 'hs_background.jpg'
                        filepath = os.path.join(app.root_path + '/static/image/', name)
                        background.save(filepath)

            data_html = request.form['html']
            f = open(app.root_path + "/templates/hotspot/hs_login.html", 'w')
            f.write(data_html)
            f.close()
        if request.form['btn'] == 'reset':
            f_html = codecs.open(app.root_path + "/templates/hotspot/hs_login.bcp", 'r')
            f = open(app.root_path + "/templates/hotspot/hs_login.html", 'w')
            f.write(f_html.read())
            f.close()
            print()

        return redirect(request.url)
    f_html = codecs.open(app.root_path + "/templates/hotspot/hs_login.html", 'r')
    return render_template('/hotspot/hs_editor.html', data=f_html.read())


# cron task
start_time = [0, 0, 0]
task0 = 5
task1 = 10
task2 = 20
def background_task():
    with app.app_context():
        while True:
            # Catat waktu awal eksekusi
            for Stime in range(len(start_time)):
                if start_time[Stime] == 0:
                    start_time[Stime] = time.time()
            
            if time.time() - start_time[0] > task0:
                data_on_netdata = net.get_netdata()
                for key, value in data_on_netdata.items():
                    if key == 'system':
                        hs = uci.HS_status()
                        
                        if hs != 'none':
                            if hs['client_list_length'] == 0:
                                hsa = 0
                            else:
                                hsa= int(hs['client_list_length'])
                        else:
                            hsa = 0
                        db_sent = System(cpu_idle=value['cpu_idle'], ram_total=value['ram_total'], ram_free=value['ram_free'], conntrack=value['conntrack'], userol=uci.get_leased(), userhs=hsa)
                    else:
                        db_sent = BandwidthStatus(eth_type=key, speed_send=value['send'], speed_recv=value['recev'])
                    db.session.add(db_sent)
                    db.session.commit()
                
                data_mwan3 = uci.get_mwan_status()
                for key, value in data_mwan3.items():
                    if 'tracking' in value:
                        db_sent = LoadBalance(interface=key, status=value['status'], tracking=value['tracking'], percentage=value['percentage'])
                    else:
                        db_sent = LoadBalance(interface=key, status=value['status'], tracking='error', percentage=value['percentage'])
                    db.session.add(db_sent)
                    db.session.commit()

                insert_domains_to_database(uci.DNS_tracker())
                start_time[0] = time.time()

            # if time.time() - start_time[1] > task1:
            #     print('task1')
            #     start_time[1] = time.time()
            
            # if time.time() - start_time[2] > task2:
            #     print('task2')
            #     start_time[2] = time.time()

def check_password(password_input):
    with open('/etc/shadow', 'r') as shadow_file:
        for line in shadow_file:
            if line.startswith('root:'):
                password_hash = line.split(':')[1]
                if crypt.crypt(password_input, password_hash) == password_hash:
                    return True
                break
    # return True
    return False

@app.route('/')
def index():
    return redirect(url_for('login'))

def checklogin():
    if 'authenticated' not in session or not session['authenticated']:
        return False
    return True

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        password = request.form['loginpass']
        if check_password(password):
            session['authenticated'] = True
            if request.args.get('redirect'):
                request.args.get('redirect')
                return redirect(request.args.get('redirect'))
            else:
                return redirect(url_for('homepage'))
        else:
            error = 'Incorect Password'
            return render_template('login.html', error=error)
    if 'authenticated' in session and session['authenticated']:
        return redirect(url_for('homepage'))
    else:
        return render_template('login.html', error=error, redirect=request.args.get('redirect'))

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/api', methods=['GET'])
@limiter.limit("200 per minute")
def api():
    if 'authenticated' in session and session['authenticated']:
        if request.method == 'GET':
            mode = request.args.get('mode')
            if(mode == 'flow'):
                data = net.get_netdata()
            elif(mode == 'system'):
                data = get_latest_system_data()
            elif(mode == 'loadbalance-status'):
                data = get_latest_mwan_status()
            elif(mode == 'flow-history'):
                lenght = request.args.get('time')
                data = get_history(lenght)
            else:
                return jsonify({'error': 'Invalid request method'}), 405
            return jsonify(data)
        else:
            return jsonify({'error': 'Invalid request method'}), 405
    else:
        return jsonify({'error': 'Unauthorized'}), 401    

@app.route('/detect-user-agent')
def detect_user_agent():
    # Mendapatkan nilai header User-Agent
    user_agent = request.headers.get('User-Agent')
    return jsonify(request.headers.get('User-Agent'))
    # Melakukan deteksi berdasarkan header User-Agent
    if 'Mozilla' in user_agent:  # Contoh sederhana, Mozilla sering digunakan oleh browser
        return "Permintaan berasal dari browser"
    else:
        return "Permintaan bukan berasal dari browser"


def install():
    print('Checker...')
    cd = sys.path[0]
    # uci.install_ipk(cd)
    app.config['DEV_CPU'] = uci.get_cpu_cores()
    app.config['DEV_ETHER'] = uci.get_hardware_interface('name')
    print("Checker done!")

@app.errorhandler(404)
def page_not_found(error):
    return render_template('/fe/404.html')

@app.errorhandler(400)
def page_not_found(error):
    return render_template('/fe/400.html')

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('/fe/429.html'), 429

@limiter.request_filter
def ip_whitelist():
    return request.remote_addr == "127.0.0.1"
@limiter.request_filter
def header_whitelist():
    return request.headers.get("X-Internal", "") == "true"

limiter.exempt(monitoring)
limiter.exempt(hotspot_login)


# background_thread = threading.Thread(target=background_task)
# background_thread.daemon = True



if __name__ == '__main__':    
    with app.app_context():
        db.create_all()
        Session(app)
        install()
        net.init(app)
        dns_block_first('load')
        # background_thread.start()
        # filter_interface_ips_load()

    app.run(debug=True, host=app.config['URL_APP'], port=app.config['URL_APP_PORT'], threaded=True)
