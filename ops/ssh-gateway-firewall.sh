#!/bin/sh
# Keep the public SSH gateway's known abusive sources and connection rate bounded.
set -eu

iptables -w -nL DOCKER-USER >/dev/null

for ip in 5.231.242.53 5.231.242.181 5.231.242.185; do
    if ! iptables -w -C DOCKER-USER -s "$ip" -p tcp --dport 2222 \
        -j REJECT --reject-with tcp-reset 2>/dev/null; then
        iptables -w -I DOCKER-USER 1 -s "$ip" -p tcp --dport 2222 \
            -j REJECT --reject-with tcp-reset
    fi
done

if ! iptables -w -C DOCKER-USER -p tcp --dport 2222 \
    -m conntrack --ctstate NEW \
    -m connlimit --connlimit-above 24 --connlimit-mask 32 --connlimit-saddr \
    -j REJECT --reject-with tcp-reset 2>/dev/null; then
    iptables -w -I DOCKER-USER 4 -p tcp --dport 2222 \
        -m conntrack --ctstate NEW \
        -m connlimit --connlimit-above 24 --connlimit-mask 32 --connlimit-saddr \
        -j REJECT --reject-with tcp-reset
fi

if ! iptables -w -C DOCKER-USER -p tcp --dport 2222 \
    -m conntrack --ctstate NEW \
    -m hashlimit --hashlimit-above 150/minute --hashlimit-burst 50 \
    --hashlimit-mode srcip --hashlimit-name frp_ssh_ip_v2 \
    -j REJECT --reject-with tcp-reset 2>/dev/null; then
    iptables -w -I DOCKER-USER 5 -p tcp --dport 2222 \
        -m conntrack --ctstate NEW \
        -m hashlimit --hashlimit-above 150/minute --hashlimit-burst 50 \
        --hashlimit-mode srcip --hashlimit-name frp_ssh_ip_v2 \
        -j REJECT --reject-with tcp-reset
fi

if ! iptables -w -C DOCKER-USER -p tcp --dport 2222 \
    -m conntrack --ctstate NEW \
    -m hashlimit --hashlimit-above 240/minute --hashlimit-burst 80 \
    --hashlimit-mode dstport --hashlimit-name frp_ssh_all_v2 \
    -j REJECT --reject-with tcp-reset 2>/dev/null; then
    iptables -w -I DOCKER-USER 6 -p tcp --dport 2222 \
        -m conntrack --ctstate NEW \
        -m hashlimit --hashlimit-above 240/minute --hashlimit-burst 80 \
        --hashlimit-mode dstport --hashlimit-name frp_ssh_all_v2 \
        -j REJECT --reject-with tcp-reset
fi
