import base64
import json
import os

import requests
import yaml

CONF_DIR = "/etc/sing-box/conf"
OUTPUT = "/home/ec2-user/clash.yaml"
BASE64_OUTPUT = "/home/ec2-user/clash_base64.txt"


def get_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except:
        return "127.0.0.1"


server_ip = get_ip()

proxies = []
node_names = []

for file in os.listdir(CONF_DIR):
    if not file.endswith(".json"):
        continue

    path = os.path.join(CONF_DIR, file)

    with open(path) as f:
        data = json.load(f)

    inbound = data["inbounds"][0]

    name = file.replace(".json", "")
    node_names.append(name)

    p = {"name": name, "server": server_ip, "port": inbound["listen_port"]}

    t = inbound["type"]

    users = inbound.get("users", [{}])[0]

    transport = inbound.get("transport", {}).get("type")
    path = inbound.get("transport", {}).get("path", "")

    tls = inbound.get("tls", {})

    if t == "vmess":
        p.update({"type": "vmess", "uuid": users.get("uuid"), "alterId": 0, "cipher": "auto"})

    elif t == "vless":
        p.update({"type": "vless", "uuid": users.get("uuid")})

    elif t == "trojan":
        p.update({"type": "trojan", "password": users.get("password")})

    elif t == "hysteria2":
        p.update({"type": "hysteria2", "password": users.get("password"), "sni": tls.get("server_name", server_ip), "skip-cert-verify": True})

    elif t == "shadowsocks":
        p.update({"type": "ss", "cipher": inbound.get("method"), "password": users.get("password")})

    elif t == "socks":
        p.update({"type": "socks5"})

    if tls.get("enabled") and t not in ["hysteria2"]:
        p["tls"] = True
        p["servername"] = tls.get("server_name", server_ip)
        p["skip-cert-verify"] = True

    if transport == "ws":
        p["network"] = "ws"
        p["ws-opts"] = {"path": path}

    if transport == "http":
        p["network"] = "http"
        p["http-opts"] = {"path": [path]}

    if transport == "h2":
        p["network"] = "h2"

    reality = tls.get("reality")

    if reality:
        p["reality-opts"] = {"public-key": reality.get("public_key")}

    proxies.append(p)

config = {
    "proxies": proxies,
    "proxy-groups": [
        {"name": "🚀 节点选择", "type": "select", "proxies": node_names},
        {"name": "🌍 代理模式", "type": "select", "proxies": ["绕过大陆", "全局代理", "DIRECT"]},
        {"name": "绕过大陆", "type": "select", "proxies": ["🚀 节点选择", "DIRECT"]},
        {"name": "全局代理", "type": "select", "proxies": ["🚀 节点选择"]},
    ],
    "rules": ["GEOIP,CN,DIRECT", "GEOSITE,CN,DIRECT", "MATCH,🌍 代理模式"],
}

with open(OUTPUT, "w") as f:
    yaml.dump(config, f, allow_unicode=True)

with open(OUTPUT, "rb") as f:
    encoded = base64.b64encode(f.read()).decode()

with open(BASE64_OUTPUT, "w") as f:
    f.write(encoded)

print("生成完成")
print("clash.yaml 已生成")
