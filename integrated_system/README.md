# IP Scout 集成系统

一个完整的 IP 评估与管理平台，包含后端 API 服务和前端界面。

## 功能特性

- 📊 数据看板与统计
- 📚 书库管理
- 👥 用户管理
- 🤖 AI 评估与预测
- 💬 留言板系统
- 🔍 数据采集与监控

## 快速开始

### 方式1：一键启动（推荐）

```bash
# 启动后端
start-backend.bat

# 启动前端（新开一个命令行窗口）
start-frontend.bat
```

### 方式2：手动启动

#### 1. 创建虚拟环境
```bash
# Windows
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

#### 2. 启动后端
```bash
cd backend
python app.py
```
后端服务将运行在 http://localhost:5000

#### 3. 启动前端
```bash
cd frontend
npm install
npm run dev
```
前端服务将运行在 http://localhost:5173

## 项目结构

```
integrated_system/
├── backend/              # Flask 后端
│   ├── app.py           # 主应用入口
│   ├── requirements.txt # Python 依赖
│   └── ...
├── frontend/            # Vue3 前端
│   ├── src/            # 源代码
│   └── ...
├── start-backend.bat   # Windows 后端启动脚本
├── start-frontend.bat  # Windows 前端启动脚本
└── README.md           # 本文档
```

## 环境要求

- Python 3.8+
- Node.js 16+
- MySQL 5.7+ (用于数据存储)

## 依赖列表

### 后端依赖 (requirements.txt)
- flask - Web 框架
- flask-cors - 跨域支持
- pandas - 数据处理
- scikit-learn - 机器学习
- xgboost - 梯度提升
- gensim - 文本分析
- jieba - 中文分词
- snownlp - 中文情感分析
- pymysql - MySQL 连接
- PyJWT - JWT 认证

### 前端依赖 (package.json)
- Vue 3 - 前端框架
- Vite - 构建工具
- Tailwind CSS - CSS 框架
- Axios - HTTP 客户端

## 常见问题

### 端口冲突
如果 5000 端口被占用，修改 `backend/app.py` 中的 `port` 参数。

### 数据库连接失败
确保 MySQL 服务已启动，并检查 `backend/auth.py` 中的数据库配置。

## 开发团队

IP Scout Team
