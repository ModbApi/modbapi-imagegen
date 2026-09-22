# modbapi-imagegen

让 Codex 通过 [modbapi](https://modbapi.com) 的异步图片任务接口生成或编辑图片，并把完成后的图片 URL 直接显示在 Codex 对话中。

> 这是一个可公开发布的 Codex Skill。它不会把 API Key 写入仓库、技能文件或命令历史。

## 功能

- 文生图：`POST /v1/image-tasks/generations`
- 图生图 / 改图：`POST /v1/image-tasks/edits`
- 自动轮询：`GET /v1/image-tasks/{task_id}?detail=true`
- 处理 `queued`、`in_progress`、`completed`、`failed`、`cancelled`
- 完成后把图片保存到本地并输出绝对路径 Markdown，避免第三方 CDN 域名被客户端拦截而显示失败
- 支持自定义 API 域名、模型、尺寸、质量、超时时间

## 安装

### 方式 A：在 ChatGPT / Codex 中发送安装命令

完整的可复制提示词见 [INSTALL.md](INSTALL.md)。

把下面这句话发送给支持 Codex Skill 安装的 ChatGPT / Codex 客户端（也可直接参考仓库中的 [INSTALL.md](INSTALL.md)）：

```text
安装 GitHub 仓库 https://github.com/ModbApi/modbapi-imagegen.git 中的 Codex Skill，并在安装完成后提示我输入 MODBAPI_API_KEY；将 API Key 安全保存为本机环境变量，不要写入仓库、日志、聊天记录或 SKILL.md，然后用该 Skill 生成一张测试图片。
```

客户端应当在安装后单独提示：

```text
请输入你的 modbapi API Key（输入内容不会显示）：
```

API Key 只保存在本机的 Codex 运行环境中。安装器默认写入 `$CODEX_HOME/secrets/modbapi-imagegen.env` 并设置权限 600；Skill 不支持把 Key 放进公开仓库，也不会在输出中回显 Key。

### 方式 B：手动安装到 Codex Skills 目录

```sh
mkdir -p "$HOME/.codex/skills"
git clone git@github-mb:ModbApi/modbapi-imagegen.git \
  "$HOME/.codex/skills/modbapi-imagegen"
```

设置 API Key：

```sh
export MODBAPI_API_KEY='你的 modbapi API Key'
```

重新打开 Codex 客户端后，输入：

```text
使用 $modbapi-imagegen 生成一张：一只猫坐在赛博朋克风格的窗边。
```

## 配置

| 环境变量 | 必填 | 默认值 | 说明 |
|---|---:|---|---|
| `MODBAPI_API_KEY` | 是 | — | modbapi API Key |
| `MODBAPI_BASE_URL` | 否 | `https://z.modbapi.com` | API 根地址，不要重复添加 `/v1` |

图片默认保存到 `$CODEX_HOME/generated_images/modbapi/`（未设置 `CODEX_HOME` 时使用 `~/.codex/generated_images/modbapi/`）。可用 `--output` 指定项目内路径；只有明确需要旧的远程 URL 展示方式时才使用 `--url-only`。

也可以在本地脚本调用时传入 `--base-url`。API Key 优先从 `MODBAPI_API_KEY` 读取。

## 使用示例

### 生成图片

```sh
python3 scripts/modbapi_imagegen.py \
  --prompt "一只猫坐在赛博朋克风格的窗边" \
  --model "gpt-image-2.5" \
  --size "1024x1024" \
  --quality "high"
```

### 编辑图片

```sh
python3 scripts/modbapi_imagegen.py \
  --edit \
  --image-url "https://example.com/product.png" \
  --prompt "只替换背景为现代办公室，保持产品、边缘、比例、光影和透视不变"
```

多个输入图片可以重复传入 `--image-url`。

### 参数

```text
--prompt              必填，生图或编辑提示词
--model               模型，默认 gpt-image-2.5
--base-url            API 根地址，默认 https://z.modbapi.com
--size                默认 1024x1024
--quality             可选，例如 high
--response-format     url 或 b64_json，默认 url
--output              本地图片文件路径；默认保存到 Codex generated_images 目录
--url-only            不保存本地文件，使用远程 URL 展示（兼容旧行为）
--edit                使用图片编辑任务
--image-url           编辑输入图片 URL，可重复
--interval            轮询间隔秒数，默认 3
--timeout             最大等待秒数，默认 300
```

## API Key 安全说明

- 不要把 API Key 写进 `SKILL.md`、README、脚本、`.env`、截图或 Git 提交。
- 不要把 API Key 放进 URL、图片提示词或公开 Issue。
- 推荐使用 Codex 客户端的本机环境变量/Secret 输入能力保存 Key。
- 轮询与错误输出会隐藏 API Key；仓库中的测试只使用本地模拟服务器。
- 如果怀疑泄露，请立即在 modbapi 控制台撤销并重新创建 Key。

## 常见问题

### `MODBAPI_API_KEY is not set`

在启动 Codex 的同一运行环境中设置 `MODBAPI_API_KEY`，然后重新打开客户端。

### 任务一直处于 `queued` 或 `in_progress`

这是异步任务的正常状态。脚本默认每 3 秒轮询，最多等待 300 秒；可使用 `--timeout` 调整。

### 任务 `completed` 但没有图片

脚本要求详情接口返回 `detail.data[].download_url`。确认请求使用 `response_format=url`，并检查任务详情接口与渠道配置。

### 任务成功但 Codex 中显示破图

更新到最新版后重新运行。脚本默认把远程结果保存为本地文件，并输出 `IMAGE_PATH` 和可直接渲染的绝对路径 Markdown；不要把 `IMAGE_URL` 手动替换回 Markdown。

### `401` 或 `404`

检查 API Key、`MODBAPI_BASE_URL` 和 `/v1` 层级。默认值应为 `https://z.modbapi.com`，脚本会自动拼接 `/v1`。

## 开发与验证

```sh
python3 -m py_compile scripts/modbapi_imagegen.py
python3 -m unittest discover -s tests -v
```

仓库不需要真实 API Key 才能运行单元测试。

## 许可证

MIT，见 [LICENSE](LICENSE)。
