"""
自动打包智能体测试文件
包含多种微服务类型的测试场景
"""

import asyncio
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

from src.agents.autopack_agent import AutoPackAgent
from src.core.pack_workflow import PackWorkflow
from src.models.pack_models import PackRequest
from src.utils.logger import log


def create_test_projects():
    """创建测试项目"""
    test_dir = Path(tempfile.mkdtemp(prefix="autopack_test_"))
    log.info(f"创建测试项目目录: {test_dir}")

    projects = {}

    # 1. Python Flask项目
    python_dir = test_dir / "python-flask-app"
    python_dir.mkdir(parents=True, exist_ok=True)

    (python_dir / "app.py").write_text("""
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Flask!"

@app.route('/health')
def health():
    return {"status": "ok"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
""", encoding='utf-8')

    (python_dir / "requirements.txt").write_text("""
Flask==2.3.2
gunicorn==21.2.0
""", encoding='utf-8')

    (python_dir / "Dockerfile").write_text("""
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
""", encoding='utf-8')

    projects["python_flask"] = str(python_dir)

    # 2. Node.js Express项目
    node_dir = test_dir / "node-express-app"
    node_dir.mkdir(parents=True, exist_ok=True)

    (node_dir / "package.json").write_text("""{
  "name": "express-app",
  "version": "1.0.0",
  "description": "Express.js application",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
""", encoding='utf-8')

    (node_dir / "server.js").write_text("""
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
    res.json({ message: 'Hello from Express!' });
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Server running on port ${port}`);
});
""", encoding='utf-8')

    (node_dir / "Dockerfile").write_text("""
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
""", encoding='utf-8')

    projects["node_express"] = str(node_dir)

    # 3. 无Dockerfile的Python项目（测试自动生成）
    python_auto_dir = test_dir / "python-auto-app"
    python_auto_dir.mkdir(parents=True, exist_ok=True)

    (python_auto_dir / "main.py").write_text("""
import http.server
import socketserver
import json

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"message": "Hello from Python HTTP Server!", "status": "ok"}
            self.wfile.write(json.dumps(response).encode())
        else:
            super().do_GET()

if __name__ == "__main__":
    PORT = 8000
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Server running on port {PORT}")
        httpd.serve_forever()
""", encoding='utf-8')

    (python_auto_dir / "requirements.txt").write_text("")
    projects["python_auto"] = str(python_auto_dir)

    # 4. 带构建脚本项目
    scripted_dir = test_dir / "scripted-app"
    scripted_dir.mkdir(parents=True, exist_ok=True)

    (scripted_dir / "app.py").write_text("""
print("Hello from scripted app!")
""", encoding='utf-8')

    (scripted_dir / "build.sh").write_text("""#!/bin/bash
echo "Building application..."
echo "Build completed successfully!"
""", encoding='utf-8')

    (scripted_dir / "build.sh").chmod(0o755)

    (scripted_dir / "requirements.txt").write_text("")
    projects["scripted"] = str(scripted_dir)

    # 5. 错误配置项目（用于测试重试逻辑）
    error_dir = test_dir / "error-app"
    error_dir.mkdir(parents=True, exist_ok=True)

    (error_dir / "Dockerfile").write_text("""
FROM invalid-base-image:latest

WORKDIR /app

COPY . .

RUN invalid-command

EXPOSE 8080

CMD ["./nonexistent-script"]
""", encoding='utf-8')

    projects["error"] = str(error_dir)

    return test_dir, projects


async def test_basic_agent():
    """测试基础AutoPackAgent"""
    log.info("=== 测试基础AutoPackAgent ===")

    test_dir, projects = create_test_projects()

    agent = AutoPackAgent()

    # 测试Python项目
    pack_request = PackRequest(
        repo_path=projects["python_flask"],
        docker_image_name="test-flask-app",
        docker_tag="v1.0.0"
    )

    try:
        result = await agent.pack(pack_request)

        print(f"\n--- Python Flask项目打包结果 ---")
        print(f"成功: {result.success}")
        print(f"镜像名称: {result.image_name}")
        print(f"执行时间: {result.execution_time:.2f}秒")
        print(f"重试次数: {result.retry_count}")
        print(f"使用的Docker命令: {result.docker_commands_used}")

        if result.error_message:
            print(f"错误信息: {result.error_message}")

    except Exception as e:
        log.error(f"Python项目测试失败: {e}")

    # 清理
    import shutil
    shutil.rmtree(test_dir)


