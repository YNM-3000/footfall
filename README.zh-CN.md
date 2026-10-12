# Footfall（人流计数）

[![CI](https://github.com/YNM-3000/footfall/actions/workflows/ci.yml/badge.svg)](https://github.com/YNM-3000/footfall/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

[English](README.md) | 简体中文

基于摄像头的人流计数：用计算机视觉检测并跟踪行人，统计穿过虚拟线的进出人数，并在浏览器里实时查看数字。

目前它处理的是上传的录像，但在设计上已经为后续扩展到多路实时摄像头的持续监控做好了准备，详见[为实时流而生](#为实时流而生)。

## 工作原理

1. **检测**：[YOLOv8](https://github.com/ultralytics/ultralytics)（`models/yolov8n.pt`）找出每一帧画面里的所有人。
2. **跟踪**：ByteTrack（`ultralytics` 内置）为每个被检测到的人跨帧分配一个持久的 ID。
3. **计数**：在画面上画一条虚拟线（比如闸机口或走廊）。当被跟踪者的中心点穿过这条线时，按方向给 IN 或 OUT 计数器加一。
4. **在场人数**：当前总数 = IN − OUT。

## 使用 Docker 快速开始

```bash
docker compose up --build        # 控制台地址 http://127.0.0.1:8000
```

API 和构建好的控制台会跑在同一个容器里。上传文件、SQLite 数据库和模型权重（首次使用时下载）都保存在具名卷中，重启后不会丢失。端口只发布在 `127.0.0.1` 上，修改之前请先阅读[安全](#安全)。

镜像默认安装 CPU 版 PyTorch，体积不到 2 GB。如果要在 NVIDIA GPU 主机上运行，请用 `docker compose build --build-arg TORCH_VARIANT=cuda` 构建，并为容器开启 GPU 访问。

不用 Docker 的话，请继续往下看。

## 环境要求

- Python ≥ 3.10
- [`uv`](https://github.com/astral-sh/uv)，用于依赖管理

```bash
# 没有 uv 的话先安装
curl -LsSf https://astral.sh/uv/install.sh | sh
```

之后不需要单独的安装步骤：`uv run` 会读取 `pyproject.toml`，并在首次运行时自动创建环境。

## 用法

```bash
# 处理录制好的视频文件
uv run footfall --source data/pedestrian.mp4 --output out/annotated.mp4

# 处理实时摄像头流（RTSP/HTTP URL）：代码不变，只换输入源
uv run footfall --source rtsp://user:pass@camera-ip/stream --output out/annotated.mp4

# 使用本机摄像头，方便本地快速测试
uv run footfall --source 0 --show

# 对长视频的前 100 帧做快速抽查
uv run footfall --source data/pedestrian.mp4 --max-frames 100
```

`uv run python -m people_counter --source ...` 与上面的写法等价。

### 参数

| 参数                 | 用途                                                                                                                                                             |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--source`           | 必填。视频文件路径、RTSP/HTTP URL 或摄像头编号。                                                                                                                  |
| `--output`           | 带标注的视频输出路径（默认 `out/annotated.mp4`）。上级目录会自动创建。                                                                                            |
| `--line X1 Y1 X2 Y2` | 计数线，单位为像素。**请按每个摄像头单独设置**：线要垂直于行走方向，横跨真实的闸机口。默认是穿过画面中部的一条水平线。 |
| `--in-direction`     | `negative-to-positive`（默认）或 `positive-to-negative`。如果测试时发现 IN/OUT 反了，就换成另一个。                                                                |
| `--conf`             | 检测置信度阈值（默认 `0.35`）。调高可减少误检，调低可检出更多的人。                                                                                               |
| `--imgsz`            | 推理分辨率（模型默认为 640）。在人物很小的高分辨率广角画面上，可以调到 `1280` 以上，代价是速度变慢。                                                               |
| `--model`            | Ultralytics 权重（默认 `models/yolov8n.pt`，首次运行时自动下载）。`yolov8s/m/l/x.pt` 用速度换精度。                                                                |
| `--max-frames N`     | 处理 N 帧后停止，用来对长视频快速抽查准确率。                                                                                                                      |
| `--progress-interval`| 每 N 帧打印一次当前计数（默认 `30`）。                                                                                                                            |
| `--show`             | 处理时实时显示带标注的视频（按 `q` 停止）。                                                                                                                        |

### 输出

- 带标注的视频：包含检测框、跟踪 ID、计数线，以及实时的 IN/OUT/NET 读数。叠加层的大小会随画面缩放，所以 720p 和 4K 的素材都能看清。
- 实时计数输出到标准输出，结束时输出最终的 IN/OUT/NET 总数。
- 退出码：成功为 `0`，输入源或输出不可用为 `1`，Ctrl-C 中断为 `130`。

## 项目结构

三层结构，组织成一个 uv workspace。每一层只依赖它下面的那一层。

```
core/                        # the counting library — no web, no HTTP
├── src/people_counter/
│   ├── cli.py               # command line entry point
│   ├── config.py            # AppConfig + defaults (single source of truth)
│   ├── pipeline.py          # frames -> tracking -> counting -> events
│   ├── detection.py         # PersonTracker protocol + YOLO/ByteTrack
│   ├── counting.py          # LineCrossingCounter, Counts, CrossingEvent
│   ├── geometry.py          # Line / BoundingBox, side-of-line maths
│   ├── rendering.py         # all OpenCV drawing
│   └── video.py             # VideoStream / writer / grab_frame
└── tests/

backend/                     # FastAPI service over the library
├── src/people_counter_api/
│   ├── app.py               # application factory
│   ├── routes/              # videos, jobs, WebSocket stream
│   ├── jobs.py              # JobRunner: pipeline execution off the event loop
│   ├── storage.py           # SQLite: videos, jobs, crossing events
│   ├── bus.py               # fan-out of live updates to dashboards
│   └── preview.py           # JPEG encoding for browser previews
└── tests/

frontend/                    # React + Vite dashboard
└── src/
    ├── api/                 # typed client and wire types
    ├── i18n/                # zh (default) + en catalogues, type-checked
    ├── hooks/useJobStream   # WebSocket subscription with reconnect
    └── components/          # line editor, counts readout, feed, history

data/  out/  models/         # footage, artifacts, weights (git-ignored)
```

这些边界是有意设计的。`detection.PersonTracker` 是一个 `Protocol`，`pipeline.run()` 接收注入的 tracker，所以可以直接换上别的检测器，整套测试也不需要模型权重就能跑。后端使用这个库的方式和其他任何客户端一样，因此要接入另一种传输方式，新增一个模块就行，不用重写。

## 控制台

上传一段录像，把计数线拖到画面里人真正走过的位置，然后在处理过程中实时观看计数。

```bash
uv sync                              # 安装 core + backend
uv run footfall-api            # http://127.0.0.1:8000

cd frontend && npm install
npm run dev                          # http://localhost:5173，代理 /api
```

如果要做单一来源（single-origin）部署，运行 `npm run build` 会生成 `frontend/dist`，该目录存在时由 API 在 `/` 下提供。

### 多语言

控制台提供中文（默认）和英文两种语言，切换器在页眉里，选择会按浏览器保存。要修改默认语言，请改 `frontend/src/i18n/index.ts` 里的 `DEFAULT_LANGUAGE`。

新增一种语言只需要一个文件：

```ts
// frontend/src/i18n/locales/ja.ts
import type { zh } from "./zh";
export const ja: typeof zh = { /* the compiler lists every missing key */ };
```

`zh.ts` 为所有其他语言包提供类型约束，所以缺失或拼错的 key 会在构建时报错，而不是在线上变成一个空白标签。API 错误带有稳定的 `code`（`unsupported_file_type`、`job_not_found` 等），由客户端翻译；对于语言包里还没有的错误码，则回退为服务端的英文消息。这样连报错信息也是本地化的，而不只是界面外壳。

### API

| 端点 | 用途 |
| -------- | ------- |
| `POST /api/videos` | 上传录像，返回探测到的几何信息 |
| `GET /api/videos/{id}/frame.jpg` | 静态帧，用于放置计数线 |
| `POST /api/jobs` | 用指定的线和设置开始计数 |
| `GET /api/jobs/{id}` | 状态、进度、当前累计数 |
| `GET /api/jobs/{id}/crossings` | 每一次穿线事件 |
| `GET /api/jobs/{id}/preview.jpg` | 最新的带标注帧 |
| `POST /api/jobs/{id}/cancel` | 停止正在运行的任务 |
| `WS /api/jobs/{id}/stream` | 先发快照，之后推送实时进度和穿线事件 |

WebSocket 在连接时会先发一份快照，所以中途加入或断线重连的浏览器，起点是真实状态，而不是后面才发生的某个增量。

## 为实时流而生

统计一个文件和监控一路摄像头有不少差别，这些差别事后再补会很痛苦，所以核心部分已经考虑到了：

- **持久化的是事件，不是总数。** 每次穿线都会单独存储（`track_id`、方向、帧号、时间戳）。总数是派生出来的，因此在线或阈值改动之后可以重新计算。
- **视频输出是可选的。** `output=None` 会完全跳过写入；一个连续运行好几天的摄像头不应该产生一个无限增长的文件。
- **帧采样。** `frame_stride` 让解码保持实时，而推理可以跑得慢一些，这正是让一台主机服务多路摄像头的关键。
- **有界状态。** `LineCrossingCounter.forget()` 会清理已离开的轨迹，因此每条轨迹占用的内存不会无限增长。
- **可取消的运行。** `should_stop` 让调度方可以干净地关闭一个 worker。实时摄像头不过是一个永远不会结束的任务。

接入实时摄像头还差这些：带"最新帧优先"策略的 RTSP 重连（实时流必须*丢弃*积压的帧，绝不能排队，否则每路摄像头都会越落越远），以及把 `JobRunner` 从线程迁到进程或独立主机上。

### 吞吐量

在 Apple Silicon Mac 上实测（CPU，`yolov8n`，单路流）：

| `imgsz` | 吞吐量 | 每帧检测到的人数 |
| ------- | ---------- | ------------------------- |
| 640（模型默认） | 17.3 fps | 3.8 |
| 1280 | 11.0 fps | 23.3 |

在密集的 4K 素材上，默认分辨率会漏掉大部分人群，所以控制台默认使用 1280。以约 11 fps 计，一台 CPU 主机大约能处理两路 5 fps 的摄像头；再多就需要 GPU 了。

## 开发

```bash
uv sync --group dev              # 运行时依赖 + 测试依赖
uv run pytest                    # core + backend，不需要权重或素材
uv run pytest --cov=core/src --cov=backend/src
uv run ruff check . && uv run ruff format --check .
uv run pyright                   # 类型检查（配置见 pyrightconfig.json）

cd frontend
npm run build                    # 类型检查并打包
npm run e2e                      # 在 Chromium 里驱动真实 UI
```

测试会对 tracker 打桩，并生成合成视频片段，因此整套测试不到一秒就能跑完，也不会下载模型权重。e2e 冒烟测试需要一个运行中的 API 和一段真实视频（`VIDEO=../data/pedestrian.mp4`）。

## 验证新摄像头

1. 从目标摄像头录一小段视频（1–2 分钟）。
2. 设置 `--line`，让它对准这段素材里实际的闸机口或走廊。
3. 先加 `--max-frames` 跑一遍，然后手动数一下同一段视频里进出的若干人，和打印出的总数对比。
4. 反复调整 `--line`、`--conf`、`--imgsz` 和 `--in-direction`，直到计数对得上。密集的高峰时段素材可能需要更大的模型（`yolov8s.pt` 及以上）和更高的 `--imgsz`；在严重遮挡下，准确率下降是意料之中的。
5. 文件测试的准确率达标后，把 `--source` 指向实时摄像头的 URL 即可，不需要改其他代码。

### 已知的准确率局限

中心点过线法会把每一次符号翻转都计入，所以在闸机口附近徘徊的人可能被重复计数；在遮挡情况下 ByteTrack 的 ID 切换，则会让两个方向的计数都有损失。在密集人群素材上，用默认的 `--imgsz 640` 时，一帧 4K 画面会被 letterbox 缩得很小，远处的人就检测不到了；在相信总数之前，请先调高 `--imgsz`。

## 负责任地使用

这个项目只统计人数，不识别身份。它不做人脸识别，也不做跨摄像头或跨会话的重识别，跟踪 ID 只是单次运行内的编号。持久化的输出是匿名的穿线事件：一个方向、一个帧号和一个时间戳。

不过，视频素材本身属于个人信息。在很多司法辖区（欧盟的 GDPR、中国的《个人信息保护法》(PIPL) 等），录制人像哪怕只是为了计数，也要承担相应的义务。把它接到真实摄像头之前：

- 查清当地关于视频录制的规定，在要求的地方张贴告示。
- 只保留必要的数据。计数并不需要留存视频。验证完一个摄像头之后，请删除 `data/` 和 `out/` 下的上传文件和带标注的视频；运行实时摄像头时不要输出视频。
- 限制对控制台和 `data/` 目录的访问。参见[安全](#安全)。

不要用这个项目去追踪特定个人、给人画像，或者秘密监视任何人。

## 安全

API **没有任何身份验证**。它默认绑定在 `127.0.0.1`，只适合在受信任的机器或网络里使用。如果要暴露到更大的范围，请放在负责身份验证和 TLS 的反向代理后面。部署模型以及如何私下报告漏洞，请参阅 [SECURITY.md](SECURITY.md)。

## 路线图

- [x] 检测 + 跟踪 + 过线计数（CLI）
- [x] 带穿线事件、实时更新和持久化的计数 API
- [x] 控制台：上传、在画面上放置计数线、实时查看计数
- [ ] 摄像头注册表：支持重连和健康检查的 RTSP 输入源，取代只能上传的输入方式
- [ ] 多摄像头平铺视图，显示每路摄像头的在场人数
- [ ] 在场人数基线和每日校准（长时间运行后净值会漂移）
- [ ] 基于已存储穿线事件的历史图表
- [ ] 进程级或主机级的 worker，以及 GPU 推理

## 参与贡献

欢迎提交 issue 和 pull request。[CONTRIBUTING.md](CONTRIBUTING.md) 介绍了环境搭建、CI 会运行的检查以及项目约定。

## 许可证

Footfall 采用 [GNU Affero General Public License v3.0](LICENSE) 授权。

这个许可证是由检测器决定的。Footfall 依赖 [Ultralytics](https://github.com/ultralytics/ultralytics)，而它的库和 YOLO 权重都是 AGPL-3.0。所以，如果你修改了这个项目，并让别人通过网络使用它（比如托管的计数控制台），就必须向他们提供你修改后版本的源代码。如果你需要不同的授权条款，要么向 Ultralytics 购买商业许可，要么通过 `detection.PersonTracker` 协议换用宽松许可的检测器。
