#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Function: Automatically fetch openvpn configuration from VPNGate.net and auto-detect and replace
# Note: Linux only
# Author: 10935336
# Creation date: 2023-05-13
# Modified date: 2023-05-14

import base64
import csv
import logging
import os
import re
import signal
import sys
import time
from random import choice

import requests

from vpngate import VPNGate


def run_command_with_cleanup(command, cleanup_command):
    os.system(command)
    cleanup_commands.add(cleanup_command)


def get_openvpn_config_from_vpngate(country_short, min_uptime, choice_column, sort_by='higher', select_by='fixed',
                                    random_range=5):
    """
    Get OPENVPN configuration files from VPNGate.net

    get_vpn_config(country_short='KR', min_uptime=1000, choice_column=Ping, sort_by = 'lower', select_by=random,
    random_range=5)
    That is to select the column whose country is KR and whose online time is greater than 1000,
    sort by ping value, the lower, the better, randomly select one of the lowest 5

    For example, get_vpn_config(country_short='US', min_uptime=100, choice_column=Score, sort_by = 'higher',
    select_by=fixed)
    That is to select the column whose country is US and whose online time is greater than 100,
    sort by Score value, the higher, the better, select the highest one

    You can choose choice_column from here:
    ['HostName', 'IP', 'Score', 'Ping', 'Speed', 'CountryLong', 'CountryShort', 'NumVpnSessions', 'Uptime',
                  'TotalUsers', 'TotalTraffic', 'LogType', 'Operator', 'Message', 'OpenVPN_ConfigData_Base64']

    :return: Type:str base64_openvpn_conf
    """

    def vpngate_selector(csv_data, country_short, min_uptime, choice_column, sort_by='higher', select_by='fixed',
                         random_range=5):
        filtered_rows = []
        for row in csv_data:
            if row['CountryShort'] == country_short and int(row['Uptime']) > min_uptime:
                filtered_rows.append(row)

        if filtered_rows:
            if sort_by == 'higher':
                filtered_rows.sort(key=lambda x: int(x[choice_column]), reverse=True)
            else:
                filtered_rows.sort(key=lambda x: int(x[choice_column]))

            if select_by == 'fixed':
                selected_row = filtered_rows[0]
            else:
                selected_row = choice(filtered_rows[:random_range])

            config_data_base64 = selected_row['OpenVPN_ConfigData_Base64']
            return config_data_base64
        else:
            logging.warning('No matching rows found')
            return None

    def get_openvpn_config_from_vpngate_html():
        # Get an openvpn list from html
        vpngate_base_url = "https://www.vpngate.net"
        csv_file_path = "vpngate.csv"
        sleep_time = 0

        vpngate = VPNGate(vpngate_base_url, csv_file_path, sleep_time)
        vpngate.run()

        with open('vpngate.csv', 'r', encoding='utf-8') as f:
            data = f.read().split('\n')
        fieldnames = [
            '#HostName', 'IP', 'Score', 'Ping', 'Speed', 'CountryLong', 'CountryShort', 'NumVpnSessions',
            'Uptime', 'TotalUsers', 'TotalTraffic', 'LogType', 'Operator', 'Message',
            'OpenVPN_ConfigData_Base64', 'TcpPort', 'UdpPort', 'L2TP', 'SSTP'
        ]
        csv_reader = csv.DictReader(data, fieldnames=fieldnames)

        return csv_reader

    def get_openvpn_config_from_vpngate_api():
        url = 'https://www.vpngate.net/'
        response = requests.get(url)
        data = response.text.split('\n')

        # Check if response is CSV
        if '*vpn_servers\r' in data or '*vpn_servers' in data:
            fieldnames = ['#HostName', 'IP', 'Score', 'Ping', 'Speed', 'CountryLong', 'CountryShort', 'NumVpnSessions',
                          'Uptime',
                          'TotalUsers', 'TotalTraffic', 'LogType', 'Operator', 'Message', 'OpenVPN_ConfigData_Base64']
            csv_reader = csv.DictReader(data, fieldnames=fieldnames)
            return csv_reader
        else:
            logging.warning('VPNGate API did not return CSV')
            return None

    try:
        csv_reader = get_openvpn_config_from_vpngate_api()
        if csv_reader is None:
            logging.warning('Trying get CSV from HTML')
            csv_reader = get_openvpn_config_from_vpngate_html()

        config_data_base64 = vpngate_selector(csv_data=csv_reader, country_short=country_short,
                                              min_uptime=min_uptime, choice_column=choice_column,
                                              sort_by=sort_by, select_by=select_by, random_range=random_range)
    except Exception as error:
        logging.exception(f'Cannot get openvpn conf: {error}')
        config_data_base64 = []

    return config_data_base64


def check_openvpn_connectivity(openvpn_dev_name, test_ip):
    result = os.system(f'ping -c 3 -W 2 {test_ip} -I {openvpn_dev_name} &> /dev/null')
    if result != 0:
        logging.warning('Ping test failed, trying to add route...')
        route_add(openvpn_dev_name, test_ip)
        result = os.system(f'ping -c 3 -W 2 {test_ip} -I {openvpn_dev_name} &> /dev/null')
    return result == 0


