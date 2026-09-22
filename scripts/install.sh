#!/bin/sh
set -eu

CODEX_HOME=${CODEX_HOME:-"$HOME/.codex"}
SKILL_NAME=modbapi-imagegen
SECRETS_DIR="$CODEX_HOME/secrets"
CONFIG_FILE="$SECRETS_DIR/$SKILL_NAME.env"
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

if [ -t 0 ]; then
  printf '请输入 modbapi API Key（输入内容不会显示）： ' >&2
  stty -echo
  IFS= read -r API_KEY
  stty echo
  printf '\n' >&2
else
  printf '%s\n' '未检测到交互式输入。请设置 MODBAPI_API_KEY 后重新运行安装器。' >&2
  exit 2
fi

if [ -z "$API_KEY" ]; then
  printf '%s\n' 'API Key 不能为空。' >&2
  exit 2
fi

umask 077
printf 'MODBAPI_API_KEY=%s\n' "$API_KEY" > "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"
printf '已保存到本机安全配置：%s\n' "$CONFIG_FILE" >&2
printf '%s\n' '请重新打开 Codex 客户端，或在当前 shell 中执行：' >&2
printf 'export MODBAPI_API_KEY_FILE=%s\n' "$CONFIG_FILE" >&2
