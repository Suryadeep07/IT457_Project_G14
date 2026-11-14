#!/bin/bash
set -euxo pipefail
dnf install -y docker
systemctl enable --now docker
TOKEN=$(curl -s -X PUT 'http://169.254.169.254/latest/api/token' -H 'X-aws-ec2-metadata-token-ttl-seconds: 300')
IID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
docker rm -f api || true
docker run -d --name api --restart always -p 80:8000 -e INSTANCE_ID="$IID" suryadeep07/abnb-poc:v2