def deploy_openvpn_config(config_data_base64, openvpn_conf_name='vpngate_auto',
                          openvpn_dev_name='vpngate_tun_auto'):
    logging.info('Deploying new configuration...')
    openvpn_conf_path = '/etc/openvpn/client/' + openvpn_conf_name + '.conf'

    try:
        config_data = base64.b64decode(config_data_base64).decode('utf-8')

        # change dev name
        config_data = config_data.replace('dev tun', f'dev-type tun\ndev {openvpn_dev_name}')

        with open(openvpn_conf_path, 'w', encoding='utf-8') as f:
            f.write(config_data)

        # Add route-nopull to prevent openvpn from automatically managing routes
        os.system(f'grep route-nopull {openvpn_conf_path} || echo route-nopull >> {openvpn_conf_path}')

    except Exception as error:
        logging.exception(f'Cannot decode config_data: {error}')


def restart_openvpn(openvpn_dev_name, test_ip, openvpn_conf_name='vpngate_auto'):
    logging.info('Restarting OPENVPN...')
    os.system(f'systemctl restart openvpn-client@{openvpn_conf_name}')
    # wait for restart
    time.sleep(10)
    route_add(openvpn_dev_name, test_ip)


def route_add(openvpn_dev_name, test_ip):
    logging.info('Adding route...')

    # Add test_ip route, use it for detection
    run_command_with_cleanup(command=f'ip route add {test_ip} dev {openvpn_dev_name}',
                             cleanup_command=f'ip route delete {test_ip} dev {openvpn_dev_name}')

    # Add route, change it to your own command
    # run_command_with_cleanup(command=f'ip route add default dev {openvpn_dev_name} table 100',cleanup_command=f'ip route delete default dev {openvpn_dev_name} table 100')

    logging.info(f'Route added "ip route add {test_ip} dev {openvpn_dev_name}"')
    logging.info(f'Route added "ip route add default dev {openvpn_dev_name} table 100"')


def get_ip_from_conf(openvpn_conf_name='vpngate_auto'):
    openvpn_conf_path = '/etc/openvpn/client/' + openvpn_conf_name + '.conf'
    try:
        with open(openvpn_conf_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'remote\s+(.+)', content)
            if len(matches) == 0:
                return 'not found'
            else:
                for match in matches:
                    return match
    except Exception:
        return 'not found'


def kill_signal_handler(sig, frame):
    # do not remove sig or frame, even though it is not used
    logging.info(f'{sig} signal received, cleaning...')
    print(f'{sig} signal received, cleaning...')

    os.system(f'systemctl stop openvpn-client@{openvpn_conf_name}')
    logging.info(f'Executed "systemctl stop openvpn-client@{openvpn_conf_name}"')
    print(f'Executed "systemctl stop openvpn-client@{openvpn_conf_name}"')

    # cleanup_commands
    for command in cleanup_commands:
        os.system(command)
        logging.info(f'executed "{command}"')
        print(f'executed "{command}"')

    sys.exit(0)


def setup_logging():
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    data_format = "%Y/%m/%d %H:%M:%S"

    logdir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(logdir, '.', 'autovpngate.log')

    # no encoding in python3.6
    logging.basicConfig(filename=log_path, level=logging.INFO, format=log_format, datefmt=data_format)


if __name__ == '__main__':
    # openvpn device name, no more than 13 bytes
    openvpn_dev_name = 'vpngate_tun0'
    # openvpn configuration file name
    openvpn_conf_name = 'vpngate_auto'
    # test ip, use for ICMP ping detection
    test_ip = '8.8.8.8'
    # Fill in the vpngate-openvpn type to be obtained here,
    # see the get_openvpn_config_from_vpngate() definition for the usage method
    get_openvpn_config_from_vpngate_params = {
        'country_short': 'KR',
        'min_uptime': 1000,
        'choice_column': 'Speed',
        'sort_by': 'higher',
        'select_by': 'random',
        'random_range': 10
    }
    # please check route_add() command

    # Don't touch,record the cleanup command corresponding to the command
    cleanup_commands = set()

    # log
    setup_logging()

    # Perform cleanup after receiving "quit" signal
    signal.signal(signal.SIGINT, kill_signal_handler)
    signal.signal(signal.SIGTERM, kill_signal_handler)

    while True:
        if not check_openvpn_connectivity(openvpn_dev_name, test_ip):
            logging.warning(
                f'VPN connection lost. Obtaining new configuration... Lost ip: "{get_ip_from_conf(openvpn_conf_name)}"')

            config_data = get_openvpn_config_from_vpngate(**get_openvpn_config_from_vpngate_params)

            if config_data:
                logging.info('Obtain new configuration success.')
                deploy_openvpn_config(config_data, openvpn_dev_name=openvpn_dev_name)
                restart_openvpn(openvpn_dev_name, test_ip, openvpn_conf_name=openvpn_conf_name)

                if check_openvpn_connectivity(openvpn_dev_name, test_ip):
                    logging.info(f'VPN connection restored. Current ip: "{get_ip_from_conf(openvpn_conf_name)}"')
                else:
                    logging.error('Failed to restore VPN connection.')
                    continue
            else:
                logging.error('Failed to obtain new configuration.')
                continue
        # Check every 60 seconds
        time.sleep(60)