async def test_workflow_agent():
    """测试智能打包工作流"""
    log.info("=== 测试智能打包工作流 ===")

    test_dir, projects = create_test_projects()

    workflow = PackWorkflow(max_retries=2)

    # 测试自动生成Dockerfile的项目
    pack_request = PackRequest(
        repo_path=projects["python_auto"],
        docker_image_name="test-auto-python",
        docker_tag="latest",
        environment="development"
    )

    try:
        result = await workflow.run(pack_request)

        print(f"\n--- 自动生成Dockerfile项目打包结果 ---")
        print(f"工作流成功: {result['success']}")
        print(f"重试次数: {result['retry_count']}")
        print(f"检测到的构建脚本: {len(result['build_scripts_found'])}")
        print(f"执行步骤: {result['execution_steps']}")

        if result['pack_result']:
            pack_result = result['pack_result']
            print(f"镜像名称: {pack_result.image_name}")
            print(f"执行时间: {pack_result.execution_time:.2f}秒")

        if result.get('error_history'):
            print("错误历史:")
            for i, error in enumerate(result['error_history'], 1):
                print(f"  {i}. {error}")

    except Exception as e:
        log.error(f"工作流测试失败: {e}")

    # 清理
    import shutil
    shutil.rmtree(test_dir)


async def test_multiple_projects():
    """测试多种项目类型"""
    log.info("=== 测试多种项目类型 ===")

    test_dir, projects = create_test_projects()

    workflow = PackWorkflow(max_retries=3)

    test_cases = [
        {
            "name": "Python Flask",
            "path": projects["python_flask"],
            "image": "test-flask-workflow",
            "expected_success": True
        },
        {
            "name": "Node.js Express",
            "path": projects["node_express"],
            "image": "test-node-workflow",
            "expected_success": True
        },
        {
            "name": "自动生成Dockerfile",
            "path": projects["python_auto"],
            "image": "test-auto-workflow",
            "expected_success": True
        },
        {
            "name": "构建脚本项目",
            "path": projects["scripted"],
            "image": "test-scripted-workflow",
            "expected_success": True
        },
        {
            "name": "错误配置项目",
            "path": projects["error"],
            "image": "test-error-workflow",
            "expected_success": False
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        log.info(f"测试 {i}/{len(test_cases)}: {test_case['name']}")

        pack_request = PackRequest(
            repo_path=test_case["path"],
            docker_image_name=test_case["image"],
            docker_tag=f"test-{i}",
            environment="test"
        )

        try:
            start_time = asyncio.get_event_loop().time()
            result = await workflow.run(pack_request)
            end_time = asyncio.get_event_loop().time()

            test_result = {
                "name": test_case["name"],
                "success": result["success"],
                "expected_success": test_case["expected_success"],
                "retry_count": result["retry_count"],
                "execution_time": end_time - start_time,
                "build_scripts": len(result["build_scripts_found"]),
                "image_name": result["pack_result"].image_name if result["pack_result"] else None,
                "error_count": len(result.get("error_history", []))
            }

            results.append(test_result)

            print(f"  ✓ {test_case['name']}: {'成功' if result['success'] else '失败'} "
                  f"(重试: {result['retry_count']}, 脚本: {len(result['build_scripts_found'])})")

        except Exception as e:
            log.error(f"测试 {test_case['name']} 失败: {e}")
            results.append({
                "name": test_case["name"],
                "success": False,
                "expected_success": test_case["expected_success"],
                "error": str(e)
            })

        # 等待一下避免资源竞争
        await asyncio.sleep(1)

    # 打印总结
    print(f"\n=== 测试总结 ===")
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    expected_successful = sum(1 for r in results if r["success"] == r["expected_success"])

    print(f"总测试数: {total}")
    print(f"成功打包: {successful}")
    print(f"符合预期: {expected_successful}")

    print(f"\n详细结果:")
    for result in results:
        status = "✓" if result["success"] == result["expected_success"] else "✗"
        print(f"  {status} {result['name']}: {'成功' if result.get('success') else '失败'} "
              f"(预期: {'成功' if result.get('expected_success') else '失败'})")

    # 清理
    import shutil
    shutil.rmtree(test_dir)

    return results


async def main():
    """主测试函数"""
    log.info("开始测试自动打包智能体")

    try:
        # 1. 测试基础Agent
        await test_basic_agent()

        # 2. 测试工作流Agent
        await test_workflow_agent()

        # 3. 测试多种项目类型
        await test_multiple_projects()

        log.info("所有测试完成")

    except Exception as e:
        log.error(f"测试过程中发生错误: {e}")


if __name__ == "__main__":
    # 确保Docker服务运行
    try:
        import docker
        docker_client = docker.from_env()
        docker_client.ping()
        print("Docker服务连接正常")
    except Exception as e:
        print(f"Docker服务连接失败: {e}")
        print("请确保Docker服务正在运行")
        exit(1)

    asyncio.run(main())