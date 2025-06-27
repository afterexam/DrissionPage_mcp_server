import asyncio
from main import DrissionPageMCP  # 从你的主文件导入我们写好的类

# 一个公开的、包含大量文章和导航栏的新闻页面，非常适合测试
TEST_URL = "https://user.qzone.qq.com/1430097658?_t_=0.7563411551280744"

async def run_visible_text_test():
    """
    一个专门用于测试 `get_visible_text` 函数效果的脚本。
    """
    print("--- 测试开始：智能提取网页正文 ---")
    
    agent = DrissionPageMCP()

    # --- 步骤 1: 启动浏览器 ---
    print("\n[Step 1] 正在启动浏览器...")
    connect_result = await agent.connect_or_open_browser()
    tab_id = connect_result.get("tab_id")
    if not tab_id:
        print(f"  [!] 失败：浏览器未能成功启动。返回信息: {connect_result}")
        return
    print(f"  [+] 成功：浏览器已启动，当前标签页ID: {tab_id}")

    # --- 步骤 2: 导航到新闻页面 ---
    print(f"\n[Step 2] 正在导航到BBC新闻页面...")
    # 调用修正后的 get 函数
    nav_result = await agent.get(url=TEST_URL, tab_id=tab_id)
    if nav_result.get("error"):
        print(f"  [!] 失败: {nav_result['error']}")
        agent.close_tab(tab_id)
        return
    print(f"  [+] 成功：已打开页面 '{nav_result.get('title')}'")
    

    # --- 步骤 4: 用不同的参数再测试一次 ---

    text_result_loose = agent.get_visible_text(tab_id=tab_id, min_text_length=2)
    
    print("\n--- 提取结果 (宽松过滤) ---")
    print(text_result_loose.get("visible_text"))
    print("---------------------------------------------")

    # --- 清理 ---
    print("\n--- 测试结束，关闭浏览器。 ---")
    agent.close_tab(tab_id)


if __name__ == "__main__":
    asyncio.run(run_visible_text_test())