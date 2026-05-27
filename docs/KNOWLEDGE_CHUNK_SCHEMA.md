# 知识块数据格式

你的切片系统应输出 UTF-8 JSONL：每行一个 JSON 对象，每个对象符合以下结构。

```json
{
  "chunk_id": "book_quant_003_012",
  "knowledge_domain": "trading_books",
  "document_title": "量化交易",
  "chapter": "第3章 趋势跟踪策略",
  "section": "移动平均线交叉系统",
  "page_start": 86,
  "page_end": 88,
  "content": "经授权可用于知识库的文本片段。",
  "keywords": ["趋势跟踪", "移动平均线", "交易信号"],
  "source_type": "book",
  "copyright_status": "authorized"
}
```

## 字段说明

| 字段 | 必须 | 说明 |
| --- | --- | --- |
| `chunk_id` | 是 | 全局唯一，重复导入同 ID 会覆盖对应向量 |
| `knowledge_domain` | 是 | 仅支持 `trading_books`、`product_manual`、`signal_rules` |
| `document_title` | 是 | 来源书名或系统文档名称 |
| `chapter` | 否 | 章节名称 |
| `section` | 否 | 小节名称 |
| `page_start` | 否 | 开始页码；能够定位时应填写 |
| `page_end` | 否 | 结束页码；能够定位时应填写 |
| `content` | 是 | 检索正文，至少 10 个字符 |
| `keywords` | 否 | 专业术语和检索增强标签 |
| `source_type` | 否 | 如 `book`、`manual`、`policy`、`demo` |
| `copyright_status` | 建议 | 如 `authorized`、`self_authored`、`internal` |

## 切片建议

- 一块只聚焦一个主题，例如 RSI 局限、ATR 止损或最大回撤。
- 尽量保留完整语义，不要从一句定义中间截断。
- 将页眉、页脚、广告、目录噪声和重复文本提前清理。
- 不要将未经授权的完整书籍内容提交到 GitHub 仓库。
