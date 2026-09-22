# 在 ChatGPT / Codex 中安装

## 推荐的安装提示词

将下列内容发送给支持 Codex Skills 的 ChatGPT / Codex 客户端：

```text
请安装 GitHub 仓库 git@github-mb:ModbApi/modbapi-imagegen.git 中的 Codex Skill。
安装完成后运行仓库里的 scripts/install.sh，并使用安全的隐藏输入提示我输入 modbapi API Key；将 Key 保存为本机 $CODEX_HOME/secrets/modbapi-imagegen.env（权限 600），不要写入仓库、SKILL.md、README、日志、聊天记录、命令历史或任何回复。
安装后验证 $modbapi-imagegen 可用，并提示我使用它生成一张测试图片。
```

客户端应显示类似：

```text
请输入 modbapi API Key（输入内容不会显示）：
```

安装器会把 Key 写入当前机器的 Codex 私有配置目录，而不是 GitHub 仓库。脚本会自动读取该配置文件；也可以设置 `MODBAPI_API_KEY` 覆盖它。

> 是否能在“聊天消息”中直接执行安装，取决于客户端是否提供本地文件和命令执行能力。这个仓库同时提供下面的终端安装方式，结果一致。

## 终端安装

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone git@github-mb:ModbApi/modbapi-imagegen.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/modbapi-imagegen"
"${CODEX_HOME:-$HOME/.codex}/skills/modbapi-imagegen/scripts/install.sh"
```

安装器会隐藏输入 API Key，并写入：

```text
$CODEX_HOME/secrets/modbapi-imagegen.env
```

之后重新打开 Codex 客户端：

```text
使用 $modbapi-imagegen 生成一张：一只猫坐在赛博朋克风格的窗边。
```
