# deploy_cf_pages.py
# 独立脚本：自动生成 dist/index.html 并部署到 Cloudflare Pages
# 用法: python deploy_cf_pages.py
# 环境变量:
#   CLOUDFLARE_API_TOKEN   (或 CF_API_TOKEN)     — Cloudflare API Token
#   CLOUDFLARE_ACCOUNT_ID  (或 CF_ACCOUNT_ID)    — Cloudflare 账户 ID
#   CLOUDFLARE_PROJECT_NAME (或 CF_PROJECT_NAME) — Pages 项目名称，默认 "allabin"

import os
import re
import subprocess
import logging
from pathlib import Path

# ========= 日志 =========
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cf-deploy")

# ========= 环境变量 =========
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN") or os.getenv("CF_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("CF_ACCOUNT_ID", "")
CLOUDFLARE_PROJECT_NAME = os.getenv("CLOUDFLARE_PROJECT_NAME") or os.getenv("CF_PROJECT_NAME", "allabin")

DIST_DIR = Path("dist")


def ensure_dist_dir() -> None:
    """确保 dist 目录存在"""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"dist 目录已就绪: {DIST_DIR.resolve()}")


def generate_index_html() -> Path:
    """在 dist 目录下生成一个简单的首页 index.html"""
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloudflare Pages - 部署成功</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
        }
        .card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }
        .card h1 { font-size: 2rem; margin-bottom: 16px; }
        .card p { font-size: 1.1rem; opacity: 0.85; line-height: 1.6; }
        .badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 6px 18px;
            border-radius: 20px;
            margin-top: 24px;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 部署成功</h1>
        <p>此页面由 Cloudflare Pages 自动部署</p>
        <span class="badge">Powered by Wrangler</span>
    </div>
</body>
</html>"""
    index_path = DIST_DIR / "index.html"
    index_path.write_text(html_content, encoding="utf-8")
    logger.info(f"index.html 已生成: {index_path.resolve()}")
    return index_path


def parse_cf_pages_domain(output: str) -> str | None:
    """从 wrangler 输出中解析出 Cloudflare Pages 域名"""
    clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", output)
    found_domains = re.findall(
        r"(?:https?://)?([a-zA-Z0-9_.-]+\.pages\.dev)", clean, re.IGNORECASE
    )
    if not found_domains:
        return None
    sorted_domains = sorted(
        set(dom.lower() for dom in found_domains),
        key=lambda x: len(x.split(".")),
        reverse=True,
    )
    for dom in sorted_domains:
        if len(dom.split(".")) >= 4:
            return dom
    return sorted_domains[0]


def deploy_dist_with_cf_pages() -> str:
    """部署 dist 目录到 Cloudflare Pages，返回部署后的域名"""
    if not CLOUDFLARE_PROJECT_NAME:
        raise ValueError("CLOUDFLARE_PROJECT_NAME 为空，请设置环境变量")

    env = os.environ.copy()
    if CLOUDFLARE_API_TOKEN:
        env["CLOUDFLARE_API_TOKEN"] = CLOUDFLARE_API_TOKEN
    if CLOUDFLARE_ACCOUNT_ID:
        env["CLOUDFLARE_ACCOUNT_ID"] = CLOUDFLARE_ACCOUNT_ID

    cmd = [
         "wrangler", "pages", "deploy", "dist",
        f"--project-name={CLOUDFLARE_PROJECT_NAME}",
    ]
    logger.info(f"执行部署命令: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    output = proc.stdout + proc.stderr

    if proc.returncode != 0:
        logger.error(f"[部署失败]\n{output}")
        raise RuntimeError("Deploy Failed")

    domain = parse_cf_pages_domain(output)
    if not domain:
        logger.error(f"无法从输出中解析域名:\n{output}")
        raise RuntimeError("No domain parsed")

    try:
        Path("domain.txt").write_text(domain, encoding="utf-8")
    except Exception:
        pass

    logger.info(f"[部署成功] 域名: https://{domain}")
    return domain


def main():
    try:
        ensure_dist_dir()
        generate_index_html()
        domain = deploy_dist_with_cf_pages()
        print(f"部署成功: https://{domain}")
    except Exception as e:
        logger.error(f"部署失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
