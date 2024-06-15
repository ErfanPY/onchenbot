import json
import os
import random
import sys
import time
from base64 import b64decode
from urllib.parse import unquote

import requests
from colorama import *

init(autoreset=True)

merah = Fore.LIGHTRED_EX
putih = Fore.LIGHTWHITE_EX
hijau = Fore.LIGHTGREEN_EX
kuning = Fore.LIGHTYELLOW_EX
biru = Fore.LIGHTBLUE_EX
reset = Style.RESET_ALL


class ConfigModel:
    def __init__(
        self,
        interval: int,
        sleep: int,
        min_energy: int,
        start_range: int,
        end_range: int,
    ):
        self.interval = interval
        self.sleep = sleep
        self.min_energy = min_energy
        self.start_range = start_range
        self.end_range = end_range


class Tapper:
    def __init__(self, tg_client):
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.5",
            "content-type": "application/json",
            "origin": "https://db4.onchaincoin.io",
            "referer": "https://db4.onchaincoin.io/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "te": "trailers",
        }
        self.has_recovery = False

    def log(self, message):
        year, mon, day, hour, minute, second, a, b, c = time.localtime()
        mon = str(mon).zfill(2)
        hour = str(hour).zfill(2)
        minute = str(minute).zfill(2)
        second = str(second).zfill(2)
        print(f"{biru}[{year}-{mon}-{day} {hour}:{minute}:{second}] {message}")

    def parse_data(self, data):
        output = {}

        for i in unquote(data).split("&"):
            key, value = i.split("=")
            output[key] = value

        return output

    def is_expired(self, token):
        header, payload, sign = token.split(".")
        depayload = b64decode(payload + "==").decode("utf-8")
        jepayload = json.loads(depayload)
        exp = jepayload["exp"]
        now = int(time.time())
        if now > int(exp):
            return True

        return False

    def run(self):
        token, tg_web_data, cfg = self.read_config_files()

        if self.is_expired(token):
            self.log(f"{kuning}token is expired !")
            self.login(tg_web_data)

        self.get_me(token)
        print("~" * 50)
        while True:
            if self.is_expired(token):
                self.login(tg_web_data)

            self.click(token, cfg)
            print("~" * 50)
            self.countdown(cfg.interval)

    def read_config_files(self):
        banner = f"""
    {putih}AUTO TAP-TAP {hijau}ONCHAIN BOT 
    {putih}By: {hijau}t.me/AkasakaID
    {putih}Github: {hijau}@AkasakaID
    {hijau}Message: {putih}Don't forget to 'git pull' maybe i update the bot !
        """

        if len(sys.argv) <= 1:
            os.system("cls" if os.name == "nt" else "clear")
        print(banner)

        if not os.path.exists("data"):
            self.log(f"{merah}'data' file is not found !")
            open("data", "a")

        tg_web_data = self.read_data()
        if len(tg_web_data) <= 0:
            self.log(f"{kuning}please fill 'data' file with your telegram data !")
            sys.exit()

        tg_web_data = self.read_data(0)

        if not os.path.exists("token"):
            self.log(f"{kuning}token file is not found !")
            open("token", "a")

        ua = open("user-agent", "r").read().splitlines()[0]
        if ua.find("#") >= 0:
            self.log(f"{kuning}please, fill your user-agent to user-agent file !")
            sys.exit()

        self.headers["user-agent"] = ua

        token = self.read_token()
        if len(token) <= 0:
            self.login(tg_web_data)
            token = self.read_token(0)

        token = self.read_token(0)

        config = json.loads(open("config.json").read())
        interval = config["interval"]
        sleep = config["sleep"]
        min_energy = config["min_energy"]
        click_range = config["click_range"]
        start = click_range["start"]
        end = click_range["end"]

        if int(start) > int(end):
            self.log(
                f"{merah}the value of click range end must be higher than start value !"
            )
            sys.exit()

        cfg = ConfigModel(interval, sleep, min_energy, start, end)

        return token, tg_web_data, cfg

    def get_me(self, token, show_name=False):
        headers = self.headers
        headers["authorization"] = f"Bearer {token}"
        res = self.http("https://db4.onchaincoin.io/api/info", headers)
        if '"success":true' in res.text:
            name = res.json()["user"]["fullName"]
            clicks = res.json()["user"]["clicks"]
            energy = res.json()["user"]["energy"]
            refill = res.json()["user"]["dailyEnergyRefill"]
            if refill >= 1:
                self.has_recovery = True

            self.log(f"{hijau}login as : {putih}{name}")
            return True

        self.log(
            f"{merah}failed fetch data info !, http status code : {kuning}{res.status_code}"
        )
        if res.status_code == 429:
            self.countdown(30 * 60)
        return False

    def click(self, token: str, cfg: ConfigModel):
        _click = random.randint(cfg.start_range, cfg.end_range)
        data = {"clicks": min(_click, self.last_energy)}
        headers = self.headers
        headers["authorization"] = f"Bearer {token}"
        headers["content-length"] = str(len(json.dumps(data)))
        res = self.http(
            "https://db4.onchaincoin.io/api/klick/myself/click",
            headers,
            json.dumps(data),
        )
        if "Insufficient energy" in res.text:
            self.log(f"{kuning}Insufficient energy")
            self.countdown(cfg.sleep)
            return True

        if '"clicks"' in res.text:
            clicks = res.json()["clicks"]
            energy = res.json()["energy"]
            coins = res.json()["coins"]
            self.last_energy = int(energy)
            self.log(f"{hijau}total click : {putih}{clicks}")
            self.log(f"{hijau}total coin : {putih}{coins}")
            self.log(f"{hijau}remaining energy : {putih}{energy}")
            if cfg.min_energy >= int(energy):
                if self.has_recovery:
                    headers["content-length"] = str(len(json.dumps({})))
                    self.http(
                        "https://db4.onchaincoin.io/api/boosts/energy",
                        headers=headers,
                        data=json.dumps({}),
                    )
                    self.has_recovery = False
                    return True

                self.countdown(cfg.sleep)

            return True

        self.log(
            f"{merah}failed to click, http status code : {kuning}{res.status_code}"
        )
        if res.status_code == 429:
            self.countdown(30 * 60)
        return False

    def login(self, data):
        data = {"hash": data}
        headers = self.headers
        headers["content-length"] = str(len(json.dumps(data)))
        while True:
            res = self.http(
                "https://db4.onchaincoin.io/api/validate", headers, json.dumps(data)
            )
            if '"success":true' in res.text:
                token = res.json()["token"]
                self.log(f"{hijau}success login !")
                open("token", "w").write(token)
                return True

            self.log(
                f"{merah}failed login with http status code : {kuning}{res.status_code}"
            )
            if res.status_code == 429:
                self.countdown(30 * 60)
            self.log(f"{kuning}trying login again !")
            continue

    def http(self, url, headers: dict, data=None):
        while True:
            try:
                if data is None:
                    headers["content-length"] = "0"
                    res = requests.get(url, headers=headers)
                    open(".http_request.log", "a").write(res.text + "\n")
                    return res

                res = requests.post(url, headers=headers, data=data)
                open(".http_request.log", "a").write(res.text + "\n")
                return res
            except KeyboardInterrupt:
                self.log(f"{merah}connection error !")


async def run_tapper(tg_client: Client):
    try:
        await Tapper(tg_client=tg_client).run()
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")


if __name__ == "__main__":
    try:
        app = Tapper()
        app.run()
    except KeyboardInterrupt:
        sys.exit()
