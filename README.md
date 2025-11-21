<div align="center">

# 🌟 Kahuna System 🌟

![Logo](https://github.com/user-attachments/assets/40c09a45-f898-4167-9315-20df6a1dc59a)

[![开发状态](https://img.shields.io/badge/状态-开发中-yellow)](https://github.com/AraragiEro/astrbot_plugin_kahunabot)
[![EVE Online](https://img.shields.io/badge/游戏-EVE%20Online-blue)](https://www.eveonline.com/)
[![Quart](https://img.shields.io/badge/框架-Quart-green)](https://github.com/AstrBotDevs/AstrBot.git)
[![Vue3](https://img.shields.io/badge/框架-Vue3-green)](https://github.com/AstrBotDevs/AstrBot.git)

_笨笨的kahuna不停的计算自己离买牛角包还有多远_

_一座新的**X**山拔地而起！_

🥰 _爱来自 凛冬联盟群 紫竹梅重工_

![sty](https://github.com/user-attachments/assets/f37a6a06-b925-4836-8561-282720f06506)

</div>

基于 Quart 和 Vue3 的 EVE Online 一体化 Web 应用平台，为玩家提供市场价格查询、成本计算、工业规划等综合服务。

## 项目简介

Kahuna System 是一个专为 EVE Online 玩家设计的 Web 应用平台，集成了市场数据分析、工业制造规划、资产统计等核心功能。平台采用现代化的前后端分离架构，提供直观的用户界面和强大的计算能力。

## 核心功能

- **市场价格查询** - 支持吉他和联盟市场实时价格查询
- **成本计算** - 精确计算制造和采购成本
- **工业规划** - 智能工业制造规划与报表输出
- **化矿分析** - 矿石精炼与材料分析
- **采购清单** - 可自定义数据来源的采购清单管理
- **利润分析** - 深度利润分析与市场机会挖掘
- **挂单分析** - 市场订单分析与优化建议
- **资产统计** - 角色和公司资产统计与管理

## 技术栈

- **后端**: Quart (Python 3.13+), Hypercorn
- **前端**: Vue 3, TypeScript, Element Plus, ECharts
- **数据库**: SQLite / PostgreSQL, Neo4j, Redis
- **其他**: ESI API, OAuth2

## 快速开始

### 环境要求

- Python 3.13 或更高版本
- Node.js 18+ (用于前端开发)
- 数据库：SQLite (默认) 或 PostgreSQL + Neo4j + Redis (可选)

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/AraragiEro/astrbot_plugin_kahunabot.git
cd astrbot_plugin_kahunabot
```

2. **安装后端依赖**

使用 `uv` (推荐):
```bash
uv sync
```

或使用 `pip`:
```bash
pip install -r requirements.txt
```

3. **安装前端依赖**

```bash
cd src_v2/frontend
npm install
```

4. **准备 SDE 数据库**

项目需要 EVE Online 的 SDE (Static Data Export) 数据库。你可以使用 [EVE-SDE-Database-Builder](https://github.com/EVEIPH/EVE-SDE-Database-Builder) 工具生成 SQLite 格式的英文和中文 SDE 数据库。

官方 SDE 数据下载地址: [https://developers.eveonline.com/](https://developers.eveonline.com/)

5. **配置 EVE API**

前往 [EVE Online 开发者中心](https://developers.eveonline.com/) 创建应用，获取 `CLIENT_ID` 和 `SECRET_KEY`。

6. **启动服务**

开发模式:
```bash
python run_server.py --dev --host 0.0.0.0 --port 9527
```

生产模式:
```bash
# 先构建前端
cd src_v2/frontend
npm run build
cd ../..

# 启动服务
python run_server.py --prod --host 0.0.0.0 --port 9527
```

或使用提供的脚本 (Linux/macOS):
```bash
./run_server.sh dev    # 开发模式
./run_server.sh start  # 生产模式
./run_server.sh stop   # 停止服务
```

启动成功后，访问 `http://localhost:9527` 即可使用平台。

## 配置说明

### 配置文件

项目使用 TOML 格式的配置文件。将 `config.toml.example` 复制为 `config.toml` 并填写相应配置。

### 主要配置项

#### [APP] - 应用基础配置
```toml
[APP]
# 图片渲染代理 (留空则不使用)
PIC_RENDER_PROXY = ""
# 代理服务器地址
PROXY = "127.0.0.1"
# 代理端口
PORT = 7890
```

#### [SQLITEDB] - SQLite 数据库配置
```toml
[SQLITEDB]
# 配置数据库路径（绝对路径）
CONFIG_DB = "/path/to/kahuna.db"
CACHE_DB = "/path/to/cache.db"
# SDE 数据库路径
SDEDB = "/path/to/sde.db"           # 英文 SDE 数据库
CN_SDEDB = "/path/to/sde_cn.db"     # 中文 SDE 数据库
```

#### [POSTGREDB] - PostgreSQL 数据库配置 (可选)
```toml
[POSTGREDB]
Host = "localhost"
Port = 5432
Database = "kahuna"
User = "admin"
Password = "secret"
```

#### [REDIS] - Redis 配置 (可选)
```toml
[REDIS]
Host = "localhost"
Port = 6379
```

#### [NEO4J] - Neo4j 图数据库配置 (可选)
```toml
[NEO4J]
Host = "localhost"
Port = 7687
Username = "neo4j"
Password = "password"
```

#### [EVE] - EVE Online API 配置
```toml
[EVE]
# 在 https://developers.eveonline.com/ 申请应用获取
CLIENT_ID = "your_client_id"
SECRET_KEY = "your_secret_key"
# 回调地址
CALLBACK_LOCAL_HOST = ""
CALLBACK_LOCAL_ADD = "https://localhost:9527/"
```

#### [ESI] - ESI API 权限配置

根据你的需求启用或禁用相应的 ESI 权限。常用权限示例：

```toml
[ESI]
# 公共数据访问
publicData = false

# 资产相关权限
"esi-assets.read_assets.v1" = true
"esi-assets.read_corporation_assets.v1" = true

# 市场相关权限
"esi-markets.structure_markets.v1" = true
"esi-markets.read_character_orders.v1" = true

# 工业相关权限
"esi-industry.read_character_jobs.v1" = true
"esi-industry.read_corporation_jobs.v1" = true

# 蓝图相关权限
"esi-characters.read_blueprints.v1" = true
"esi-corporations.read_blueprints.v1" = true

# 技能相关权限
"esi-skills.read_skills.v1" = true

# 钱包相关权限
"esi-wallet.read_character_wallet.v1" = true
```

完整的权限列表请参考 `config.toml.example` 文件。

### 配置文件位置

配置文件应命名为 `config.toml` 并放置在项目根目录。

## 开发计划


- [x] Web 应用平台开发
  - [x] 前端框架搭建
  - [x] ESI 访问队列控制
  - [x] 数据库重构
    - [x] PostgreSQL 和 Redis 部署
- [ ] 核心功能
  - [x] 工业计划的计算与拆解
    - [x] 可调整的产品清单
    - [x] 可调整的计算配置
    - [x] 详细的数据报表
      - [x] 计划分解树
      - [x] 材料清单
      - [x] 可参考可执行的工作流
      - [x] 可复制的采购清单
      - [x] 成本成分比例分析
      - [x] 合作工业的薪水计算
      - [x] 可参考的物流计划
  - [ ] 市场分析
    - [ ] 市场价格查看
    - [ ] 自选清单的价格监控
    - [ ] 自选产品清单的利润计算
    - [ ] 市场单品的详细数据计算【成本、利润等】
    - [ ] 特定星域的市场利润计算
- [ ] 其他
  - [x] 服务权限分级
  - [ ] 邀请码生成
  - [ ] 性能优化
  - [ ] 用户体验改进
  - [ ] 文档完善

## 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 许可证。

这意味着：
- 你可以自由使用、修改和分发本软件
- 如果你修改了代码并在网络上提供服务，必须公开修改后的源代码
- 使用本软件的服务也必须遵循 AGPL-3.0 许可证

完整的许可证文本请查看 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 相关链接

- [EVE Online 官网](https://www.eveonline.com/)
- [EVE Online 开发者中心](https://developers.eveonline.com/)
