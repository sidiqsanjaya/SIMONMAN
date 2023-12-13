#!/usr/bin/env python

import crypt
import os
import re
from flask import Flask, jsonify, request, redirect, render_template, session, url_for
from dotenv import load_dotenv, set_key
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
import datetime
import requests

# logging.basicConfig(filename='/root/NDS/logfile.log', level=logging.ERROR)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
app.app_context()
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('sqlite_database')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
uri = os.environ.get('url')
port = os.environ.get('port')
app.secret_key = os.environ.get('secret_key')

db.init_app(app)


@app.route('/homepage')
def homepage():
    if not checklogin():
        return redirect('/login')
    model, dd, da = uci.board()
    return render_template('homepage.html', model=model, arch=da, desc=dd)

@app.route('/Online-client', methods=['GET', 'POST'])
def user_online():
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        ip = request.form['ip']
        mac= request.form['mac']
        name= request.form['name']
        uci.set_static_dhcp(name, ip, mac)
        return redirect(url_for('user_online'))
    return render_template('online-user.html', data=uci.dhcp_lease(), static=uci.get_static_dhcp())

@app.route('/dns-access', methods=['GET', 'POST'])
def dns_access():
    if not checklogin():
        return redirect('/login')
    if request.args.get('purge') == 'yes':
        purge_dns_data()
        return redirect(url_for('dns_access'))
    if request.args.get('reenable') == 'yes':
        dns_block_first('del')
        dns_block_first('load')
        return redirect(url_for('dns_access'))

    if request.args.get('state')  == 'unblock':
        urls = request.args.getlist('urls')
        for url in urls:
            update_mode_for_url(url, 'Unblock')
            dns_block_mode('Unblock', url)
        return redirect(url_for('dns_access'))

    if request.args.get('state')  == 'block':
        urls = request.args.getlist('urls')
        urls = request.args.getlist('urls')
        for url in urls:
            update_mode_for_url(url, 'Block')
            dns_block_mode('Block', url)
        return redirect(url_for('dns_access'))

    if request.method == 'POST':
        url = request.form['url']
        mode= request.form['mode']
        update_mode_for_url(url, mode)
        dns_block_mode(mode, url)
        return redirect(url_for('dns_access'))
    return render_template('dns-access.html')

@app.route('/dns-access/logs', methods=['GET'])
def get_dns_logs():
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

@app.route('/services/monitoring/api', methods=['GET'])
def monitoring_device():
    if not checklogin():
        return redirect('/login')
    if request.args.get('type') == 'local':
        fm = request.args.get('ip')
        data = ping_ips([fm])
    elif request.args.get('type') == 'ping':
        data = uci.get_static_dhcp()
    else:
        return jsonify({'error': 'Invalid request method'}), 405
    return jsonify(data)

@app.route('/services/monitoring')
def monitoring():
    return render_template('/services/monitor.html', data1=uci.get_static_dhcp())

@app.route('/services/exam', methods=['GET'])
def allow_specific_web():
    return render_template('/services/allow_web_exam.html')

@app.route('/hotspot', methods=['GET','POST'])
def hotspot():
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
        uci.set_opennds_config(enable, GWname, GWport, GWinterf[0], GWurl, passthrought, Mclient, Drate, Urate, Dqouta, Uqouta, GWinterf[1], port, cd, ssourl)
        return redirect(url_for('hotspot'))
    return render_template('/hotspot/hs_homepage.html', interface=uci.get_interface(), data=uci.get_opennds_config())
    
@app.route('/hotspot/user', methods=['GET','POST'])
def hotspot_user():
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

@app.route('/hotspot/profile', methods=['GET','POST'])
def hotspot_profile():
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

@app.route('/hotspot/active', methods=['GET', 'POST'])
def hotspot_active():
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        token = request.form['mac']
        uci.HS_death(token)
    return render_template('/hotspot/hs_active.html', data=uci.HS_status())

@app.route('/hotspot/walled-garden', methods=['GET', 'POST'])
def hotspot_walled_garden():
    if not checklogin():
        return redirect('/login')
    if request.method == 'POST':
        url = request.form['url']
        port = request.form['port']
        uci.set_opennds_config_WG(url, port)
    return render_template('/hotspot/hs_wallet_garden.html', data=uci.get_opennds_config())

@app.route('/hotspot/login', methods=['GET', 'POST'])
def hotspot_login():
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
                            'field' : 'id',
                            'values[0]': 2
                        }
                        ssourl_server = f"{ssourl}/webservice/rest/server.php"
                        get_usertipe = requests.get(ssourl_server, params=params_data_2)
                        get_usertipe = get_usertipe.json()

                        string = get_usertipe[0]['firstname']
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


min1 = 0
min2 = 0
@app.route('/cron')
def cron():
    with app.app_context():
        global min1, min2
        date_time = datetime.datetime.now()
        time_unix = time.mktime(date_time.timetuple())

        # per 5 seccond
        data_on_netdata = net.get_netdata()
        for key, value in data_on_netdata.items():
            if key == 'system':
                hs = uci.HS_status()
                
                if hs['client_list_length'] == 0:
                    hsa = 0
                else:
                    hsa= int(hs['client_list_length'])
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

        # per minute run
        
        HS_get_user_qouta()
        if min1 == 0 or (time_unix - min1) >= 32:
            min1 = time_unix
            # HS_save_user_qouta()
        if min2 == 0 or (time_unix - min2) >= 60:
            min2 = time_unix
            # print(f"Memperbarui sec5 ke {min2}")

    return ''

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
            return redirect(url_for('homepage'))
        else:
            error = 'Incorect Password'
            return render_template('login.html', error=error)
    if 'authenticated' in session and session['authenticated']:
        return redirect(url_for('homepage'))
    else:
        return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/api', methods=['GET'])
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

def install():
    if os.environ.get('first_run') == 'true':
        print('Installing...')
        cd = sys.path[0]
        uci.install_ipk(cd)
        cpu_core_str = ",".join(map(str, uci.get_cpu_cores()))
        set_key('.env', 'cpu_cores', cpu_core_str)

        eth_str = ",".join(map(str, uci.get_hardware_interface('name')))
        set_key('.env', 'ether', eth_str)

        set_key('.env', 'first_run', 'false')
        print("Instaling done!")

@app.errorhandler(404)
def page_not_found(error):
    return render_template('/fe/404.html')

@app.errorhandler(400)
def page_not_found(error):
    return render_template('/fe/400.html')

if __name__ == '__main__':    
    with app.app_context():
        db.create_all()
        install()
        net.init()
        dns_block_first('load')
        # filter_interface_ips_load()
    app.run(debug=True, host=uri, port=port, threaded=True)
