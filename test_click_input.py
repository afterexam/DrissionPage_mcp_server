import asyncio
import json
from main import DrissionPageMCP

GITHUB_LOGIN_URL = "https://github.com/login"

async def run_github_test():
    """
    一个完整的端到端测试脚本，用于在 GitHub 登录页面上测试
    `find_element`, `input_text` 和 `click` 函数的功能和反馈机制。
    """
    print("--- 测试开始：GitHub 登录流程 ---")
    
    agent = DrissionPageMCP()

    # --- 步骤 1: 启动浏览器 ---
    print("\n[Step 1] 正在启动浏览器...")
    connect_result = await agent.connect_or_open_browser()
    tab_id = connect_result.get("tab_id")
    if not tab_id:
        print(f"  [!] 失败：浏览器未能成功启动。返回信息: {connect_result}")
        return
    print(f"  [+] 成功：浏览器已启动，当前标签页ID: {tab_id}")

    # --- 步骤 2: 导航到 GitHub 登录页面 ---
    print(f"\n[Step 2] 正在导航到: {GITHUB_LOGIN_URL}...")
    nav_result = await agent.get(url=GITHUB_LOGIN_URL, tab_id=tab_id)
    if nav_result.get("error"):
        print(f"  [!] 失败: {nav_result['error']}")
        agent.browser.close()
        return
    print(f"  [+] 成功：已打开页面 '{nav_result.get('title')}'")

    # --- 步骤 3: 定位关键元素 ---
    print("\n[Step 3] 正在定位用户名、密码输入框和登录按钮...")
    
    try:
        username_field = agent.find_element(tab_id=tab_id, by='css', value='#login_field')
        username_id = username_field.get("element_id")
        print(f"  [+] 成功：找到用户名输入框, ID: {username_id}")

        password_field = agent.find_element(tab_id=tab_id, by='css', value='#password')
        password_id = password_field.get("element_id")
        print(f"  [+] 成功：找到密码输入框, ID: {password_id}")

        login_button = agent.find_element(tab_id=tab_id, by='css', value='input[name="commit"]')
        login_button_id = login_button.get("element_id")
        print(f"  [+] 成功：找到登录按钮, ID: {login_button_id}")
    except Exception as e:
        print(f"  [!] 失败: 定位元素时出错 - {e}")
        return

    # --- 步骤 4: 测试 input_text ---
    print("\n[Step 4] 正在测试 input_text...")
    input_result = agent.input_text(element_id=username_id, text="test-user-12345")
    print(input_result)

    input_result_pass = agent.input_text(element_id=password_id, text="a-fake-password")
    print(input_result_pass)

    # --- 步骤 5: 测试 click ---
    print("\n[Step 5] 正在测试 click...")
    click_result = agent.click(element_id=login_button_id)
    print(f"  [+] 登录按钮已点击。反馈: {click_result.get('feedback')}")
    
    # 验证点击后URL是否发生变化
    assert click_result.get('feedback', {}).get('url_changed') == True

    # --- 步骤 6: 最终验证 ---
    print("\n[Step 6] 验证登录后的页面状态...")
    final_tabs = agent.list_tabs()
    final_url = final_tabs[0].get('url') if final_tabs else ""
    if "session" in final_url:
         print(f"  [🎉] 测试成功！点击后页面已跳转到包含 'session' 的URL: {final_url}")
    else:
        print(f"  [!] 测试失败：点击后URL未按预期跳转。当前URL: {final_url}")

    # --- 清理 ---
    print("\n--- 测试结束 ---")

if __name__ == "__main__":
    asyncio.run(run_github_test())