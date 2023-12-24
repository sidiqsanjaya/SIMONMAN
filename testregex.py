import subprocess
import json
import netdata
def get_speedtest_results():
    # Jalankan speedtest dan dapatkan hasil dalam format JSON
    result = subprocess.run(["speedtest", "--json"], capture_output=True, text=True)

    # Pastikan perintah berhasil dijalankan
    if result.returncode != 0:
        print(f"Error running speedtest: {result.stderr}")
        return None

    # Parse hasil JSON
    data = json.loads(result.stdout)

    return data

# Gunakan fungsi di atas
data = get_speedtest_results()
if data is not None:
    print(data)  # Cetak seluruh data
    print(data["download"])  # Cetak kecepatan download saja
