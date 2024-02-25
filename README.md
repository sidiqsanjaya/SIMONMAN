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
