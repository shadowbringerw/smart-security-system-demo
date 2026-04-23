# 校园智能安防系统

这是一个基于 Flask、OpenCV、YOLOv8、DeepSORT 和 SQLite 搭建的校园智能安防演示系统，适合用于课程设计展示、毕业设计答辩演示，以及单摄像头安防场景的原型验证。

## 功能特性
- 单摄像头实时监控页面
- YOLOv8 行人检测，异常情况下可退化到背景减除方案
- DeepSORT 多目标跟踪，不可用时自动退化为 IoU 跟踪
- 电子围栏入侵检测
- 奔跑与聚集行为告警规则
- 支持条件筛选的告警中心页面
- 支持运行指标与告警统计的看板页面
- 使用 SQLite 保存告警历史记录

## 项目结构
```text
smart_security_system/
├── app.py                     # Flask 应用入口
├── config.py                  # 系统配置
├── core/
│   ├── detector.py            # 检测模块
│   ├── tracker.py             # 跟踪模块
│   ├── rules.py               # 围栏、奔跑、聚集规则
│   ├── pipeline.py            # 主视频处理链路
│   ├── storage.py             # SQLite 告警存储
│   └── models.py              # 数据模型
├── web/
│   ├── static/
│   │   ├── app.css            # 前端样式
│   │   └── app.js             # 前端脚本
│   └── templates/
│       ├── base.html          # 统一布局
│       ├── index.html         # 实时监控页
│       ├── alerts.html        # 告警中心页
│       └── dashboard.html     # 统计看板页
└── data/
    └── alerts.db              # SQLite 数据库
```

## 环境要求

- Python 3.10 或更高版本
- `pip`
- 如果使用摄像头输入，需要允许程序访问摄像头
- 推荐系统：macOS / Linux / Windows，并确保 OpenCV 可正常安装

## 快速开始

1. 创建虚拟环境并安装依赖：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 使用摄像头或本地视频运行：
```bash
python app.py --source 0
# or
python app.py --source data/demo.mp4
```

3. 浏览器访问：
- 实时监控页：`http://127.0.0.1:5000/`
- 告警中心页：`http://127.0.0.1:5000/alerts`
- 统计看板页：`http://127.0.0.1:5000/dashboard`

## 主要接口
- `GET /api/alerts?limit=100&type=intrusion`
- `GET /api/alerts/summary`
- `GET /api/stats`
- `GET /api/dashboard`
- `POST /api/fence`
- `POST /api/rules`

## 说明
- 如果 `ultralytics` 无法正常加载，检测模块会退化到背景减除方案
- 如果 `deep-sort-realtime` 不可用，跟踪模块会退化为简单 IoU 跟踪
- 默认检测类别为 `person`
- 默认数据库路径为 `data/alerts.db`

## GitHub 上传建议

推荐仓库名：
- `smart-security-system-demo`
- `campus-smart-security-demo`

建议上传内容：
- `app.py`
- `config.py`
- `requirements.txt`
- `README.md`
- `core/`
- `web/`
