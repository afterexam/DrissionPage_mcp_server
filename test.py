import asyncio
from pprint import pprint

from main import DrissionPageMCP  # 把这里替换成你实际的文件名，比如 mcp_impl.py

async def test_bilibili():
    # 初始化 MCP 实例
    mcp = DrissionPageMCP()

    # 打开浏览器
    browser_info = await mcp.connect_or_open_browser()
    tab_id = browser_info['tab_id']
    print(f"[+] Browser launched. Tab ID: {tab_id}")

    # 访问 B 站首页
    print("[*] Navigating to Bilibili...")
    await mcp.navigate(tab_id, "https://bing.com")
    mcp.wait(1)  # 等待页面加载

    # 获取交互元素信息
    print("[*] Scanning interactive elements...")
    result = mcp.get_interactive_elements_info(tab_id)
    
    # 输出结果
    if "elements" in result:
        print(f"[+] Found {len(result['elements'])} interactive elements:")
        for ele in result["elements"][:10]:  # 只展示前10个，避免刷屏
            pprint(ele)
    else:
        print("[!] Error:", result.get("error"))

    # 可选：关闭标签页
    mcp.close_tab(tab_id)

if __name__ == "__main__":
    asyncio.run(test_bilibili())
