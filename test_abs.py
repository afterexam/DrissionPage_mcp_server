import json
from typing import List, Dict, Any

# --- 模拟你提供的数据包对象结构 (用于独立测试) ---
class MockResponse:
    def __init__(self, body, status=200, mime_type="application/json"):
        self.body = body
        self.status = status
        self.mimeType = mime_type
        self.url = "https://api.bilibili.com/x/space/arc/search"

class MockDataPacket:
    def __init__(self, response_body):
        self.is_failed = False
        self.url = "https://api.bilibili.com/x/space/arc/search"
        self.method = "GET"
        self.resourceType = "fetch"
        self.response = MockResponse(body=response_body)
        self.fail_info = None

# --- 核心算法实现 (递归升级版) ---

class DataPacketSummarizer:
    """
    一个用于生成 DataPacket 对象摘要的算法类 (递归升级版)。
    """
    def summarize_packet(self, packet: Any) -> Dict[str, Any]:
        """对单个数据包生成摘要"""
        summary = {
            "url": packet.url,
            "method": packet.method,
            "status": packet.response.status if packet.response else "Failed",
            "content_summary": None,
            "error_info": packet.fail_info.errorText if packet.fail_info else None
        }

        if packet.response and packet.response.body:
            body = packet.response.body
            mime_type = packet.response.mimeType or ""

            if "json" in mime_type and isinstance(body, (dict, list)):
                # [核心] 调用新的递归摘要函数
                summary["content_summary"] = self._summarize_json_recursively(body)
            elif isinstance(body, bytes):
                summary["content_summary"] = f"Binary data, {len(body)} bytes"
            else:
                summary["content_summary"] = f"Text data, length {len(str(body))}, preview: '{str(body)[:100]}...'"
                
        return summary

    def _summarize_json_recursively(self, data: Any, max_depth: int = 4, current_depth: int = 0) -> Any:
        """
        递归地对JSON对象/列表进行摘要。
        """
        if current_depth >= max_depth:
            return f"Max depth ({max_depth}) reached..."

        if isinstance(data, list):
            if not data:
                return {"type": "list", "item_count": 0}
            
            # 对列表，只摘要第一个元素的结构
            first_item_summary = self._summarize_json_recursively(data[0], max_depth, current_depth + 1)
            return {
                "type": "list",
                "item_count": len(data),
                "first_item_schema": first_item_summary
            }
        
        if isinstance(data, dict):
            summary_dict = {}
            for key, value in data.items():
                # 对字典的每个值进行递归摘要
                summary_dict[key] = self._summarize_json_recursively(value, max_depth, current_depth + 1)
            return summary_dict
            
        # 对于其他基础类型 (str, int, bool, etc.)，直接返回值本身
        return data

    def summarize_packets(self, packets: List[Any]) -> List[Dict[str, Any]]:
        """对一整个数据包列表生成摘要"""
        return [self.summarize_packet(p) for p in packets]

# --- 测试脚本 ---
if __name__ == '__main__':
    # 你提供的 Bilibili API 响应体
    bilibili_response_body = {
        "code": 0, "message": "0", "ttl": 1,
        "data": {
            "list": {
                "tlist": {
                    "4": {"tid": 4, "count": 1, "name": "游戏"},
                    "5": {"tid": 5, "count": 2, "name": "娱乐"},
                    # ... more tlist items
                },
                "vlist": [
                    {"comment": 4136, "typeid": 201, "play": 1585119, "title": "【毕导】太阳究竟早上近还是中午近？...", "author": "毕导"},
                    {"comment": 2375, "typeid": 201, "play": 1802984, "title": "【毕导】你试过...用肛门呼吸吗？", "author": "毕导"},
                    # ... more vlist items
                ]
            },
            "page": {"pn": 1, "ps": 40, "count": 161}
        }
    }
    
    # 构造一个模拟的数据包
    mock_packet = MockDataPacket(response_body=bilibili_response_body)
    
    # 实例化并使用新的摘要算法
    summarizer = DataPacketSummarizer()
    summary = summarizer.summarize_packet(mock_packet)
    
    # 打印格式化的摘要结果
    print("--- 复杂数据包摘要结果 ---")
    print(json.dumps(summary, indent=2, ensure_ascii=False))