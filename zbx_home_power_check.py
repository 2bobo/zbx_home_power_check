import json
import base64
import configparser
import socket
import struct
import time
import datetime
import re
import requests
from requests.auth import HTTPDigestAuth
from lxml import html


class ZabbixSender(object):
    """Zabbix Sender クラス
    ZabbixSenderを利用可能にするクラス
    """

    def __init__(self, server="127.0.0.1", port="10051"):
        """
        データを送信するZabbixサーバーの情報を指定

        Args:
            server (str): ZabbixServerのIP/hostname(デフォルト値:127.0.0.1)
            port (ste): Zabbixのポート番号(デフォルト値:10051)
        """

        self.server = server
        self.port = port
        self.zbx_sender_data = {u"request": u"sender data", u"data": []}

    def add(self, host, key, value, clock=None):
        """データ追加関数
        ZabbixSenderで送信するデータを追加する関数

        Args:
            host (str): Zabbixホスト名
            key (str): 送信するアイテムのキー
            value (str): 送信するアイテムの値
            clock (int):

        Returns: None

        """
        if clock is None:
            clock = datetime.datetime.now().timestamp()

        data = {"host": str(host),
                "key": str(key),
                "value": str(value),
                "clock": int(clock)
                }
        self.zbx_sender_data["data"].append(data)

    def lldadd(self, host, key, value):
        """データ追加関数
        ZabbixSenderで送信するデータを追加する関数

        Args:
            host (str): Zabbixホスト名
            key (str): 送信するアイテムのキー
            value (str): 送信するアイテムの値

        Returns: None

        """

        lld_data = {"host": str(host),
                "key": str(key),
                "value": str(value),
                }
        self.zbx_sender_data["data"].append(lld_data)

    def clean_packet(self):
        """データクリア関数
        addで追加されたデータをすべて削除する関数

        Args: None
        Returns: None

        """

        self.zbx_sender_data = {u"request": u"sender data", u"data": []}

    def send(self):
        """送信関数
        addされたデータをZabbixへ送信する関数

        Args: None
        Returns:
            json: 送信結果データ

        """
        # s = socket.socket()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((self.server, int(self.port)))
        except Exception as e:
            print(e)
        data = str(json.dumps(self.zbx_sender_data)).encode("utf-8")
        packet = b"ZBXD\1" + struct.pack('<Q', len(data)) + data
        s.send(packet)
        time.sleep(1)

        status = s.recv(1024).decode("utf-8")
        re_status = re.compile("(\{.*\})")
        status = re_status.search(status).groups()[0]

        self.clean_packet()
        s.close()

        return status
        #return json.loads(status)



def main():
    # config読み込み
    config_ini = configparser.ConfigParser()
    config_ini.read("config2.ini", encoding="utf-8")
    AiSEG2_user = config_ini["AiSEG2"]["User"]
    AiSEG2_password = config_ini["AiSEG2"]["Password"]
    AiSEG2_host = config_ini["AiSEG2"]["Host"]

    Zabbix_server = config_ini["Zabbix"]["Server"]
    Zabbix_port = config_ini["Zabbix"]["Port"]
    Zabbix_hostname = config_ini["Zabbix"]["HostName"]

    zbx_sender = ZabbixSender(Zabbix_server, Zabbix_port)
    # zbx_sender.add("host", "key", "value")
    # result = zbx_sender.send()

    # 今日の使用電力量
    url = "http://" + AiSEG2_host + "/page/graph/52111"
    response = requests.get(url, auth=HTTPDigestAuth(AiSEG2_user, AiSEG2_password))
    root = html.fromstring(response.content)
    print("今日の使用電力量: " + root.xpath('//span[@id="val_kwh"]')[0].text + "kwh")
    zbx_sender.add(Zabbix_hostname, "AiSEG.today.power.consumption", root.xpath('//span[@id="val_kwh"]')[0].text)
    result = zbx_sender.send()
    print(result)


    # 今日の買電量
    url = "http://" + AiSEG2_host + "/page/graph/53111"
    response = requests.get(url, auth=HTTPDigestAuth(AiSEG2_user, AiSEG2_password))
    root = html.fromstring(response.content)
    print("今日の買電量: " + root.xpath('//span[@id="val_kwh"]')[0].text + "kwh")
    zbx_sender.add(Zabbix_hostname, "AiSEG.today.power.purchase", root.xpath('//span[@id="val_kwh"]')[0].text)
    result = zbx_sender.send()
    print(result)

    # 今日の売電量
    url = "http://" + AiSEG2_host + "/page/graph/54111"
    response = requests.get(url, auth=HTTPDigestAuth(AiSEG2_user, AiSEG2_password))
    root = html.fromstring(response.content)
    print("今日の売電量: " + root.xpath('//span[@id="val_kwh"]')[0].text + "kwh")
    zbx_sender.add(Zabbix_hostname, "AiSEG.today.power.sales", root.xpath('//span[@id="val_kwh"]')[0].text)
    result = zbx_sender.send()
    print(result)

    # 今日の発電量
    url = "http://" + AiSEG2_host + "/page/graph/51111"
    response = requests.get(url, auth=HTTPDigestAuth(AiSEG2_user, AiSEG2_password))
    root = html.fromstring(response.content)
    print("今日の発電量: " + root.xpath('//span[@id="val_kwh"]')[0].text + "kwh")
    zbx_sender.add(Zabbix_hostname, "AiSEG.today.power.generation", root.xpath('//span[@id="val_kwh"]')[0].text)
    result = zbx_sender.send()
    print(result)


    # 計測回路ごとの使用電力量
    url = "http://" + AiSEG2_host + "/page/setting/installation/734"
    response = requests.get(url, auth=HTTPDigestAuth(AiSEG2_user, AiSEG2_password))
    root = html.fromstring(response.content)
    elements = root.xpath('//script[contains(text(), "window.onload")]')
    circuit_list = []

    for element in elements:
        index = element.text.index("(") + 1
        rindex = element.text.rindex(")")
        json_text = element.text[index:rindex]
        json_dict = json.loads(json_text)
        for circuit in json_dict["arrayCircuitNameList"]:
            if (circuit["strBtnType"] == "1"):
                params_dict = {"circuitid": circuit["strId"]}
                url = "http://" + AiSEG2_host + "/page/graph/584?data=" + base64.b64encode(
                    json.dumps(params_dict).encode()).decode()
                response = requests.get(url, auth=HTTPDigestAuth(user, password))
                root = html.fromstring(response.content)
                print(circuit["strId"].rjust(2) + ": " + root.xpath('//span[@id="val_kwh"]')[0].text + "kwh" + " " + circuit["strCircuit"])
                circuit_list.add = {"id": circuit["strId"].rjust(2), "name": circuit["strCircuit"], "power": root.xpath('//span[@id="val_kwh"]')[0].text}
    print(circuit_list)
    # LLD send
    zbx_sender.lldadd(Zabbix_hostname, "consumption.circuit.discovery", value)



if __name__ == "__main__":
    main()