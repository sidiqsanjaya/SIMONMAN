import telnetlib

list_ip_ap = [
    '192.168.120.196',
    '192.168.120.245',
    '192.168.120.14',
    '192.168.120.107',
    '192.168.120.113',
    '192.168.120.151',
    '192.168.120.108',
    '192.168.120.159',
    '192.168.120.145',
    '192.168.120.155',
    '192.168.120.56',
    '192.168.120.83',
    '192.168.120.54',
    '192.168.120.220',
    '192.168.120.109',
    '192.168.120.167',
    '192.168.120.176',
    '192.168.120.15',
    '192.168.120.51',
    '192.168.120.208',
    '192.168.120.252',
    '192.168.120.4',
    '192.168.120.69',
    '192.168.120.84',
    '192.168.120.171',
    '192.168.120.185'
]


print('jumlah Ap yang direset : ' + str(len(list_ip_ap)))

port = 23
password = "fVu@43me5D"
command = "apm factory-reset"

print(f"resetting all ap ruijie")
for ip in list_ip_ap:
    try:
        tn = telnetlib.Telnet(ip, port)
        tn.read_until(b"Password: ")
        tn.write(password.encode('utf-8') + b"\n")

        tn.write(command.encode('utf-8') + b"\n")

        output = tn.read_all().decode('utf-8')

        print(f"Output dari {ip}:\n{output}")

        tn.close()

    except Exception as e:
        print(f"Gagal terhubung ke {ip}: {e}")
