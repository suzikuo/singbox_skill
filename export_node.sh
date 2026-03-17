#!/bin/bash

CONF_DIR="/etc/sing-box/conf"
OUTPUT_FILE="./node"

echo "开始扫描目录: $CONF_DIR"
> "$OUTPUT_FILE"

for file in "$CONF_DIR"/*.json; do
    [ -f "$file" ] || continue
    echo "处理文件: $file"

    protocol=$(jq -r '.inbounds[0].type' "$file" 2>/dev/null)
    port=$(jq -r '.inbounds[0].listen_port' "$file" 2>/dev/null)
    password=$(jq -r '.inbounds[0].users[0].password // .inbounds[0].users[0].uuid' "$file" 2>/dev/null)
    server=$(curl -s ifconfig.me)

    case "$protocol" in
        hysteria2)
            echo "hysteria2://$password@$server:$port?insecure=1#$(basename "$file" .json)" >> "$OUTPUT_FILE"
            ;;
        trojan)
            echo "trojan://$password@$server:$port#$(basename "$file" .json)" >> "$OUTPUT_FILE"
            ;;
        vless)
            echo "vless://$password@$server:$port?security=reality&type=tcp#$(basename "$file" .json)" >> "$OUTPUT_FILE"
            ;;
        vmess)
            echo "vmess://$password@$server:$port#$(basename "$file" .json)" >> "$OUTPUT_FILE"
            ;;
        *)
            echo "未知协议: $protocol"
            ;;
    esac

done

sort -u -o "$OUTPUT_FILE" "$OUTPUT_FILE"

echo "完成，节点已写入 $OUTPUT_FILE"