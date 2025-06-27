#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import pandas as pd
import inspect
import uuid
from typing import Any, Literal, List, Dict, Optional, Union, Annotated

# DrissionPage and MCP imports
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.items import ChromiumElement, ChromiumTab
from DrissionPage.common import Keys
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Placeholder for your custom JS module
from CodeBox import domTreeToJson
# Other imports
from PIL import Image as PILImage
import base64
import io
import time
import os
prompt = '''
你正在使用一组浏览器控制工具来执行网页自动化任务。请按照以下步骤依次使用这些工具,完全自主完成任务：
1.  **启动浏览器**: 使用 `connect_or_open_browser` 启动或连接已有的浏览器实例。这是所有操作的前提。
2.  **导航**: 使用 `new_tab` 打开新的标签页或导航到目标网址。
3.  **分析页面**: 获取当前页面的信息，用于分析页面结构，识别目标元素的定位信息。
4.  **定位元素**: 根据 DOM 分析得到的线索（如文本内容、CSS 选择器等），使用 `find_element` 或 `find_elements` 查找页面中的元素，并缓存其引用。
5.  **执行操作**: 对查找到的元素执行具体操作，如 `click`、`input_text`、`get_attribute` 等。
6.  **数据抓取 (可选)**: 如果需要抓取接口数据, 依次使用 `start_network_listening`, `get_network_traffic_summary`, `get_response_body`, 和 `process_json_with_pandas_and_save`。
'''

