# Quant Trading Knowledge Assistant

面向看盘工具的**量化交易专业知识问答服务**。本项目将你已有切片系统产出的书籍/文档知识块接入 RAG 检索链路，基于检索证据回答量化交易、短线策略、技术指标、回测评估、风险管理与系统使用问题。

> 本服务定位为“知识解释与系统帮助助手”，不是自动下单机器人，也不在缺少实时行情、策略信号和用户风险信息时给出确定性的买卖结论。

## 1. 项目目标

- 接入《量化交易》《短线交易秘诀》等**已取得合法使用权限**的资料切片。
- 分离三类知识域：交易书籍、产品使用手册、系统信号规则。
- 通过向量检索获取依据，生成带来源的专业回答。
- 对“现在全仓买入吗”“能否保证盈利”等越界请求进行风险边界拦截。
- 提供标准 HTTP API，便于后续接入现有看盘前端或智能体系统。

## 2. 当前 MVP 能力

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| JSONL 知识块导入 | 已实现 | 适配你的外部切片系统输出 |
| Qdrant 向量存储 | 已实现 | 保存知识块向量及来源元数据 |
| 专业问答接口 | 已实现 | 检索内容后调用 OpenAI-Compatible 大模型回答 |
| 来源返回 | 已实现 | 返回书名、章节、小节、页码和 chunk_id |
| 越界交易问题拦截 | 已实现 | 不对即时买卖、高风险仓位、收益保证给确定结论 |
| 混合检索 / 专用 Reranker | 规划中 | 当前为向量召回 + 轻量词项加权基线 |
| LoRA 微调 | 后置 | 仅在积累人工修正问答后考虑 |

## 3. 技术栈

- Python 3.11+
- FastAPI + Pydantic Settings
- Qdrant 向量数据库
- OpenAI-Compatible Embedding API
- OpenAI-Compatible Chat Completion API
- Docker Compose
- Pytest

模型接口采用 OpenAI-Compatible 协议，因此后续可根据实际供应商或自部署网关替换模型配置，而无需改动主要业务逻辑。

## 4. 工程结构

```text
quant-trading-knowledge-assistant/
├── app/
│   ├── api/                 # health、知识导入、问答接口
│   ├── core/                # 配置、提示词、回答安全边界
│   ├── models/              # 请求/响应与知识块数据模型
│   └── services/            # embedding、LLM、检索、入库、答案编排
├── data/
│   └── samples/             # 非版权样例知识块
├── docs/                    # 架构、知识格式、回答规范与路线图
├── scripts/                 # JSONL 导入脚本
├── tests/                   # 基础接口和安全边界测试
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## 5. 快速开始

### 5.1 克隆与安装

```bash
git clone https://github.com/SXC-error0/quant-trading-knowledge-assistant.git
cd quant-trading-knowledge-assistant
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 5.2 配置环境变量

```bash
cp .env.example .env
```

在 `.env` 中配置你的模型接口：

```env
LLM_BASE_URL=https://your-openai-compatible-provider.example/v1
LLM_API_KEY=replace_with_your_key
LLM_MODEL=your-chat-model

EMBEDDING_BASE_URL=https://your-openai-compatible-provider.example/v1
EMBEDDING_API_KEY=replace_with_your_key
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSIONS=1024
```

请确认 `EMBEDDING_DIMENSIONS` 与所选 embedding 模型实际输出维度一致；更换维度前应重建 Qdrant collection。

### 5.3 启动 Qdrant 与 API 服务

```bash
docker compose up -d qdrant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后可打开 Swagger 文档：`/docs`。

### 5.4 导入样例知识块

```bash
python scripts/import_chunks.py data/samples/knowledge_chunks.example.jsonl
```

### 5.5 发起专业问题

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "MACD 金叉是否可以单独作为立即买入依据？",
    "knowledge_domains": ["trading_books", "signal_rules"],
    "top_k": 5
  }'
```

响应包含 `answer`、`sources`、`risk_notice` 和是否触发边界规则的标记。

## 6. 接入你的切片系统

你的切片系统只需要输出 JSONL，每行一个知识块：

```json
{"chunk_id":"book_quant_003_012","knowledge_domain":"trading_books","document_title":"量化交易","chapter":"第3章 趋势跟踪策略","section":"移动平均线交叉系统","page_start":86,"page_end":88,"content":"这里填写经授权可用于知识库的文本片段。","keywords":["趋势跟踪","移动平均线","交易信号"],"source_type":"book","copyright_status":"authorized"}
```

导入方式：

```bash
python scripts/import_chunks.py /path/to/your_chunks.jsonl
```

详细字段规范参见 [`docs/KNOWLEDGE_CHUNK_SCHEMA.md`](docs/KNOWLEDGE_CHUNK_SCHEMA.md)。

## 7. 回答边界

本项目默认执行以下边界：

- 可以解释指标、策略、回测、仓位管理、止损概念与系统规则。
- 可以说明系统提醒的含义，但不将提醒表述为保证盈利的交易指令。
- 无实时行情、风险参数与策略状态时，不回答具体资产“现在买还是卖”。
- 不鼓励全仓、梭哈、高杠杆，不承诺收益或胜率。
- 不接收、不输出、不存储交易所 Secret/API Key。

详见 [`docs/ANSWER_POLICY.md`](docs/ANSWER_POLICY.md)。

## 8. 数据与版权说明

仓库不包含书籍正文或未经授权的电子资料。将书籍切片用于商业服务前，请确认你拥有相应的存储、处理与提供问答服务的使用权限。样例数据仅用于演示接口结构，不构成交易建议。

## 9. 下一阶段

1. 接入你的正式切片输出并创建知识域数据集。
2. 建立 100 条专业问答评测集，验证检索命中率、引用准确率和越界处理能力。
3. 增加 BM25/全文检索与专用 Reranker，形成混合检索链路。
4. 接入看盘工具前端，记录用户反馈与人工修正答案。
5. 数据积累充分后，再考虑 ShareGPT + LoRA 的回答行为微调。

## 10. 免责声明

本项目提供交易知识、策略原理与系统规则解释，不构成对任何数字资产的投资建议、收益保证或即时买卖指令。用户应独立评估风险并对自身交易行为负责。
