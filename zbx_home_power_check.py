import json
import base64
import configparser
import os
import socket
import struct
import time
import datetime
import re
import requests
from requests.auth import HTTPDigestAuth
from lxml import html
from zabbix_utils import Sender, ItemValue

def get_power_summary(config_ini, zbx_sender):
    # 今日の使用電力量
    url = "http://" + config_ini["AiSEG2"]["Host"] + "/page/graph/52111"
    response = requests.get(url, auth=HTTPDigestAuth(config_ini["AiSEG2"]["User"], config_ini["AiSEG2"]["Password"]))
    root = html.fromstring(response.content)
    zbx_sender.send_value(config_ini["Zabbix"]["HostName"], "AiSEG.today.power.consumption", root.xpath('//span[@id="val_kwh"]')[0].text)

    # 今日の買電量
    url = "http://" + config_ini["AiSEG2"]["Host"] + "/page/graph/53111"
    response = requests.get(url, auth=HTTPDigestAuth(config_ini["AiSEG2"]["User"], config_ini["AiSEG2"]["Password"]))
    root = html.fromstring(response.content)
    zbx_sender.send_value(config_ini["Zabbix"]["HostName"], "AiSEG.today.power.purchase", root.xpath('//span[@id="val_kwh"]')[0].text)

    # 今日の売電量
    url = "http://" + config_ini["AiSEG2"]["Host"] + "/page/graph/54111"
    response = requests.get(url, auth=HTTPDigestAuth(config_ini["AiSEG2"]["User"], config_ini["AiSEG2"]["Password"]))
    root = html.fromstring(response.content)
    zbx_sender.send_value(config_ini["Zabbix"]["HostName"], "AiSEG.today.power.sales", root.xpath('//span[@id="val_kwh"]')[0].text)

    # 今日の発電量
    url = "http://" + config_ini["AiSEG2"]["Host"] + "/page/graph/51111"
    response = requests.get(url, auth=HTTPDigestAuth(config_ini["AiSEG2"]["User"], config_ini["AiSEG2"]["Password"]))
    root = html.fromstring(response.content)
    zbx_sender.send_value(config_ini["Zabbix"]["HostName"], "AiSEG.today.power.generation", root.xpath('//span[@id="val_kwh"]')[0].text)


def get_power_details(config_ini, zbx_sender):
    # 計測回路ごとの使用電力量
    url = "http://" + config_ini["AiSEG2"]["Host"] + "/page/setting/installation/734"
    response = requests.get(url, auth=HTTPDigestAuth(config_ini["AiSEG2"]["User"], config_ini["AiSEG2"]["Password"]))
    root = html.fromstring(response.content)
    elements = root.xpath('//script[contains(text(), "window.onload")]')
    circuit_list = []

    for element in elements:
        index = element.text.index("(") + 1
        rindex = element.text.rindex(")")
        json_text = element.text[index:rindex]
        json_dict = json.loads(json_text)
        for circuit in json_dict["arrayCircuitNameList"]:
            if circuit["strBtnType"] == "1":
                params_dict = {"circuitid": circuit["strId"]}
                url = "http://" + config_ini["AiSEG2"]["Host"] + "/page/graph/584?data=" + base64.b64encode(
                    json.dumps(params_dict).encode()).decode()
                response = requests.get(url, auth=HTTPDigestAuth(config_ini["AiSEG2"]["User"], config_ini["AiSEG2"]["Password"]))
                root = html.fromstring(response.content)
                circuit_list.append({"{#CIRCUITID}": circuit["strId"].rjust(2).strip(), "{#CIRCUITNAME}": circuit["strCircuit"], "power": root.xpath('//span[@id="val_kwh"]')[0].text})

    # LLDsender前処理
    data = json.dumps({'data': circuit_list})

    # LLD送付
    zbx_sender.send_value(config_ini["Zabbix"]["HostName"], "consumption.circuit.discovery", data)

    # データ送付
    items = []
    for data in circuit_list:
        items.append(ItemValue(config_ini["Zabbix"]["HostName"], f"circuit.consumption[{data['{#CIRCUITID}']}]", data["power"]))
    zbx_sender.send(items)


def main():
    # ファイルパス取得
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # config読み込み
    config_ini = configparser.ConfigParser()
    config_ini.read(os.path.join(base_dir, "config.ini"), encoding="utf-8")

    # Zabbix Sender設定
    sender = Sender(server=config_ini["Zabbix"]["Server"], port=int(config_ini["Zabbix"]["Port"]))

    # サマリ取得
    get_power_summary(config_ini, sender)

    # 詳細取得
    get_power_details(config_ini, sender)

if __name__ == "__main__":
    main()
