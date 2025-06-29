
from typing import Any,List, Dict


class DataPacketSummarizer:
    """
    一个用于生成 DataPacket 对象摘要的算法类 (递归升级版)。
    """
    def summarize_packet(self, packet) -> dict:
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
