import asyncio
from DrissionPage import Chromium, ChromiumOptions
from CodeBox import domTreeToJson
async def test_dom_tree_to_json():
    # 初始化浏览器
    co = ChromiumOptions()
    page = Chromium(co)
    tab = page.new_tab('https://www.zoulixin.site/')  # 或换成任意页面，如 https://tonzhon.com/


    # JS 脚本：构建可视 DOM 树 JSON

    print("[*] 执行 DOM 树结构提取中...")
    result = tab.run_js(domTreeToJson)
    print("[+] 提取结果：")
    print(result if isinstance(result, str) else str(result))

    tab.close()

asyncio.run(test_dom_tree_to_json())
