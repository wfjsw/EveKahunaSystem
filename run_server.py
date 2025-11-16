import argparse
import sys
import asyncio
import platform
from pathlib import Path

from hypercorn.config import Config
from hypercorn.asyncio import serve
from src_v2.backend.app import get_app, serve_vue
from src_v2.core import init_database
from src_v2.model.EVE.eveesi import init_esi_manager

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def parse_args():
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dev", "-d", action="store_true")
    group.add_argument("--prod", "-p", action="store_true")

    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9527)

    return parser.parse_args()


async def main():
    args = parse_args()

    config = Config()
    config.bind = [f"{args.host}:{args.port}"]

    # 配置 worker 模式：优先使用 uvloop（性能更好），否则使用 asyncio
    # 注意：uvloop 在 Windows 上不支持，会自动回退到 asyncio
    if platform.system() != "Windows":
        try:
            import uvloop
            config.worker_class = "uvloop"
            print("[性能优化] 使用 uvloop 事件循环（高性能模式）")
        except ImportError:
            config.worker_class = "asyncio"
            print("[默认模式] 使用 asyncio 事件循环（安装 uvloop 可提升性能：pip install uvloop）")
    else:
        config.worker_class = "asyncio"
        print("[Windows 模式] 使用 asyncio 事件循环（uvloop 不支持 Windows）")

    if args.dev:
        # 🔥 关键点：Hypercorn 0.18 就是用这个重载
        config.use_reloader = True
        print("[开发模式] 热重载已启用（默认监控整个项目目录）")
    else:
        config.use_reloader = False
        print("[生产模式] 正常启动")

    # 初始化数据库和基础服务
    await init_database()
    await init_esi_manager()

    from src_v2.core.database.connect_manager import redis_manager
    # await redis_manager.r.flushall()

    # TODO 市场信息节点初始化，参数控制。
    # from src_v2.model.EVE.industry.industry_manager import MarketTree
    # await MarketTree.init_market_tree()
    # await MarketTree.link_type_to_market_group()
    # TODO 蓝图信息节点初始化，参数控制。
    # from src_v2.model.EVE.industry.blueprint import BPManager
    # await BPManager.init_bp_data_to_neo4j()

    # 初始化 Quart App
    app = get_app()
    
    # 生产模式下启用前端静态文件服务
    if args.prod:
        serve_vue()
        print("[生产模式] 前端静态文件服务已启用")

    print(f"启动服务器：http://{args.host}:{args.port}")

    # 0.18 reloader 逻辑内置在 serve() 里
    await serve(app, config)


if __name__ == "__main__":
    asyncio.run(main())
