#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import pandas as pd
import inspect
import uuid
from typing import Any, Literal, List, Dict, Optional, Union

# 导入 DrissionPage 相关的类
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.items import ChromiumElement, ChromiumTab
from DrissionPage.common import Keys

# 导入 MCP 相关
from mcp.server.fastmcp import FastMCP
from CodeBox import domTreeToJson # 假设这是你自定义的模块

# 导入其他需要的库
from PIL import Image as PILImage
import base64
import io
import time

# --- Prompts and Instructions for LLM ---
prompt = '''
你正在使用一组浏览器控制工具来执行网页自动化任务。请按照以下步骤依次使用这些工具,一直尝试直到完成任务：
1.  **启动浏览器**: 使用 `connect_or_open_browser` 启动或连接已有的浏览器实例。这是所有操作的前提。
2.  **导航**: 使用 `new_tab` 打开新的标签页或导航到目标网址。
3.  **分析页面**: 使用 `get_domTreeToJson` 获取当前页面的 DOM 树结构（JSON 格式），用于分析页面结构，识别目标元素的定位信息。
4.  **定位元素**: 根据 DOM 分析得到的线索（如文本内容、CSS 选择器等），使用 `find_element` 或 `find_elements` 查找页面中的元素，并缓存其引用。
5.  **执行操作**: 对查找到的元素执行具体操作，如 `click`、`input_text`、`get_attribute` 等。
6.  **数据抓取 (可选)**: 如果需要抓取接口数据, 依次使用 `start_network_listening`, `get_network_traffic_summary`, `get_response_body`, 和 `process_json_with_pandas_and_save`。
'''

