# SIMONMAN [system monitoring manager]
an openwrt monitoring manager application

### list of features that will be available
- [x] hotspot manager [OpenNDS] (need fix, over busy server) {works also with moodle API for user login}
  - [x] admin
  - [x] users
  - [x] user profiles
  - [x] active
  - [x] walled garden
  - [x] custom login page
- [x] Realtime Flow and history on web base [netdata] (done)
  - [x] overview
  - [x] realtime flow
  - [x] history
- [x] Url Logger [DNSmasq]
- [ ] security (idk, but still working)
  - [ ] firewall
  - [ ] TTL rule
- [x] service for monitoring device [search port and check]
- [x] network config (same like default openwrt) on web [speedtest cli]
  - [x] speedtest
  - [ ] interface, routing, dhcp and dns, firewall
- [ ] loadbalance and split traffic [Mwan3] (split traffic still going)
  - [ ] multi wan
  - [ ] flow control
  - [ ] app control (need librarry app, idk where to get)
- [ ] parent control for some vlan or ips
- [ ] web filter
- [ ] allow spesific web filter


### what i need improv or fix
- cannot reboot or shutdown when flask running
- improv netfilter on sysnctl when huge user
- huge db storage for 2 month like 600MB (because it saves data every 5 seconds)

You can request features if can be added ya wkwk
database using sqlite, but you can use like mysql or mariadb if you like

### preview
![image](https://github.com/sidiqsanjaya/SIMONMAN/assets/44673223/e194320c-f00c-44d3-8e79-016c13dbc1a8)
![image](https://github.com/sidiqsanjaya/SIMONMAN/assets/44673223/4f65b052-7dfb-42cb-9f51-a4b508ad1233)
![image](https://github.com/sidiqsanjaya/SIMONMAN/assets/44673223/8b7e2215-6365-4553-9784-b81a9746e6f4)
![image](https://github.com/sidiqsanjaya/SIMONMAN/assets/44673223/d0bbbb88-3588-4c13-9a0d-d0bcd6ddfe22)
![image](https://github.com/sidiqsanjaya/SIMONMAN/assets/44673223/6e1e9364-98b6-4adf-8b9a-e9f8a73cfd2f)
![image](https://github.com/sidiqsanjaya/SIMONMAN/assets/44673223/3d022581-3e41-4349-8efe-2ba9c88f009d)
![image](https://github.com/sidiqsanjaya/SIMONMAN/assets/44673223/a0053eda-2c05-4fd4-b74a-18a7e8b6f181)












