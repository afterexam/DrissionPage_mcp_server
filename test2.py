import asyncio
from pathlib import Path
from datetime import datetime

from main import DrissionPageMCP  # 替换成你的实际模块名，比如 mcp_impl.py

async def test_screenshot_bilibili():
    mcp = DrissionPageMCP()

    # 1. 启动浏览器
    browser_info = await mcp.connect_or_open_browser()
    tab_id = browser_info['tab_id']
    print(f"[+] 启动浏览器成功，Tab ID: {tab_id}")

    # 2. 打开 B站
    print("[*] 正在跳转至 bing 首页...")
    await mcp.navigate(tab_id, "https://www.bing.com")

    mcp.wait(5)  # 等待页面加载完毕

    # 3. 截图
    print("[*] 获取页面截图中...")
    result = mcp.get_page_screenshot(tab_id)

    if isinstance(result, dict):
        if result.get("screenshot"):
            Path("bilibili.jpg").write_bytes(result["screenshot"])
            print("[+] 截图已保存")
        else:
            print("[!] 截图失败：", result.get("error", "未知错误"))
    else:
        Path("bilibili.jpg").write_bytes(result)


    # 可选：关闭标签页
    mcp.close_tab(tab_id)

if __name__ == "__main__":
    asyncio.run(test_screenshot_bilibili())
