#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import pandas as pd
import inspect
import uuid
from typing import Any, Literal, List, Dict
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.items import ChromiumElement, ChromiumTab
from DrissionPage.common import Keys
from mcp.server.fastmcp import FastMCP
from CodeBox import domTreeToJson

from PIL import Image as PILImage
import base64
import io
prompt = '''
你正在使用一组浏览器控制工具来执行网页自动化任务。请按照以下步骤依次使用这些工具,一直尝试直到完成任务：
启动或连接已有的浏览器实例。该步骤是所有后续操作的前提。
打开新的标签页或导航到目标网址。
获取当前页面的 DOM 树结构（JSON 格式）。这一步是为了分析页面结构，识别目标元素的定位信息，比如通过 text, css 等方式。
根据 DOM 分析得到的线索（如文本内容、CSS 选择器等），查找页面中的单个元素，并缓存其引用。
对查找到的元素执行具体操作，如点击、输入、发送按键或获取属性。
'''

class DrissionPageMCP:
    def __init__(self):
        """初始化 DrissionPageMCP 实例，建立一个元素缓存。"""
        self.browser: Chromium | None = None
        self.element_cache: Dict[str, ChromiumElement] = {}

    def _get_tab(self, tab_id: str) -> ChromiumTab | None:
        """内部辅助函数，根据 tab_id 获取标签页对象，支持 'current' 别名。"""
        if not self.browser:
            print("[!] 浏览器未初始化")
            return None
        if tab_id == "current":
            return self.browser.latest_tab
        return self.browser.get_tab(tab_id)

    def get_domTreeToJson(self, tab_id: str) -> dict:
        """
        获取给定tab的json页面信息
        """
        tab = self._get_tab(tab_id)
        if not tab: return {"error": f"Tab {tab_id} not found."}
        
        page_tree = tab._run_js(domTreeToJson)
        
        return page_tree

    async def connect_or_open_browser(self, config: dict = {'debug_port': 9222}) -> dict:
        """
        打开一个新浏览器或接管一个已存在的浏览器。
        这是所有操作的入口点。
        Returns:
            dict: 包含浏览器信息和初始标签页的 `tab_id`。
        """
        co = ChromiumOptions()
        if debug_port := config.get("debug_port"): co.set_local_port(debug_port)
        if browser_path := config.get("browser_path"): co.set_browser_path(browser_path)
        if config.get("headless", False): co.headless(True)
        self.browser = Chromium(co)
        tab = self.browser.latest_tab or self.browser.new_tab()
        return {"tab_id": tab.tab_id, "title": tab.title, "url": tab.url}

    def list_tabs(self) -> List[Dict]:
            """
            获取所有已打开标签页的列表，并标明当前活动标签页。
            当需要操作非当前活动标签页时，可以用此函数找到目标 `tab_id`。
            Returns:
                List[Dict]: 每个标签页的信息列表，包含 'index', 'tab_id', 'title', 'url', 'is_active'。
            """
            if not self.browser:
                return []
            
            tab_list = []
            # [改动] 使用 .get_tabs() 方法，这是 DrissionPage 的正确用法
            all_tabs = self.browser.get_tabs()
            # 获取当前活动的标签页，用于后续判断
            active_tab = self.browser.latest_tab

            # [改动] 使用 for 循环和 enumerate 来方便地添加索引和判断活动状态
            for i, tab in enumerate(all_tabs):
                try:
                    tab_info = {
                        "index": i + 1,  # 增加一个 1-based 的索引，方便人类和 AI 沟通
                        "tab_id": tab.tab_id,
                        "title": tab.title,
                        "url": tab.url,
                        "is_active": tab == active_tab  # 增加一个布尔值，标明是否为当前活动标签
                    }
                    tab_list.append(tab_info)
                except Exception as e:
                    # 增加一个try-except，防止某个tab因为意外关闭等原因导致读取信息失败，从而中断整个函数
                    print(f"[!] Warning: Failed to get info for a tab, skipping. Error: {e}")
                
            return tab_list

    async def new_tab(self, url: str) -> dict:
        """
        打开一个新的浏览器标签页并导航到指定网址。
        Args:
            url (str): 要在新标签页中打开的网址。

        Returns:
            dict: 新标签页的信息，包含 'tab_id', 'title', 'url'。
        """
        await self.connect_or_open_browser()
        # if not self.browser: a = await self.connect_or_open_browser()
        tab = self.browser.new_tab(url)
        return {"tab_id": tab.tab_id, "title": tab.title, "url": tab.url,'domTree_json':self.get_domTreeToJson(tab.tab_id)}

    def close_tab(self, tab_id: str) -> bool:
        """
        根据 tab_id 关闭指定的标签页。
        任务完成后，建议关闭不再需要的标签页以释放资源。
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
        向指定的标签页发送一个特殊的键盘按键。
        可用于提交表单 (Enter)、关闭弹窗 (Escape) 等。
        Args:
            tab_id (str): 目标标签页的ID。
            key (str): 要发送的特殊按键。

        Returns:
            dict: 操作结果。
        """
        tab = self._get_tab(tab_id)
        if not tab: return {"error": f"Tab {tab_id} not found."}
        key_map = {
            "Enter": Keys.ENTER, "Escape": Keys.ESCAPE, "Backspace": Keys.BACKSPACE, 
            "Tab": Keys.TAB, "PageUp": Keys.PAGE_UP, "PageDown": Keys.PAGE_DOWN,
            "End": Keys.END, "Home": Keys.HOME
        }
        tab.actions.type(key_map[key])
        return {"status": "success", "action": "send_key", "key": key}

    def find_element(self, tab_id: str, by: Literal['css', 'text'], value: str) -> dict:
        """
        在指定标签页中查找单个元素，并返回其 element_id。
        Args:
            tab_id (str): 目标标签页的ID。
            by (str): 定位策略，'css' 或 'text',其中text为模糊匹配
            value (str): 定位策略对应的值。
        Returns:
            dict: 包含 `element_id` 的字典，或错误信息。
        """
        tab = self._get_tab(tab_id)
        if not tab: return {"error": f"Tab with id {tab_id} not found."}
        locator = f'text:{value}' if by == 'text' else f'css:{value}'
        element = tab.ele(locator, timeout=5)
        if element:
            element_id = f"elem-{uuid.uuid4()}"
            self.element_cache[element_id] = element
            return {"element_id": element_id,'texts':element.texts(),'html':element.html}
        else:
            raise Exception(f"Element not found by {by} with value '{value}'")

    def find_elements(self, tab_id: str, by: Literal['css', 'text'], value: str) -> dict:
        """
        在指定标签页中查找多个元素，并返回它们的 element_id 列表和对应的文本。
        Args:
            tab_id (str): 目标标签页的ID。
            by (str): 定位策略，'css' 或 'text'，其中 text 为模糊匹配。
            value (str): 定位策略对应的值。
        Returns:
            dict: 包含多个元素的 `element_id` 和 `texts` 列表，或错误信息。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab with id {tab_id} not found."}
        
        locator = f'text:{value}' if by == 'text' else f'css:{value}'
        elements = tab.eles(locator, timeout=5)
        if not elements:
            raise Exception(f"No elements found by {by} with value '{value}'")
        results = []
        for ele in elements:
            element_id = f"elem-{uuid.uuid4()}"
            self.element_cache[element_id] = ele
            results.append({
                "element_id": element_id,
                "texts": ele.texts()
            })
        return {"elements": results}

    def run_javascript(self, tab_id: str, js_script: str) -> dict:
        """
        【高阶工具】在指定的标签页中执行一段任意的 JavaScript 代码，并返回结果。
        当标准工具无法满足特殊的信息提取或操作需求时，可使用此工具。
        Args:
            tab_id (str): 目标标签页的ID, 可传入 'current'。
            js_script (str): 要执行的 JavaScript 代码字符串。脚本中必须有 `return` 语句才能获取返回值。

        Returns:
            dict: 包含执行结果的字典 `{'result': ...}` 或错误信息 `{'error': ...}`。
        
        用法示例:
        - 获取页面标题: `js_script="return document.title;"`
        - 获取特定元素的值: `js_script="return document.querySelector('#my-element').value;"`
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        
        try:
            result = tab.run_js(js_script)
            return {"result": result}
        except Exception as e:
            # 返回详细的JS错误信息，方便LLM调试自己的代码
            return {"error": f"JavaScript execution failed: {e}"}



    def clear_element_cache(self) -> str:
        """
        清除所有已缓存的元素。
        在页面发生重大变化（如跳转、刷新）或关闭后，建议调用此函数以防止引用到旧的、已失效的元素。
        Returns:
            str: 清理完成的消息。
        """
        count = len(self.element_cache)
        self.element_cache.clear()
        return f"Element cache cleared. {count} elements removed."

    def read_element_cache(self) -> dict:
        """
        该方法缓存中查看所有已经找到的元素。
        Returns:
            dict: 所有已经找到的元素
        """
        return self.element_cache

    def click(self, element_id: str) -> dict:
        """
        需要先调用find_element获取元素ID,点击该元素
        Args:
            element_id (str): 目标元素的唯一ID, 需要去获取

        Returns:
            dict: 操作结果。
        """
        element = self.element_cache.get(element_id)
        if not element: return {"error": f"Element ID '{element_id}' not found in cache."}
        element.click()
        return {"status": "success", "action": "click"}

    def input_text(self, element_id: str, text: str, clear_first: bool = True) -> dict:
        """
        向一个由扫描或查找工具获取到的元素输入文本。

        Args:
            element_id (str): 目标元素的唯一ID。
            text (str): 要输入的文本内容。
            clear_first (bool): 输入前是否先清空输入框，默认为 True。

        Returns:
            dict: 操作结果。
        """
        element = self.element_cache.get(element_id)
        if not element: return {"error": f"Element ID '{element_id}' not found in cache."}
        element.input(text, clear=clear_first)
        return {"status": "success", "action": "input_text"}

    def get_attribute(self, element_id: str, attribute_name: str) -> dict:
        """
        获取一个由扫描或查找工具获取到的元素的指定HTML属性值。
        例如 'href' (获取链接), 'value' (获取输入框当前的值), 'class' 等。

        Args:
            element_id (str): 目标元素的唯一ID。
            attribute_name (str): 想要获取的属性名。

        Returns:
            dict: 包含属性值的字典。
        """
        element = self.element_cache.get(element_id)
        if not element: return {"error": f"Element ID '{element_id}' not found in cache."}
        return {"attribute_value": element.attr(attribute_name)}
    
    def get_screenshot_of_element(self, element_id: str) -> bytes:
        """
        获取单个元素的截图。比如播放按钮等
        用于需要对特定区域进行视觉分析的场景。

        Args:
            element_id (str): 目标元素的唯一ID。

        Returns:
            bytes: 元素截图的二进制数据 (JPEG格式)。
        """
        element = self.element_cache.get(element_id)
        if not element: return b''
        return element.get_screenshot(as_bytes='jpeg')

    def wait(self, seconds: int) -> str:
        """
        让程序暂停指定的秒数。
        用于等待页面加载或某些异步操作完成。

        Args:
            seconds (int): 需要等待的秒数。

        Returns:
            str: 表示等待完成的消息。
        """
        import time
        time.sleep(seconds)
        return f"Waited for {seconds} seconds."
    

    # --- 新增：网络监听与数据处理工具 ---

    def _network_event_handler(self, **kwargs):
        """内部函数：处理网络事件的回调"""
        if not hasattr(self, 'network_events'):
            self.network_events = []
        
        # 我们只关心收到响应的事件
        if kwargs.get('method') == 'Network.responseReceived':
            self.network_events.append(kwargs)

    def start_network_listening(self, tab_id: str = "current") -> dict:
        """
        【数据分析第1步】开启对指定标签页的网络监听。
        在需要捕获API请求等场景下，首先调用此工具。
        """
        tab = self._get_tab(tab_id)
        if not tab: return {"error": f"Tab '{tab_id}' not found."}
        
        self.network_events = [] # 清空旧数据
        tab.driver.set_callback('Network.responseReceived', self._network_event_handler)
        tab.run_cdp('Network.enable')
        return {"status": "Network listening has been enabled."}
        
    def get_network_traffic_summary(self, tab_id: str = "current") -> dict:
        """
        【数据分析第2步】获取已捕获网络请求的摘要列表。
        此工具不返回具体数据内容，只返回请求的URL、类型等元信息，用于判断哪个请求可能包含有价值的数据。
        """
        if not hasattr(self, 'network_events') or not self.network_events:
            return {"error": "No network traffic captured. Did you run 'start_network_listening' first?"}
            
        summary = []
        for event in self.network_events:
            params = event.get('params', {})
            response = params.get('response', {})
            summary.append({
                "request_id": params.get('requestId'),
                "url": response.get('url'),
                "method": response.get('request', {}).get('method', 'GET'), # 修正：从response中获取method
                "status": response.get('status'),
                "mime_type": response.get('mimeType')
            })
        return {"traffic_summary": summary}
        
    def get_response_body(self, tab_id: str, request_id: str) -> dict:
        """
        【数据分析第3步】根据 request_id 获取单个网络响应的具体内容（body）。
        当从摘要中发现可疑的JSON请求后，用此工具提取其数据。
        """
        tab = self._get_tab(tab_id)
        if not tab: return {"error": f"Tab '{tab_id}' not found."}
        
        try:
            # DrissionPage的CDP方法可能与原始定义略有不同，这里我们直接调用
            result = tab.run_cdp('Network.getResponseBody', requestId=request_id)
            return result
        except Exception as e:
            return {"error": f"Could not get response body for request ID '{request_id}': {e}"}

    def process_json_with_pandas_and_save(self, json_data: str, output_filename: str) -> dict:
        """
        【数据分析第4步】使用Pandas处理JSON数据并将其保存为CSV文件。
        Args:
            json_data (str): 包含列表的JSON格式字符串。
            output_filename (str): 要保存的本地文件名，例如 'my_data.csv'。
        """
        if not output_filename.endswith('.csv'):
            return {"error": "Output filename must end with .csv"}
            
        try:
            # 将JSON字符串解析为Python对象
            data = json.loads(json_data)
            
            # 使用 pandas.json_normalize 处理可能嵌套的JSON
            df = pd.json_normalize(data)
            
            # 保存为CSV文件，不包含索引列
            df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            
            return {"status": "success", "file_path": output_filename, "records_saved": len(df)}
            
        except Exception as e:
            return {"error": f"Failed to process data with pandas and save: {e}"}

    def count(self,target: str, text: str) -> int:
        """
        统计 {target} 在 {text} 中出现的次数。
        """
        return text.count(target)


#region 初始化mcp
mcp = FastMCP("DrissionPageMCP-UltimateScanner", log_level="ERROR", instructions=prompt)
b = DrissionPageMCP()




for name, method in inspect.getmembers(b, predicate=inspect.ismethod):
    if not name.startswith('_'):
        mcp.add_tool(method)

def main():
    print("DrissionPage MCP server (Ultimate Scanner) is running...")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()