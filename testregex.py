import re

string = "XIITBSM1"
pattern = re.compile(r'^X')

if pattern.search(string):
    print(f"'X' ditemukan dalam {string}")
else:
    print(f"'X' tidak ditemukan dalam {string}")