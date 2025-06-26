# test_network.py

import asyncio
import json
from main import DrissionPageMCP  # 从你的主文件导入我们写好的类

# 这是一个公开的测试API，它会返回一个包含用户列表的JSON
TEST_API_URL = "https://space.bilibili.com/5870268"
OUTPUT_CSV_FILE = "users_from_api.csv"

async def run_network_capture_test():
    """
    一个完整的测试流程，用于演示和验证网络抓包、提取和处理的功能。
    """
    print("--- 测试开始：网络抓包与数据处理 ---")
    
    agent = DrissionPageMCP()

    # --- 步骤 1: 启动浏览器 ---
    print("\n[Step 1] 正在启动浏览器...")
    connect_result = await agent.connect_or_open_browser()
    tab_id = connect_result.get("tab_id")
    print(f"  [+] 成功：浏览器已启动，当前标签页ID: {tab_id}")

    # --- 步骤 2: 开启网络监听 ---
    print("\n[Step 2] 正在开启网络监听...")
    listen_result = agent.start_network_listening(tab_id="current")
    print(listen_result)

    # --- 步骤 3: 导航到目标URL以触发API请求 ---
    print(f"\n[Step 3] 正在导航到测试API: {TEST_API_URL}...")
    await agent.get(url=TEST_API_URL, tab_id=tab_id)
    print("  [+] 成功：页面导航完成。")

    # --- 步骤 4: 获取抓取到的网络请求 ---
    print("\n[Step 4] 正在获取已捕获的网络请求...")
    capture_result = agent.get_captured_requests(tab_id=tab_id)
    
    requests = capture_result.get("captured_requests", [])
    if not requests:
        print("  [!] 失败：没有捕获到任何网络请求。")
        return
        
    print(f"  [+] 成功：捕获到 {len(requests)} 条API请求。")
    for req in requests:
        if req['json'] is None:
            continue
        print(req['json'])
if __name__ == "__main__":
    asyncio.run(run_network_capture_test())