class DrissionPageMCP:
    """
    一个基于 DrissionPage 的 MCP 工具集，用于控制浏览器执行自动化任务。
    """
    def __init__(self):
        """
        title: 初始化
        description: 初始化 DrissionPageMCP 实例，建立一个浏览器和元素缓存。
        """
        self.browser: Optional[Chromium] = None
        self.element_cache: Dict[str, ChromiumElement] = {}
        self.network_events: List[Dict] = []

    def _get_tab(self, tab_id: str) -> Optional[ChromiumTab]:
        """内部辅助函数，根据 tab_id 获取标签页对象，支持 'current' 别名。"""
        if not self.browser:
            print("[!] 浏览器未初始化")
            return None
        if tab_id == "current":
            return self.browser.latest_tab
        return self.browser.get_tab(tab_id)

    def get_domTreeToJson(self, tab_id: str = "current") -> dict:
        """
        title: 获取页面的 DOM 结构
        description: 获取指定标签页的完整 DOM 结构，并以 JSON 格式返回。这对于分析页面布局和定位元素至关重要。
        Args:
            tab_id (str): 目标标签页的ID，默认为 'current'，即当前活动标签页。
        Returns:
            dict: 包含页面DOM树的JSON对象，或在找不到标签页时返回错误信息。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        
        page_tree = tab.run_js(domTreeToJson)
        return page_tree

    async def connect_or_open_browser(self, config: dict = {'debug_port': 9222}) -> dict:
        """
        title: 启动或连接浏览器
        description: 打开一个新浏览器或接管一个已存在的浏览器。这是所有浏览器操作的入口点。
        Args:
            config (dict): 浏览器配置字典，可以包含 'debug_port', 'browser_path', 'headless' 等。
        Returns:
            dict: 包含浏览器会话信息和初始标签页的 `tab_id`、`title` 和 `url`。
        """
        co = ChromiumOptions()
        if debug_port := config.get("debug_port"):
            co.set_local_port(debug_port)
        if browser_path := config.get("browser_path"):
            co.set_browser_path(browser_path)
        if config.get("headless", False):
            co.headless(True)
            
        self.browser = Chromium(co)
        tab = self.browser.latest_tab or self.browser.new_tab()
        return {"tab_id": tab.tab_id, "title": tab.title, "url": tab.url}

    def list_tabs(self) -> List[Dict[str, Any]]:
        """
        title: 列出所有标签页
        description: 获取所有已打开标签页的列表，并标明哪个是当前活动标签页。当需要操作非当前活动标签页时，用此函数找到目标 `tab_id`。
        Returns:
            List[Dict[str, Any]]: 每个标签页的信息列表，包含 'index', 'tab_id', 'title', 'url', 和 'is_active'。
        """
        if not self.browser:
            return []
        
        tab_list = []
        all_tabs = self.browser.tabs
        active_tab = self.browser.latest_tab

        for i, tab in enumerate(all_tabs):
            try:
                tab_info = {
                    "index": i + 1,
                    "tab_id": tab.tab_id,
                    "title": tab.title,
                    "url": tab.url,
                    "is_active": tab == active_tab,
                }
                tab_list.append(tab_info)
            except Exception as e:
                print(f"[!] Warning: Failed to get info for a tab, skipping. Error: {e}")
            
        return tab_list

    async def new_tab(self, url: str) -> dict:
        """
        title: 新建标签页并导航
        description: 打开一个新的浏览器标签页并导航到指定的URL。
        Args:
            url (str): 要在新标签页中打开的网址。
        Returns:
            dict: 新标签页的信息，包含 'tab_id', 'title', 'url' 和页面加载后的DOM结构。
        """
        if not self.browser:
            await self.connect_or_open_browser()
        tab = self.browser.new_tab(url)
        return {"tab_id": tab.tab_id, "title": tab.title, "url": tab.url, 'domTree_json': self.get_domTreeToJson(tab.tab_id)}

    def close_tab(self, tab_id: str) -> bool:
        """
        title: 关闭标签页
        description: 根据 tab_id 关闭指定的标签页。任务完成后，建议关闭不再需要的标签页以释放资源。
        Args:
            tab_id (str): 目标标签页的ID。
        Returns:
            bool: 如果成功关闭则返回 True，否则返回 False。
        """
        tab = self._get_tab(tab_id)
        if tab:
            tab.close()
            self.clear_element_cache() 
            return True
        return False

    def send_key(self, tab_id: str, key: Literal["Enter", "Escape", "Backspace", "Tab", "PageUp", "PageDown", "End", "Home"]) -> dict:
        """
        title: 发送特殊按键
        description: 向指定的标签页发送一个特殊的键盘按键，可用于提交表单 (Enter)、关闭弹窗 (Escape) 等。
        Args:
            tab_id (str): 目标标签页的ID。
            key (str): 要发送的特殊按键，从预设的列表中选择。
        Returns:
            dict: 操作成功或失败的状态。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        key_map = {
            "Enter": Keys.ENTER, "Escape": Keys.ESCAPE, "Backspace": Keys.BACKSPACE, 
            "Tab": Keys.TAB, "PageUp": Keys.PAGE_UP, "PageDown": Keys.PAGE_DOWN,
            "End": Keys.END, "Home": Keys.HOME
        }
        tab.actions.type(key_map[key])
        return {"status": "success", "action": "send_key", "key": key}

    def find_element(self, tab_id: str, by: Literal['css', 'text'], value: str) -> dict:
        """
        title: 查找单个元素
        description: 在指定标签页中通过 CSS选择器 或 模糊文本匹配 查找单个元素，并将其ID存入缓存以便后续操作。
        Args:
            tab_id (str): 目标标签页的ID。
            by (str): 定位策略，'css' 或 'text'。
            value (str): 定位策略对应的值。
        Returns:
            dict: 包含 `element_id` 的字典和元素的文本及HTML，或错误信息。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab with id '{tab_id}' not found."}
        locator = f'text:{value}' if by == 'text' else f'css:{value}'
        element = tab.ele(locator, timeout=5)
        if element:
            element_id = f"elem-{uuid.uuid4()}"
            self.element_cache[element_id] = element
            return {"element_id": element_id, 'texts': element.texts(), 'html': element.html}
        
        raise Exception(f"Element not found by '{by}' with value '{value}'")

    def find_elements(self, tab_id: str, by: Literal['css', 'text'], value: str) -> dict:
        """
        title: 查找多个元素
        description: 在指定标签页中查找所有匹配的元素，并返回它们的 element_id 列表和对应的文本。
        Args:
            tab_id (str): 目标标签页的ID。
            by (str): 定位策略，'css' 或 'text'。
            value (str): 定位策略对应的值。
        Returns:
            dict: 包含多个元素的 `element_id` 和 `texts` 列表，或错误信息。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab with id '{tab_id}' not found."}
        
        locator = f'text:{value}' if by == 'text' else f'css:{value}'
        elements = tab.eles(locator, timeout=5)
        if not elements:
            raise Exception(f"No elements found by '{by}' with value '{value}'")
        
        results = [{"element_id": f"elem-{uuid.uuid4()}", "texts": ele.texts()} for ele in elements]
        for i, ele in enumerate(elements):
            self.element_cache[results[i]['element_id']] = ele
            
        return {"elements": results}

    def run_javascript(self, tab_id: str, js_script: str) -> dict:
        """
        title: 执行JavaScript代码
        description: 【高阶工具】在指定的标签页中执行一段任意的 JavaScript 代码，并返回结果。当标准工具无法满足特殊需求时使用。
        Args:
            tab_id (str): 目标标签页的ID, 可传入 'current'。
            js_script (str): 要执行的 JavaScript 代码字符串。脚本中必须有 `return` 语句才能获取返回值。
        Returns:
            dict: 包含执行结果的字典 `{'result': ...}` 或错误信息 `{'error': ...}`。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        
        try:
            result = tab.run_js(js_script)
            return {"result": result}
        except Exception as e:
            return {"error": f"JavaScript execution failed: {e}"}

    def clear_element_cache(self) -> str:
        """
        title: 清空元素缓存
        description: 清除所有已缓存的元素引用。在页面跳转、刷新或关闭后，应调用此函数以避免操作过时元素。
        Returns:
            str: 清理完成的消息。
        """
        count = len(self.element_cache)
        self.element_cache.clear()
        return f"Element cache cleared. {count} elements removed."

    def read_element_cache(self) -> Dict[str, str]:
        """
        title: 读取元素缓存
        description: 查看所有当前已缓存的元素及其ID。
        Returns:
            dict: 一个字典，键是 element_id，值是元素的简要描述。
        """
        return {eid: str(ele) for eid, ele in self.element_cache.items()}

    def click(self, element_id: str) -> dict:
        """
        title: 点击元素
        description: 点击一个已通过 find_element 获取到的元素。
        Args:
            element_id (str): 目标元素的唯一ID。
        Returns:
            dict: 操作成功或失败的状态。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return {"error": f"Element ID '{element_id}' not found in cache."}
        element.click()
        return {"status": "success", "action": "click"}

    def input_text(self, element_id: str, text: str, clear_first: bool = True) -> dict:
        """
        title: 输入文本
        description: 向一个已获取的元素（通常是输入框）输入文本。
        Args:
            element_id (str): 目标元素的唯一ID。
            text (str): 要输入的文本内容。
            clear_first (bool): 输入前是否先清空输入框，默认为 True。
        Returns:
            dict: 操作成功或失败的状态。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return {"error": f"Element ID '{element_id}' not found in cache."}
        element.input(text, clear=clear_first)
        return {"status": "success", "action": "input_text"}

    def get_attribute(self, element_id: str, attribute_name: str) -> dict:
        """
        title: 获取元素属性
        description: 获取一个已获取元素的指定HTML属性值，如 'href', 'src', 'value', 'class' 等。
        Args:
            element_id (str): 目标元素的唯一ID。
            attribute_name (str): 要获取的属性名。
        Returns:
            dict: 包含属性值的字典。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return {"error": f"Element ID '{element_id}' not found in cache."}
        return {"attribute_value": element.attr(attribute_name)}
    
    def get_screenshot_of_element(self, element_id: str) -> Union[bytes, str]:
        """
        title: 获取元素截图
        description: 获取单个元素的截图，比如播放按钮、验证码等，用于需要对特定区域进行视觉分析的场景。
        Args:
            element_id (str): 目标元素的唯一ID。
        Returns:
            bytes | str: 元素截图的二进制数据 (JPEG格式)，或错误信息。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return f"Error: Element ID '{element_id}' not found in cache."
        return element.get_screenshot(as_bytes='jpeg')

    def wait(self, seconds: Union[int, float]) -> str:
        """
        title: 等待
        description: 让程序暂停指定的秒数，用于等待页面加载或某些异步操作完成。
        Args:
            seconds (int | float): 需要等待的秒数。
        Returns:
            str: 表示等待完成的消息。
        """
        time.sleep(seconds)
        return f"Waited for {seconds} seconds."
    
    # --- 网络监听与数据处理工具 ---

    def _network_event_handler(self, **kwargs):
        """内部函数：处理网络事件的回调"""
        if kwargs.get('method') == 'Network.responseReceived':
            self.network_events.append(kwargs)

    def start_network_listening(self, tab_id: str = "current") -> dict:
        """
        title: 开启网络监听 (数据分析第1步)
        description: 对指定标签页开启网络流量监听。在需要捕获API请求（如XHR）来获取数据时，首先调用此工具。
        Args:
            tab_id (str): 目标标签页的ID，默认为 'current'。
        Returns:
            dict: 操作状态。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        
        self.network_events = []
        tab.driver.set_callback('Network.responseReceived', self._network_event_handler)
        tab.run_cdp('Network.enable')
        return {"status": "Network listening has been enabled."}
        
    def get_network_traffic_summary(self, tab_id: str = "current") -> dict:
        """
        title: 获取网络流量摘要 (数据分析第2步)
        description: 获取已捕获网络请求的摘要列表，包含URL、方法、状态码和MIME类型。用于判断哪个请求可能包含目标数据。
        Args:
            tab_id (str): 目标标签页的ID，默认为 'current'。
        Returns:
            dict: 包含网络流量摘要列表的字典。
        """
        if not self.network_events:
            return {"error": "No network traffic captured. Did you run 'start_network_listening' first?"}
            
        summary = [
            {
                "request_id": event.get('params', {}).get('requestId'),
                "url": event.get('params', {}).get('response', {}).get('url'),
                "method": event.get('params', {}).get('response', {}).get('request', {}).get('method', 'GET'),
                "status": event.get('params', {}).get('response', {}).get('status'),
                "mime_type": event.get('params', {}).get('response', {}).get('mimeType')
            }
            for event in self.network_events
        ]
        return {"traffic_summary": summary}
        
    def get_response_body(self, tab_id: str, request_id: str) -> dict:
        """
        title: 获取响应体 (数据分析第3步)
        description: 根据 request_id 获取单个网络响应的具体内容（body）。当从摘要中发现可疑的JSON请求后，用此工具提取其数据。
        Args:
            tab_id (str): 目标标签页的ID。
            request_id (str): 目标网络请求的ID，从 `get_network_traffic_summary` 中获取。
        Returns:
            dict: 包含响应体内容的字典。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        
        try:
            result = tab.run_cdp('Network.getResponseBody', requestId=request_id)
            return result
        except Exception as e:
            return {"error": f"Could not get response body for request ID '{request_id}': {e}"}

    def process_json_with_pandas_and_save(self, json_data: str, output_filename: str) -> dict:
        """
        title: 处理JSON并保存为CSV (数据分析第4步)
        description: 使用Pandas库将JSON格式的字符串数据转换并保存为CSV文件。
        Args:
            json_data (str): 包含列表的JSON格式字符串。
            output_filename (str): 要保存的本地文件名，必须以 '.csv' 结尾。
        Returns:
            dict: 操作结果，包含状态、文件路径和保存的记录数。
        """
        if not output_filename.endswith('.csv'):
            return {"error": "Output filename must end with .csv"}
            
        try:
            data = json.loads(json_data)
            df = pd.json_normalize(data)
            df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            return {"status": "success", "file_path": output_filename, "records_saved": len(df)}
        except Exception as e:
            return {"error": f"Failed to process data with pandas and save: {e}"}

    def count(self, target: str, text: str) -> int:
        """
        title: 统计子字符串出现次数
        description: 统计一个目标字符串（target）在另一个文本（text）中出现的次数。
        Args:
            target (str): 要计数的子字符串。
            text (str): 在其中进行搜索的文本。
        Returns:
            int: 目标字符串出现的次数。
        """
        return text.count(target)

# --- MCP Server Initialization ---
mcp = FastMCP("DrissionPageMCP-UltimateScanner", log_level="ERROR", instructions=prompt)
b = DrissionPageMCP()

# 动态添加实例方法作为工具
for name, method in inspect.getmembers(b, predicate=inspect.ismethod):
    if not name.startswith('_'):
        mcp.add_tool(method)

def main():
    print("DrissionPage MCP server (Ultimate Scanner) is running...")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()