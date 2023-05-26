# AutoVPNGate_Linux
Automatically obtain openvpn configuration from [VPNGate.net](https://www.vpngate.net/) and auto-detect and replace. 

Linux only.
<br>
<br>

## Introduce

By default this automatically fetches the openvpn list from [VPNGate.net](https://www.vpngate.net/).
<br>
<br>

Then get a openvpn config from the condition you specify, for example:
```
get_openvpn_config_from_vpngate(country_short='KR', min_uptime=1000, choice_column=Ping, sort_by = 'lower', select_by=random, random_range=5)
```
That is to select the column whose country is KR and whose online time is greater than 1000, sort by ping value, the lower, the better, randomly select one of the lowest 5.

```
get_openvpn_config_from_vpngate(country_short='US', min_uptime=100, choice_column=Score, sort_by = 'higher', select_by=fixed)
``` 
That is to select the column whose country is US and whose online time is greater than 100, sort by Score value, the higher, the better, select the highest one
<br>
<br>

VPN availability is detected via ICMP ping and https GET every 60 seconds, and if unavailable, it is automatically reacquired and deployed.

Adds route-nopull to the openvpn config file by default to let you choose which routes you want to add.
<br>
<br>

Check `route_add()` Then add your own routes, or remove `os.system(f'grep route-nopull {openvpn_conf_path} || echo route-nopull >> {openvpn_conf_path}')` and let openvpn manage routes automatically.
<br>
<br>

`run_command_with_cleanup()` can record a set of relative commands, such as
```
run_command_with_cleanup(ip route add, ip route delete)
```
It will execute when executing, `ip route add`, and then execute `ip route delete` at the end of the program(SIGINT, SIGTERM).
<br>
<br>

## Require
- Python 3.6.8 or higher
- OpenVPN 2.4.12 or higher
- iproute2-ss170501 or  higher
- curl 7.29.0 or higher
- OpenVPN is configured with systemd and can be started with `systemctl start openvpn-client@<conf>`
<br>
<br>

## Quick start
- Run `git clone --recursive https://github.com/10935336/AutoVPNGate_Linux.git`
- Check and change the `if __name__ == '__main__':` variable in `main.py` to your liking.
- Check `route_add()` Then add your own routes, or remove `os.system(f'grep route-nopull {openvpn_conf_path} || echo route-nopull >> {openvpn_conf_path}')` and let openvpn manage routes automatically.
- Run `python3 main.py`
<br>
<br>

## library reference
When VPNGate API is not available, use this way to get csv.
- https://github.com/hoang-rio/vpn-gate-openvpn-udp
- Author： [hoang-rio](https://github.com/hoang-rio) 
- License: [MIT License](https://github.com/hoang-rio/vpn-gate-openvpn-udp/blob/master/LICENSE)
