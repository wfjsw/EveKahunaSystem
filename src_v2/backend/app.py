# -*- coding: utf-8 -*-

import os
from quart import Quart, send_from_directory

app = Quart(__name__)
app.secret_key = "生成一个安全的随机密钥"  # 在生产环境中应使用强随机密钥

from .api import init_api

init_api(app)

# 静态文件路由
@app.route('/')
@app.route('/<path:path>')
async def serve_vue(path='index.html'):
    root_dir = os.path.join(os.path.dirname(__file__), '../frontend/dist')
    return await send_from_directory(root_dir, path)

async def init_backend():
    return await app.run_task(debug=True, port=9527)

