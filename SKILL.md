sing-box script v1.15 by 233boy
Usage: sing-box [options]... [args]...
配置(订阅)文件存储目录：/etc/sing-box/conf/
查看订阅链接时，你应该先查看配置文件有哪些，然后再遍历sb -i [conf_name]
协议:

 1) TUIC
 2) Trojan
 3) Hysteria2
 4) VMess-WS
 5) VMess-TCP
 6) VMess-HTTP
 7) VMess-QUIC
 8) Shadowsocks
 9) VMess-H2-TLS
10) VMess-WS-TLS
11) VLESS-H2-TLS
12) VLESS-WS-TLS
13) Trojan-H2-TLS
14) Trojan-WS-TLS
15) VMess-HTTPUpgrade-TLS
16) VLESS-HTTPUpgrade-TLS
17) Trojan-HTTPUpgrade-TLS
18) VLESS-REALITY
19) VLESS-HTTP2-REALITY
20) Socks

基本:
   v, version                                      显示当前版本
   ip                                              返回当前主机的 IP
   pbk                                             同等于 sing-box generate reality-keypair
   get-port                                        返回一个可用的端口
   ss2022                                          返回一个可用于 Shadowsocks 2022 的密码

一般:
   a, add [protocol] [args... | auto]              添加配置
   c, change [name] [option] [args... | auto]      更改配置
   d, del [name]                                   删除配置**
   i, info [name]                                  查看配置
   qr [name]                                       二维码信息
   url [name]                                      URL 信息
   log                                             查看日志
更改:
   full [name] [...]                               更改多个参数
   id [name] [uuid | auto]                         更改 UUID
   host [name] [domain]                            更改域名
   port [name] [port | auto]                       更改端口
   path [name] [path | auto]                       更改路径
   passwd [name] [password | auto]                 更改密码
   key [name] [Private key | atuo] [Public key]    更改密钥
   method [name] [method | auto]                   更改加密方式
   sni [name] [ ip | domain]                       更改 serverName
   new [name] [...]                                更改协议
   web [name] [domain]                             更改伪装网站

进阶:
   dns [...]                                       设置 DNS
   dd, ddel [name...]                              删除多个配置**
   fix [name]                                      修复一个配置
   fix-all                                         修复全部配置
   fix-caddyfile                                   修复 Caddyfile
   fix-config.json                                 修复 config.json
   import                                          导入 xray/v2ray 脚本配置

管理:
   un, uninstall                                   卸载
   u, update [core | sh | caddy] [ver]             更新
   U, update.sh                                    更新脚本
   s, status                                       运行状态
   start, stop, restart [caddy]                    启动, 停止, 重启
   t, test                                         测试运行
   reinstall                                       重装脚本

测试:
   debug [name]                                    显示一些 debug 信息, 仅供参考
   gen [...]                                       同等于 add, 但只显示 JSON 内容, 不创建文件, 测试使用
   no-auto-tls [...]                               同等于 add, 但禁止自动配置 TLS, 可用于 *TLS 相关协议
其他:
   bbr                                             启用 BBR, 如果支持
   bin [...]                                       运行 sing-box 命令, 例如: sing-box bin help
   [...] [...]                                     兼容绝大多数的 sing-box 命令, 例如: sing-box generate uuid
   h, help                                         显示此帮助界面

扩展脚本 (独立运行):
   bash export_node.sh                             扫描配置目录并批量导出所有节点分享链接到 ./node 文件
   python3 export_clash.py                         导出节点信息为 Clash 订阅/配置格式