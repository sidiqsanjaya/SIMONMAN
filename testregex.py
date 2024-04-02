import socket

def get_ip_addresses(domain):
    try:
        ip_addresses = socket.gethostbyname_ex(domain)[-1]
        return ip_addresses
    except socket.gaierror:
        print(f"DNS lookup failed for {domain}")
        return []

def main():
    domains = ["facebook.com", "google.com"]  # Ganti dengan daftar domain dan subdomain yang Anda inginkan

    ip_set = set()
    for domain in domains:
        ips = get_ip_addresses(domain)
        ip_set.update(ips)

    print("List of IP addresses:")
    for ip in ip_set:
        print(ip)

if __name__ == "__main__":
    main()