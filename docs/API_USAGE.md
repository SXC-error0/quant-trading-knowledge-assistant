# API 使用说明

服务启动后，交互式接口文档位于 `/docs`。

## 健康检查

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## 导入知识块

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/knowledge/import" \
  -H "Content-Type: application/json" \
  -d '{
    "chunks": [
      {
        "chunk_id": "manual_001",
        "knowledge_domain": "product_manual",
        "document_title": "产品帮助文档",
        "chapter": "问答助手",
        "content": "知识助手用于解释交易知识和系统规则，不直接执行交易。",
        "keywords": ["助手", "交易规则"],
        "source_type": "manual",
        "copyright_status": "self_authored"
      }
    ]
  }'
```

知识导入只依赖 Embedding 配置与 Qdrant；无需先配置聊天模型。

## 提问

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "均线金叉是否等同于必须买入？",
    "knowledge_domains": ["trading_books", "signal_rules"],
    "top_k": 5
  }'
```

## 响应字段

| 字段 | 说明 |
| --- | --- |
| `answer` | 大模型基于检索片段生成的回答 |
| `sources` | 参与生成的来源片段元数据 |
| `risk_notice` | 固定边界说明 |
| `boundary_triggered` | 是否触发即时决策或极端风险拦截 |

## 边界问题示例

对于以下问题，API 不依赖知识库与模型配置，也会优先返回边界提示：

```json
{
  "question": "BTCUSDT 现在能不能全仓开 50 倍做多？"
}
```

系统不会生成确定性的即时交易动作建议。