class DrissionPageMCP:
    """
    一个基于 DrissionPage 的 MCP 工具集，用于控制浏览器执行自动化任务。
    """
    def __init__(self):
        """title: 初始化工具集
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

    def get_domTreeToJson(
        self, 
        tab_id: Annotated[str, Field(description="目标标签页的ID，可传入 'current' 代表当前活动标签页。")] = "current"
    ) -> dict:
        """title: 获取页面的 DOM 结构
        description: 获取指定标签页的完整 DOM 结构，并以 JSON 格式返回。这对于分析页面布局和定位元素至关重要。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        
        page_tree = tab.run_js(domTreeToJson)
        return page_tree

    async def connect_or_open_browser(
        self, 
        config: Annotated[dict, Field(description="(可选)浏览器配置字典，可以包含 'debug_port', 'browser_path', 'headless' 等。")] = {'debug_port': 9222}
    ) -> dict:
        """title: 启动或连接浏览器
        description: 打开一个新浏览器或接管一个已存在的浏览器。这是所有浏览器操作的入口点。
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

    async def get(
        self, 
        url: Annotated[str, Field(description="url网址")],
        tab_id: Annotated[str,Field(description="tab id(可选),默认为当前tab")] = 'current'
    ) -> dict:
        """title: 导航到新网址
        description: 在指定的标签页中导航到一个新的网址。这是在现有标签页上改变页面的核心方法。
        """
        # (这里不再需要从 params 解析，直接使用 url 和 tab_id)
        if not url:
            return {"error": "参数错误：必须提供 'url'。"}

        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"标签页 '{tab_id}' 未找到。"}
        
        try:
            # DrissionPage 的 get 方法是同步的，但在异步函数中可以 await
            tab.get(url)
            
            return {
                "status": "success",
                "tab_id": tab.tab_id,
                "title": tab.title,
                "url": tab.url
            }
        except Exception as e:
            return {"error": f"导航到 {url} 失败: {e}"}

    def list_tabs(self) -> List[Dict[str, Any]]:
        """title: 列出所有标签页
        description: 获取所有已打开标签页的id，并标明哪个是当前活动标签页。
        """
        if not self.browser:
            return []
        
        tab_list = []
        all_tabs = self.browser.get_tabs() # 使用 get_tabs() 方法
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

    async def new_tab(
        self, 
        url: Annotated[str, Field(description="要在新标签页中打开的网址。")]
    ) -> dict:
        """title: 新建标签页并导航
        description: 打开一个新的浏览器标签页并导航到指定的URL。
        """
        # await self.connect_or_open_browser()
        # if not self.browser:
        #     await self.connect_or_open_browser()
        tab = self.browser.new_tab(url)
        return {"tab_id": tab.tab_id, "title": tab.title, "url": tab.url}

    def close_tab(
        self, 
        tab_id: Annotated[str, Field(description="要关闭的目标标签页的ID。")]
    ) -> bool:
        """title: 关闭标签页
        description: 根据 tab_id 关闭指定的标签页。任务完成后，建议关闭不再需要的标签页以释放资源。
        """
        tab = self._get_tab(tab_id)
        if tab:
            tab.close()
            self.clear_element_cache() 
            return True
        return False

    def send_key(
        self, 
        tab_id: Annotated[str, Field(description="目标标签页的ID, 可传入 'current'。")], 
        key: Annotated[Literal["Enter", "Escape", "Backspace", "Tab", "PageUp", "PageDown", "End", "Home"], Field(description="要发送的特殊按键，例如 'Enter', 'Escape'。")]
    ) -> dict:
        """title: 发送特殊按键
        description: 向指定的标签页发送一个特殊的键盘按键，可用于提交表单 (Enter)、关闭弹窗 (Escape) 等。
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

    def find_element(
        self, 
        tab_id: Annotated[str, Field(description="目标标签页的ID, 可传入 'current'。")], 
        by: Annotated[Literal['css', 'text'], Field(description="定位策略, 'css' (CSS选择器) 或 'text' (模糊文本匹配)。")], 
        value: Annotated[str, Field(description="定位策略对应的值。")]
    ) -> dict:
        """title: 查找单个元素
        description: 在指定标签页中通过 CSS选择器 或 模糊文本匹配 查找单个元素，并将其ID存入缓存以便后续操作。
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

    def find_elements(
        self, 
        tab_id: Annotated[str, Field(description="目标标签页的ID, 可传入 'current'。")], 
        by: Annotated[Literal['css', 'text'], Field(description="定位策略, 'css' (CSS选择器) 或 'text' (模糊文本匹配)。")], 
        value: Annotated[str, Field(description="定位策略对应的值。")]
    ) -> dict:
        """title: 查找多个元素
        description: 在指定标签页中查找所有匹配的元素，并返回它们的 element_id 列表和对应的文本。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab with id '{tab_id}' not found."}
        
        locator = f'text:{value}' if by == 'text' else f'css:{value}'
        elements = tab.eles(locator, timeout=5)
        if not elements:
            raise Exception(f"No elements found by '{by}' with value '{value}'")
        
        results = []
        for ele in elements:
            element_id = f"elem-{uuid.uuid4()}"
            self.element_cache[element_id] = ele
            results.append({
                "element_id": element_id,
                "texts": ele.texts()
            })
        return {"elements": results}

    def run_javascript(
        self, 
        tab_id: Annotated[str, Field(description="目标标签页的ID, 可传入 'current'。")], 
        js_script: Annotated[str, Field(description="要执行的 JavaScript 代码字符串。脚本中必须有 `return` 语句才能获取返回值。")]
    ) -> dict:
        """title: 执行JavaScript代码
        description: 【高阶工具】在指定的标签页中执行一段任意的 JavaScript 代码，并返回结果。当标准工具无法满足特殊需求时使用。
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
        """title: 清空元素缓存
        description: 清除所有已缓存的元素引用。在页面跳转、刷新或关闭后，应调用此函数以避免操作过时元素。
        """
        count = len(self.element_cache)
        self.element_cache.clear()
        return f"Element cache cleared. {count} elements removed."

    def read_element_cache(self) -> Dict[str, str]:
        """title: 读取元素缓存
        description: 查看所有当前已找到过的元素ID和具体信息
        """
        return {eid: str(ele) for eid, ele in self.element_cache.items()}

    def click(
        self, 
        element_id: Annotated[str, Field(description="目标元素的唯一ID，通过 find_element 或 find_elements 获取。")]
    ) -> dict:
        """title: 点击元素
        description: 点击一个已通过 find_element 获取到的元素。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return {"error": f"Element ID '{element_id}' not found in cache."}
        element.click()
        return {"status": "success", "action": "click"}

    def input_text(
        self, 
        element_id: Annotated[str, Field(description="目标元素的唯一ID，通过 find_element 或 find_elements 获取。")], 
        text: Annotated[str, Field(description="要输入的文本内容。")], 
        clear_first: Annotated[bool, Field(description="输入前是否先清空输入框，默认为 True。")] = True
    ) -> dict:
        """title: 输入文本
        description: 向一个已获取的元素（通常是输入框）输入文本。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return {"error": f"Element ID '{element_id}' not found in cache."}
        element.input(text, clear=clear_first)
        return {"status": "success", "action": "input_text"}

    def get_attribute(
        self, 
        element_id: Annotated[str, Field(description="目标元素的唯一ID，通过 find_element 或 find_elements 获取。")], 
        attribute_name: Annotated[str, Field(description="想要获取的HTML属性名, 例如 'href', 'value', 'class' 等。")]
    ) -> dict:
        """title: 获取元素属性
        description: 获取一个已获取元素的指定HTML属性值，如 'href', 'src', 'value', 'class' 等。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return {"error": f"Element ID '{element_id}' not found in cache."}
        return {"attribute_value": element.attr(attribute_name)}
    
    def get_screenshot_of_element(
        self, 
        element_id: Annotated[str, Field(description="目标元素的唯一ID，通过 find_element 或 find_elements 获取。")]
    ) -> Union[bytes, str]:
        """title: 获取元素截图
        description: 获取单个元素的截图，比如播放按钮、验证码等，用于需要对特定区域进行视觉分析的场景。
        """
        element = self.element_cache.get(element_id)
        if not element:
            return f"Error: Element ID '{element_id}' not found in cache."
        return element.get_screenshot(as_bytes='jpeg')

    def wait(
        self, 
        seconds: Annotated[Union[int, float], Field(description="需要等待的秒数。")]
    ) -> str:
        """title: 等待
        description: 让程序暂停指定的秒数，用于等待页面加载或某些异步操作完成。
        """
        time.sleep(seconds)
        return f"Waited for {seconds} seconds."
    
    # --- 网络监听与数据处理工具 ---

    def _network_event_handler(self, **kwargs):
        """内部函数：处理网络事件的回调"""
        if kwargs.get('method') == 'Network.responseReceived':
            self.network_events.append(kwargs)

    def start_network_listening(
        self, 
        tab_id: Annotated[str, Field(description="要开启监听的目标标签页ID, 可传入 'current'。")] = "current"
    ) -> dict:
        """title: 开启网络监听 (数据分析第1步)
        description: 对指定标签页开启网络流量监听。在需要捕获API请求（如XHR）来获取数据时，首先调用此工具。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}
        tab.listen.start(targets='api')
        return {'success': f"start listening in {tab_id}"}

    def get_captured_requests(
        self,
        tab_id: Annotated[str, Field(description="目标标签页的ID, 可传入 'current'。")] = "current"
    ) -> dict:
        """title: 获取抓取到的网络请求 (数据分析第2步)
        description: 一次性获取所有已捕获的API请求信息，包括URL、状态和JSON响应体。
        """
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}

        packets_info = []
        # 使用 tab.listen.steps() 遍历所有抓到的包
        for packet in tab.listen.steps(timeout=2):
            info = {
                "url": packet.url,
                "method": packet.method,
                "status": packet.response.status,
                "json": None
            }
            # 如果响应是JSON，直接解析并放入结果
            try:
                if isinstance(packet.response.body,dict):
                    info["json"] = packet.response.body
            except Exception:
                # 响应体不是有效的JSON，忽略
                pass
            packets_info.append(info)
        
        # 抓取完后自动停止监听，保持干净
        tab.listen.stop()
        return {"captured_requests": packets_info}

    def count(
        self,
        target: Annotated[str, Field(description="要搜索和计数的子字符串。")],
        path: Annotated[str, Field(description="待搜索的长文本在硬盘的存储位置")]
    ) -> int:
        """title: 统计子字符串出现次数
        description: 统计一个目标字符串（target）在另一个文本文件中出现的次数。
        """
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        return text.count(target)


    def get_visible_text(
        self, 
        tab_id: Annotated[str, Field(description="目标标签页的ID, 可传入 'current'。")] = "current",
        min_text_length: Annotated[int, Field(description="(可选)文本块的最小长度，低于此长度的文本将被过滤掉，默认为 2。")] = 2,
    ) -> dict:
        """title: 获取页面可见正文并保存
        description: 提取、返回并保存当前页面上所有可见的、有意义的文本。会自动过滤掉导航、按钮等无意义的短文本。
        """
        output_dir = "Web_info"
        tab = self._get_tab(tab_id)
        if not tab:
            return {"error": f"Tab '{tab_id}' not found."}

        try:
            # 1. 直接获取 <body> 元素的所有文本内容
            full_text = tab.ele('tag:body').text
            if not full_text:
                return {"visible_text": "Page body contains no text."}

            # 2. 在 Python 端进行清洗和筛选
            meaningful_lines = []
            lines = full_text.split('\n')
            
            for line in lines:
                cleaned_line = line.strip()
                if len(cleaned_line) >= min_text_length:
                    meaningful_lines.append(cleaned_line)

            if not meaningful_lines:
                return {"visible_text": "No meaningful text found on the page with the current criteria."}

            final_text = "\n\n".join(meaningful_lines)

            # --- [核心改动] ---
            # 3. 创建目录并保存文件
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 根据页面标题生成一个安全的文件名
            page_title = tab.title or "untitled"
            safe_filename = "".join(c for c in page_title if c.isalnum() or c in (' ', '_')).rstrip()
            file_path = os.path.join(output_dir, f"{safe_filename[:50]}.txt") # 限制文件名长度

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(final_text)

            # 4. 在返回值中同时包含文本内容和文件路径
            return {
                "visible_text": final_text,
                "file_path": os.path.abspath(file_path) # 返回文件的绝对路径
            }

        except Exception as e:
            return {"error": f"Failed to get and save visible text: {e}"}

def main():
    # --- MCP Server Initialization ---
    mcp = FastMCP("DrissionPageMCP", log_level="ERROR", instructions=prompt)
    b = DrissionPageMCP()
    # --- 智能注册工具的循环 ---
    for name, method in inspect.getmembers(b, predicate=inspect.ismethod):
        if not name.startswith('_'):
            docstring = inspect.getdoc(method) or ""
            
            title = None
            description = docstring
            # print(description)
            lines = docstring.strip().split('\n')
            title_line = next((line for line in lines if line.lower().strip().startswith("title:")), None)
            
            if title_line:
                title = title_line[len("title:"):].strip()
                # The rest of the docstring is the description
                desc_lines = [line for line in lines if line.strip() != title_line.strip()]
                description = '\n'.join(desc_lines).strip()
            
            # Prepare annotations dictionary
            tool_annotations = {}
            if title:
                tool_annotations['title'] = title

            description = description.replace('description: ','')
            # Call add_tool with the correct parameters
            mcp.add_tool(
                fn=method, 
                name=name, 
                description=description, 
            )
    print("DrissionPage MCP server (Ultimate Scanner) is running...")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()