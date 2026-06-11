# 智能交易平台 RAG 知识助手优化升级方案

## 0. 文档说明

本文档用于指导 `quant-trading-knowledge-assistant` 的后续升级开发。

当前项目已经具备交易知识 RAG 问答服务的 MVP 骨架，包括 FastAPI、Qdrant、OpenAI-Compatible Embedding、OpenAI-Compatible Chat Completion、JSONL 知识块导入、来源返回、SSE 流式回答和基础交易风险边界拦截。

下一阶段的目标不是简单增加知识文档数量，而是将当前系统从“交易知识 RAG API Demo”升级为：

> 面向智能交易平台的专业知识中枢、信号解释助手、策略说明助手、风险教育助手和产品帮助助手。

---

## 1. 升级目标

### 1.1 产品目标

系统需要能够回答以下几类问题：

```text
1. 交易知识解释
   - 什么是 MACD？
   - 什么是 ATR 止损？
   - 夏普比率和最大回撤怎么看？

2. 策略原理解释
   - 趋势跟踪策略为什么在震荡行情容易亏损？
   - 网格策略适合什么行情？
   - 均值回归策略的主要风险是什么？

3. 系统信号解释
   - 这个买入信号是什么意思？
   - 为什么系统提示风险预警？
   - 当前策略触发了哪些条件？

4. 回测指标解释
   - 回测胜率高为什么实盘仍然可能亏损？
   - 最大回撤代表什么？
   - 盈亏比和胜率哪个更重要？

5. 风险管理教育
   - 为什么不能全仓？
   - 为什么不能只看一个指标交易？
   - 止损和仓位管理有什么关系？

6. 产品使用帮助
   - 如何创建策略？
   - 如何查看回测？
   - 信号提醒在哪里设置？
   - 订阅套餐功能有什么区别？
```

系统不应该回答以下问题：

```text
1. 现在 BTC 能不能买？
2. 马上做多还是做空？
3. 能不能全仓梭哈？
4. 这个信号能不能保证盈利？
5. 给我一个 100% 胜率策略。
6. 怎么绕过交易所风控？
7. 怎么刷成交量、对敲、操纵市场？
8. 帮我保存交易所 Secret Key。
```

### 1.2 工程目标

升级后的系统应具备：

```text
1. 更细的知识域划分。
2. 更懂交易语义的 KnowledgeChunk。
3. Dense + Keyword + RRF + Reranker 的高级检索链路。
4. 最低相关度阈值和拒答机制。
5. 平台上下文接入能力。
6. 更完整的交易风险边界。
7. 问答日志、用户反馈和评估闭环。
8. 可扩展的知识库管理能力。
9. 可接入智能交易平台前端的 API 结构。
10. 可持续演进到商业化 SaaS 或内部知识中枢。
```

---

## 2. 当前项目现状

### 2.1 当前已有能力

当前项目已经实现：

```text
1. JSONL 知识块导入。
2. KnowledgeChunk 数据模型。
3. Qdrant 向量存储。
4. OpenAI-Compatible Embedding。
5. OpenAI-Compatible LLM。
6. /api/v1/knowledge/import 导入接口。
7. /api/v1/chat/ask 普通问答接口。
8. /api/v1/chat/ask/stream 流式问答接口。
9. 基础来源返回。
10. 基础风险边界拦截。
11. signal_context 信号上下文支持。
12. FastAPI 服务生命周期依赖初始化。
```

当前服务初始化链路：

```text
FastAPI lifespan
  -> Settings
  -> EmbeddingService
  -> VectorStore
  -> LLMService
  -> RetrievalService
  -> IngestionService
  -> AnswerService
```

当前问答链路：

```text
用户问题
  -> safety.assess_question()
  -> RetrievalService.retrieve()
  -> build_grounded_prompt() / build_signal_prompt()
  -> LLMService.answer()
  -> AskResponse(answer, sources, risk_notice)
```

当前检索链路：

```text
用户问题
  -> 生成 query embedding
  -> Qdrant 向量召回候选
  -> 对召回候选临时构建 BM25
  -> 向量分数 0.7 + BM25 分数 0.3
  -> 返回 top_k
```

### 2.2 当前主要问题

```text
1. 知识域过少
   当前只有 trading_books、product_manual、signal_rules，难以支撑复杂交易平台场景。

2. 知识块交易语义不足
   当前 chunk 主要描述来源信息，缺少 symbol、timeframe、strategy_type、indicator_names、market_regime 等交易语义字段。

3. 检索链路仍偏初级
   当前 BM25 只在向量召回候选中做加权，不能从全库独立召回关键词强相关内容。

4. 没有真正的 Reranker
   当前没有 cross-encoder 或专用 rerank 模型，交易知识相似问题容易排序错误。

5. 缺少最低相关度阈值
   只要 Qdrant 返回结果，系统就可能回答，容易产生“弱相关硬答”。

6. 缺少知识库版本管理
   无法区分文档版本、策略版本、信号规则版本。

7. 缺少权限控制
   交易平台未来可能有免费用户、会员用户、内部运营、管理员、策略作者等不同角色。

8. 缺少问答日志与反馈闭环
   无法持续优化知识库、Prompt、检索参数和回答质量。

9. 缺少评测体系
   没有标准问题集，无法量化 RAG 效果。

10. 缺少平台上下文
   当前 signal_context 只是初步支持，还没有完整接入用户所在页面、交易对、周期、策略、指标、订阅等级、风险偏好等上下文。
```

---

## 3. 目标架构设计

### 3.1 第一阶段推荐架构

第一阶段继续保留单体 FastAPI 服务，但将模块拆得更清晰。

```text
quant-trading-knowledge-assistant/
├── app/
│   ├── api/
│   │   ├── health.py
│   │   ├── chat.py
│   │   ├── knowledge.py
│   │   ├── documents.py
│   │   ├── feedback.py
│   │   └── evaluations.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── prompts.py
│   │   ├── safety.py
│   │   ├── constants.py
│   │   ├── logging.py
│   │   └── errors.py
│   │
│   ├── models/
│   │   ├── chat.py
│   │   ├── knowledge.py
│   │   ├── document.py
│   │   ├── signal.py
│   │   ├── platform_context.py
│   │   ├── user_context.py
│   │   ├── feedback.py
│   │   └── evaluation.py
│   │
│   ├── services/
│   │   ├── answer_service.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   ├── vector_store.py
│   │   ├── keyword_store.py
│   │   ├── retrieval_service.py
│   │   ├── rerank_service.py
│   │   ├── ingestion_service.py
│   │   ├── document_parser.py
│   │   ├── safety_service.py
│   │   ├── feedback_service.py
│   │   └── evaluation_service.py
│   │
│   ├── repositories/
│   │   ├── chat_repository.py
│   │   ├── document_repository.py
│   │   ├── knowledge_repository.py
│   │   ├── feedback_repository.py
│   │   └── evaluation_repository.py
│   │
│   └── workers/
│       ├── parse_document_worker.py
│       ├── import_chunks_worker.py
│       └── reindex_worker.py
│
├── data/
│   ├── samples/
│   └── eval_sets/
│
├── docs/
│   ├── KNOWLEDGE_CHUNK_SCHEMA.md
│   ├── ANSWER_POLICY.md
│   ├── UPGRADE_PLAN.md
│   ├── EVALUATION_GUIDE.md
│   └── API_DESIGN.md
│
├── scripts/
│   ├── import_chunks.py
│   ├── build_eval_set.py
│   └── run_evaluation.py
│
├── tests/
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

### 3.2 第二阶段服务化架构

当知识量、用户量和平台功能变多后，再拆分为多个服务。

```text
chat-web / trading-platform-front
          |
          v
API Gateway / Nginx
          |
          v
quant-rag-api
          |
          |---- document-service
          |---- ingestion-worker
          |---- retrieval-service
          |---- rerank-service
          |---- llm-service
          |---- feedback-service
          |---- evaluation-service
          |
          |---- PostgreSQL
          |---- Qdrant
          |---- Elasticsearch / OpenSearch
          |---- Redis
          |---- MinIO
```

第一阶段不建议过早微服务化，应优先保证 RAG 效果和产品闭环。

---

## 4. 知识域升级方案

### 4.1 当前知识域

当前项目中：

```python
KnowledgeDomain = Literal["trading_books", "product_manual", "signal_rules"]
```

建议升级为：

```python
KnowledgeDomain = Literal[
    "trading_books",
    "indicator_docs",
    "strategy_docs",
    "risk_management",
    "backtest_docs",
    "product_manual",
    "signal_rules",
    "exchange_rules",
    "case_studies",
    "faq",
    "compliance_policy",
]
```

### 4.2 知识域说明

| 知识域 | 用途 | 示例问题 |
|---|---|---|
| trading_books | 交易书籍知识 | 《短线交易秘诀》中如何理解波动？ |
| indicator_docs | 技术指标知识 | MACD 金叉是否能单独作为买入依据？ |
| strategy_docs | 策略原理知识 | 趋势跟踪策略适合什么行情？ |
| risk_management | 风险管理知识 | 为什么不能全仓？ |
| backtest_docs | 回测评估知识 | 最大回撤怎么看？ |
| product_manual | 产品使用手册 | 如何创建策略？ |
| signal_rules | 系统信号规则 | 这个买入信号为什么触发？ |
| exchange_rules | 交易所规则 | 合约资金费率是什么？ |
| case_studies | 历史案例复盘 | 某次极端行情为什么策略失效？ |
| faq | 高频问答 | 为什么我的信号延迟了？ |
| compliance_policy | 合规与免责声明 | 平台是否提供投资建议？ |

### 4.3 知识域选择策略

```text
知识解释类问题：
  indicator_docs + trading_books + risk_management

策略解释类问题：
  strategy_docs + trading_books + backtest_docs + risk_management

信号解释类问题：
  signal_rules + strategy_docs + indicator_docs + risk_management

产品使用类问题：
  product_manual + faq

合规风险类问题：
  compliance_policy + risk_management

交易所规则类问题：
  exchange_rules + faq
```

建议新增 `IntentRouterService`：

```python
class IntentRouterService:
    async def route(self, question: str, platform_context: PlatformContext | None):
        return RoutedQuery(
            intent="signal_interpretation",
            preferred_domains=["signal_rules", "strategy_docs", "indicator_docs", "risk_management"],
            query_rewrite="解释 BTCUSDT 15m MACD 买入信号的触发条件、适用场景和风险",
            safety_level="signal_explanation",
        )
```

---

## 5. 知识块 Schema 升级方案

### 5.1 当前 KnowledgeChunk

当前字段：

```python
class KnowledgeChunk(BaseModel):
    chunk_id: str
    knowledge_domain: KnowledgeDomain
    document_title: str
    chapter: str | None
    section: str | None
    page_start: int | None
    page_end: int | None
    content: str
    keywords: list[str]
    source_type: str
    copyright_status: str | None
```

该结构适合普通文档知识，但对交易平台语义不够。

### 5.2 升级后的 KnowledgeChunk

建议升级为：

```python
from typing import Literal
from pydantic import BaseModel, Field

KnowledgeDomain = Literal[
    "trading_books",
    "indicator_docs",
    "strategy_docs",
    "risk_management",
    "backtest_docs",
    "product_manual",
    "signal_rules",
    "exchange_rules",
    "case_studies",
    "faq",
    "compliance_policy",
]

class KnowledgeChunk(BaseModel):
    chunk_id: str = Field(min_length=1, max_length=200)

    knowledge_base_id: str | None = None
    knowledge_domain: KnowledgeDomain

    document_id: str | None = None
    document_title: str = Field(min_length=1, max_length=300)
    document_version: str | None = None

    chapter: str | None = Field(default=None, max_length=300)
    section: str | None = Field(default=None, max_length=300)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)

    content: str = Field(min_length=10)
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)

    source_type: str = Field(default="document", max_length=50)
    copyright_status: str | None = Field(default=None, max_length=100)

    asset_classes: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    timeframes: list[str] = Field(default_factory=list)
    indicator_names: list[str] = Field(default_factory=list)
    strategy_types: list[str] = Field(default_factory=list)
    market_regimes: list[str] = Field(default_factory=list)

    risk_level: Literal["low", "medium", "high", "extreme"] | None = None
    answer_intents: list[str] = Field(default_factory=list)

    permission_tags: list[str] = Field(default_factory=list)
    status: Literal["active", "disabled", "archived"] = "active"

    created_at: str | None = None
    updated_at: str | None = None
```

### 5.3 交易语义字段说明

| 字段 | 说明 | 示例 |
|---|---|---|
| asset_classes | 资产类别 | crypto, stock, futures |
| symbols | 适用交易对 | BTCUSDT, ETHUSDT |
| timeframes | 适用周期 | 1m, 5m, 15m, 1h, 4h, 1d |
| indicator_names | 指标名 | MACD, RSI, EMA, ATR |
| strategy_types | 策略类型 | trend_following, mean_reversion, grid |
| market_regimes | 行情状态 | trend, range, high_volatility |
| risk_level | 风险等级 | low, medium, high, extreme |
| answer_intents | 适合回答的问题类型 | indicator_explanation, signal_interpretation |
| permission_tags | 权限标签 | free, pro, internal, admin |
| status | 启用状态 | active, disabled, archived |

### 5.4 JSONL 示例

```json
{"chunk_id":"indicator_macd_001","knowledge_domain":"indicator_docs","document_title":"技术指标知识库","chapter":"MACD","section":"MACD 金叉的意义与局限","content":"MACD 金叉通常表示短期动能改善，但不能单独作为立即买入依据，需要结合趋势、成交量、支撑阻力和风险控制共同判断。","summary":"MACD 金叉代表动能改善，但不能单独作为买入依据。","keywords":["MACD","金叉","动能","趋势","假信号"],"source_type":"internal_doc","copyright_status":"self_authored","asset_classes":["crypto"],"timeframes":["15m","1h","4h","1d"],"indicator_names":["MACD"],"strategy_types":["momentum","trend_following"],"market_regimes":["trend","range"],"risk_level":"medium","answer_intents":["indicator_explanation","signal_interpretation"],"permission_tags":["free","pro"],"status":"active"}
```

---

## 6. 文档导入与切片升级方案

### 6.1 当前导入方式

当前系统支持外部切片系统输出 JSONL，然后通过脚本或接口导入：

```bash
python scripts/import_chunks.py data/samples/knowledge_chunks.example.jsonl
```

```http
POST /api/v1/knowledge/import
```

该方式适合内部调试，但不适合产品化管理。

### 6.2 推荐新增文档处理链路

```text
文件上传
  -> 保存原始文件
  -> 创建 document 记录
  -> 异步解析文本
  -> 清洗噪声
  -> 语义切片
  -> 生成 chunk
  -> 生成 embedding
  -> 写入 Qdrant
  -> 写入 PostgreSQL 元数据
  -> 标记导入完成
```

### 6.3 支持文件类型

第一阶段支持：

```text
1. Markdown
2. TXT
3. JSONL
4. PDF
5. Word docx
6. CSV
7. Excel
```

第二阶段支持：

```text
1. 网页 URL 抓取
2. Notion / 飞书 / 语雀文档同步
3. 数据库表同步
4. 策略规则自动导入
5. 产品帮助中心自动同步
```

### 6.4 切片策略

| 类型 | 切片方式 |
|---|---|
| 交易书籍 | 按章节、小节、语义段落切片 |
| 指标说明 | 一个指标概念一个 chunk |
| 策略说明 | 按策略原理、适用行情、风险、参数解释切片 |
| 信号规则 | 一个信号规则一个 chunk |
| 产品手册 | 一个页面功能或操作流程一个 chunk |
| FAQ | 一个问答一个 chunk |
| 回测说明 | 一个指标或一个分析维度一个 chunk |
| 交易所规则 | 按规则条款切片 |
| 案例复盘 | 按背景、过程、结果、教训切片 |

### 6.5 切片原则

```text
1. 一个 chunk 只表达一个核心主题。
2. chunk 内容必须语义完整。
3. 不要从定义、公式、步骤中间截断。
4. 保留标题层级。
5. 保留来源信息。
6. 保留交易语义标签。
7. 删除页眉、页脚、目录、广告、重复免责声明。
8. 对长文档保留 section summary。
9. 对 FAQ 保持问题和答案在同一个 chunk。
10. 对策略规则保持触发条件和风险说明在同一个 chunk。
```

---

## 7. 检索链路升级方案

### 7.1 当前检索链路问题

当前链路：

```text
Qdrant 向量召回 top N
  -> 对候选构建 BM25
  -> 向量分数和 BM25 分数加权
```

问题：

```text
1. BM25 只能在向量候选里起作用，不能全库召回。
2. 中文分词较弱。
3. 没有独立 keyword index。
4. 没有真正 reranker。
5. 没有 query rewrite。
6. 没有最低相关度阈值。
7. 没有来源覆盖度检查。
8. 没有多阶段检索。
```

### 7.2 目标检索链路

升级为：

```text
用户问题
  -> 意图识别
  -> Query Rewrite
  -> 权限与平台上下文过滤
  -> Dense Vector Search top 50
  -> Sparse / BM25 Search top 50
  -> 合并去重
  -> RRF 融合
  -> Reranker 重排序
  -> 相关度阈值过滤
  -> 来源覆盖检查
  -> top 5~8 进入 Prompt
```

### 7.3 新增 KeywordStore

新增 `app/services/keyword_store.py`。

可选方案：

```text
方案 A：PostgreSQL Full Text Search
适合 MVP，部署简单。

方案 B：Elasticsearch / OpenSearch
适合生产，中文分词、复杂过滤、权重控制更强。

方案 C：Qdrant Sparse Vector
适合希望统一在 Qdrant 内做 dense + sparse 混合检索。
```

推荐第一阶段：

```text
Qdrant dense vector
+
PostgreSQL / Elasticsearch BM25
+
Reranker
```

### 7.4 RetrievalService 升级结构

```python
class RetrievalService:
    def __init__(
        self,
        settings: Settings,
        embeddings: EmbeddingService,
        vector_store: VectorStore,
        keyword_store: KeywordStore,
        reranker: RerankService,
    ):
        ...

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        routed = await self.intent_router.route(request)
        rewritten_queries = await self.query_rewriter.rewrite(
            request.question,
            request.platform_context,
        )

        dense_candidates = await self.vector_store.search(
            query=rewritten_queries.semantic_query,
            filters=routed.filters,
            limit=settings.dense_candidate_k,
        )

        keyword_candidates = await self.keyword_store.search(
            query=rewritten_queries.keyword_query,
            filters=routed.filters,
            limit=settings.keyword_candidate_k,
        )

        fused_candidates = self.fuse_by_rrf(dense_candidates, keyword_candidates)

        reranked = await self.reranker.rerank(
            question=request.question,
            candidates=fused_candidates,
            top_n=settings.rerank_top_n,
        )

        filtered = self.filter_by_score(reranked)
        coverage = self.check_source_coverage(request.question, filtered)

        return RetrievalResult(
            chunks=filtered[:request.top_k],
            coverage=coverage,
            query_info=..., 
        )
```

### 7.5 RRF 融合策略

RRF 即 Reciprocal Rank Fusion，用于融合多个检索结果排名。

```python
def reciprocal_rank_fusion(result_sets: list[list[Candidate]], k: int = 60):
    scores = {}

    for results in result_sets:
        for rank, item in enumerate(results):
            chunk_id = item.chunk.chunk_id
            scores.setdefault(chunk_id, 0)
            scores[chunk_id] += 1 / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

推荐参数：

```text
dense_top_k = 50
keyword_top_k = 50
rrf_k = 60
rerank_top_n = 20
final_top_k = 5~8
```

---

## 8. Reranker 升级方案

### 8.1 为什么必须加 Reranker

交易知识问题高度相似，例如：

```text
MACD 金叉能不能买？
MACD 金叉是什么意思？
MACD 金叉为什么会失败？
MACD 金叉和均线金叉区别？
MACD 金叉在震荡行情有什么风险？
```

向量检索容易召回一堆 MACD 片段，但不一定把真正匹配的问题排在前面。

Reranker 的作用：

```text
第一阶段：快速召回大量候选。
第二阶段：用更精细的模型判断“问题-片段”相关性。
```

### 8.2 推荐 RerankService

新增：

```text
app/services/rerank_service.py
```

接口设计：

```python
class RerankService:
    async def rerank(
        self,
        question: str,
        candidates: list[RetrievedChunk],
        top_n: int,
    ) -> list[RetrievedChunk]:
        ...
```

### 8.3 Reranker 选型

第一阶段推荐：

```text
本地模型：
- bge-reranker-v2-m3
- bge-reranker-large
- gte-rerank

API 模型：
- Qwen Reranker
- Cohere Rerank
- 其他 OpenAI-Compatible rerank 服务
```

中文交易知识场景优先考虑：

```text
bge-reranker-v2-m3
```

### 8.4 Rerank 输入与输出

输入：

```python
pairs = [
    {
        "query": question,
        "document": f"{chunk.title}\n{chunk.content}",
    }
    for chunk in candidates
]
```

输出：

```python
[
    {
        "chunk_id": "indicator_macd_001",
        "rerank_score": 0.87,
    }
]
```

最终分数建议：

```text
final_score = 0.2 * fused_score + 0.8 * rerank_score
```

---

## 9. 相关度阈值与拒答机制

### 9.1 当前问题

当前系统只在无检索结果时拒答。

但实际场景中，向量库几乎总能返回一些结果，即使它们弱相关。

因此需要增加：

```text
1. 最低相关度阈值。
2. 来源覆盖度检查。
3. 多来源冲突检查。
4. 问题类型与知识域匹配检查。
```

### 9.2 推荐拒答条件

```text
1. 没有检索结果。
2. top1 rerank_score < min_rerank_score。
3. top1 内容无法覆盖问题核心实体。
4. 问题涉及具体系统功能，但未检索到 product_manual 或 faq。
5. 问题涉及系统信号，但未检索到 signal_rules。
6. 问题涉及具体资产即时买卖，且没有 signal_context。
7. 问题要求全仓、高杠杆、保证收益。
8. 问题涉及违法违规交易行为。
```

### 9.3 配置项

在 `Settings` 中增加：

```python
dense_candidate_k: int = 50
keyword_candidate_k: int = 50
rerank_top_n: int = 20
retrieval_final_top_k: int = 6

min_vector_score: float = 0.25
min_rerank_score: float = 0.45
min_source_count: int = 1

enable_query_rewrite: bool = True
enable_rerank: bool = True
enable_keyword_search: bool = True
enable_source_coverage_check: bool = True
```

### 9.4 拒答模板

```text
## 结论
当前知识库未检索到足够可靠的依据，无法直接回答该问题。

## 原因
- 现有资料没有覆盖问题中的核心概念、系统功能或策略规则。
- 为避免误导，系统不会在证据不足时编造答案。

## 建议
你可以补充以下资料后重新提问：
- 对应策略规则
- 指标说明文档
- 系统使用手册
- 风险管理说明
- 回测报告说明

## 风险提示
本回答仅用于交易知识和系统规则解释，不构成投资建议、收益承诺或即时买卖指令。
```

---

## 10. 平台上下文升级方案

### 10.1 当前 AskRequest

当前 AskRequest 主要包含：

```text
question
knowledge_domains
top_k
signal_context
history
```

建议升级为：

```python
class UserContext(BaseModel):
    user_id: str | None = None
    role: str | None = None
    subscription_plan: str | None = None
    risk_profile: str | None = None
    locale: str | None = "zh-CN"


class PlatformContext(BaseModel):
    page: str | None = None
    symbol: str | None = None
    asset_class: str | None = None
    exchange: str | None = None
    timeframe: str | None = None
    strategy_id: str | None = None
    strategy_name: str | None = None
    indicators: list[str] = []
    market_regime: str | None = None


class AskRequest(BaseModel):
    question: str
    knowledge_domains: list[KnowledgeDomain] | None = None
    top_k: int = 6

    user_context: UserContext | None = None
    platform_context: PlatformContext | None = None
    signal_context: SignalContext | None = None

    history: list[ConversationTurn] = []
```

### 10.2 平台上下文使用方式

| 上下文字段 | 用途 |
|---|---|
| page | 判断用户是在图表页、回测页、策略页还是帮助页 |
| symbol | 识别当前交易对 |
| asset_class | 过滤 crypto、stock、futures 等知识 |
| exchange | 检索交易所规则 |
| timeframe | 检索适用周期相关知识 |
| strategy_id | 检索具体策略规则 |
| indicators | 检索相关指标说明 |
| market_regime | 匹配趋势、震荡、高波动等行情知识 |
| subscription_plan | 控制可访问知识范围 |
| risk_profile | 调整风险提示强度 |

### 10.3 示例请求

```json
{
  "question": "这个信号可靠吗？",
  "top_k": 6,
  "user_context": {
    "user_id": "u_10001",
    "role": "normal_user",
    "subscription_plan": "pro",
    "risk_profile": "medium"
  },
  "platform_context": {
    "page": "chart",
    "symbol": "BTCUSDT",
    "asset_class": "crypto",
    "exchange": "binance",
    "timeframe": "15m",
    "strategy_id": "macd_trend_v1",
    "strategy_name": "MACD 趋势策略",
    "indicators": ["MACD", "EMA", "RSI"],
    "market_regime": "high_volatility"
  },
  "signal_context": {
    "signal_type": "buy",
    "asset": "BTCUSDT",
    "strategy_name": "MACD 趋势策略",
    "timeframe": "15m",
    "conditions_met": [
      "MACD DIF 上穿 DEA",
      "价格站上 EMA20",
      "成交量高于过去 20 根均值"
    ],
    "triggered_at": "2026-06-11T10:30:00Z"
  }
}
```

---

## 11. Prompt 升级方案

### 11.1 Prompt 分类

建议将当前 `prompts.py` 拆分为多个模板：

```text
SYSTEM_PROMPT_BASE
KNOWLEDGE_QA_PROMPT
SIGNAL_EXPLANATION_PROMPT
STRATEGY_EXPLANATION_PROMPT
PRODUCT_HELP_PROMPT
RISK_EDUCATION_PROMPT
NO_EVIDENCE_PROMPT
```

### 11.2 基础系统 Prompt

```text
你是智能交易平台中的“专业交易知识助手”。

你的职责：
1. 基于检索到的知识片段，解释交易知识、策略原理、技术指标、回测评估、风险管理、系统信号和产品功能。
2. 不能脱离参考资料编造结论。
3. 不能将回答表述为确定性的买卖指令。
4. 不能承诺收益、保证胜率或暗示能够预测未来价格。
5. 不能鼓励全仓、重仓、高杠杆或报复性加仓。
6. 不能存储、索要或回显用户交易所 API Secret。
7. 对资料不足的问题，应明确说明“当前知识库依据不足”。
8. 回答应清晰、分点、可执行，但必须保持非投资建议边界。
```

### 11.3 信号解释 Prompt

```text
你正在解释智能交易平台中已经产生的系统信号。

请基于【系统信号上下文】和【参考资料】回答用户问题。

回答必须包含：
1. 信号含义
2. 触发条件解释
3. 该信号不代表什么
4. 适用行情
5. 可能失效的场景
6. 风险控制建议
7. 参考来源
8. 风险提示

限制：
- 可以解释信号，但不能说“应该立即买入/卖出”。
- 可以解释触发条件，但不能保证盈利。
- 可以说明风险点，但不能给出确定仓位。
```

### 11.4 策略解释 Prompt

```text
你正在解释交易策略的原理、适用条件和风险。

回答必须包含：
1. 策略核心思想
2. 适用行情
3. 不适用行情
4. 关键参数
5. 常见误区
6. 风险控制
7. 与平台功能的关系
8. 参考来源
```

### 11.5 产品帮助 Prompt

```text
你正在回答智能交易平台的产品使用问题。

回答必须：
1. 优先基于产品手册、FAQ、系统规则回答。
2. 给出清晰步骤。
3. 不要混入无关交易理论。
4. 如果资料没有覆盖该功能，应说明当前帮助文档不足。
```

---

## 12. 安全边界升级方案

### 12.1 当前安全边界

当前系统已经识别：

```text
1. 直接即时买卖决策。
2. 极端风险操作。
3. 收益保证。
4. 高杠杆。
5. 全仓梭哈。
```

需要扩展到智能交易平台完整风控场景。

### 12.2 新增风险类型

```python
class RiskCategory(str, Enum):
    SAFE_KNOWLEDGE = "safe_knowledge"
    SIGNAL_EXPLANATION = "signal_explanation"
    DIRECT_TRADING_DECISION = "direct_trading_decision"
    EXTREME_LEVERAGE = "extreme_leverage"
    PROFIT_GUARANTEE = "profit_guarantee"
    API_SECRET_REQUEST = "api_secret_request"
    MARKET_MANIPULATION = "market_manipulation"
    ILLEGAL_ACTIVITY = "illegal_activity"
    INSUFFICIENT_CONTEXT = "insufficient_context"
```

### 12.3 增加拦截关键词

```text
市场操纵类：
- 刷量
- 对敲
- 拉盘
- 砸盘
- 操纵市场
- 绕过风控
- 多账户对倒
- 虚假成交
- 洗盘控盘

账户安全类：
- API Secret
- 私钥
- 助记词
- 交易所密钥
- 帮我保存 secret
- 把密钥发给你
```

### 12.4 风险处理策略

| 风险类型 | 处理方式 |
|---|---|
| safe_knowledge | 正常回答 |
| signal_explanation | 可以解释，不给确定买卖动作 |
| direct_trading_decision | 拒绝给出即时买卖结论，引导解释指标/策略 |
| extreme_leverage | 拒绝鼓励高风险行为，强调风险 |
| profit_guarantee | 明确不能保证收益 |
| api_secret_request | 拒绝接收或保存 Secret |
| market_manipulation | 拒绝协助违规交易 |
| insufficient_context | 要求补充系统信号、策略规则或资料 |

---

## 13. 数据存储升级方案

### 13.1 当前存储

当前主要使用：

```text
Qdrant 保存向量和 payload
```

后续需要增加 PostgreSQL 管理结构化元数据。

### 13.2 推荐数据库表

#### knowledge_bases

```sql
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    owner_id VARCHAR(100),
    visibility VARCHAR(50) DEFAULT 'private',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### documents

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    knowledge_base_id UUID REFERENCES knowledge_bases(id),
    title VARCHAR(300) NOT NULL,
    file_name VARCHAR(300),
    file_type VARCHAR(50),
    file_url TEXT,
    source_type VARCHAR(50),
    version VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    parse_status VARCHAR(50) DEFAULT 'pending',
    chunk_count INT DEFAULT 0,
    uploaded_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### document_chunks

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    chunk_id VARCHAR(200) UNIQUE NOT NULL,
    document_id UUID REFERENCES documents(id),
    knowledge_base_id UUID REFERENCES knowledge_bases(id),
    knowledge_domain VARCHAR(100),
    title VARCHAR(300),
    content TEXT NOT NULL,
    summary TEXT,
    metadata JSONB,
    qdrant_point_id VARCHAR(200),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### chat_sessions

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(100),
    title VARCHAR(300),
    source_page VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### chat_messages

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id),
    role VARCHAR(50),
    content TEXT,
    answer TEXT,
    sources JSONB,
    risk_category VARCHAR(100),
    boundary_triggered BOOLEAN DEFAULT FALSE,
    model_name VARCHAR(100),
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### answer_feedback

```sql
CREATE TABLE answer_feedback (
    id UUID PRIMARY KEY,
    message_id UUID REFERENCES chat_messages(id),
    user_id VARCHAR(100),
    rating INT,
    feedback_type VARCHAR(100),
    comment TEXT,
    corrected_answer TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### evaluation_cases

```sql
CREATE TABLE evaluation_cases (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    expected_answer TEXT,
    expected_sources JSONB,
    expected_domains JSONB,
    case_type VARCHAR(100),
    difficulty VARCHAR(50),
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 14. API 升级方案

### 14.1 保留现有接口

```text
GET  /api/v1/health
POST /api/v1/knowledge/import
POST /api/v1/chat/ask
POST /api/v1/chat/ask/stream
```

### 14.2 新增知识库接口

```text
POST   /api/v1/knowledge-bases
GET    /api/v1/knowledge-bases
GET    /api/v1/knowledge-bases/{id}
PUT    /api/v1/knowledge-bases/{id}
DELETE /api/v1/knowledge-bases/{id}
```

### 14.3 新增文档接口

```text
POST   /api/v1/documents/upload
GET    /api/v1/documents
GET    /api/v1/documents/{id}
DELETE /api/v1/documents/{id}
POST   /api/v1/documents/{id}/parse
POST   /api/v1/documents/{id}/reindex
```

### 14.4 新增 Chunk 管理接口

```text
GET    /api/v1/chunks
GET    /api/v1/chunks/{chunk_id}
PUT    /api/v1/chunks/{chunk_id}
DELETE /api/v1/chunks/{chunk_id}
```

### 14.5 新增反馈接口

```text
POST /api/v1/feedback
GET  /api/v1/feedback/stats
GET  /api/v1/feedback/bad-cases
```

### 14.6 新增评估接口

```text
POST /api/v1/evaluations/run
GET  /api/v1/evaluations/{evaluation_id}
GET  /api/v1/evaluations/latest
```

---

## 15. 问答返回结构升级方案

### 15.1 当前返回结构

当前 AskResponse：

```python
class AskResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    risk_notice: str
    boundary_triggered: bool = False
```

### 15.2 推荐升级结构

```python
class AskResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    risk_notice: str

    boundary_triggered: bool = False
    risk_category: str | None = None

    intent: str | None = None
    confidence: float | None = None

    retrieval_debug: RetrievalDebugInfo | None = None

    follow_up_questions: list[str] = []
    missing_context: list[str] = []

    session_id: str | None = None
    message_id: str | None = None
```

### 15.3 SourceReference 升级

```python
class SourceReference(BaseModel):
    chunk_id: str
    document_id: str | None = None
    knowledge_base_id: str | None = None
    knowledge_domain: KnowledgeDomain

    document_title: str
    chapter: str | None = None
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None

    score: float | None = None
    vector_score: float | None = None
    keyword_score: float | None = None
    rerank_score: float | None = None

    quote: str | None = None
```

---

## 16. 评估体系建设

### 16.1 为什么必须做评估

RAG 系统不能只靠主观感觉判断效果。

必须建立评测集，持续验证：

```text
1. 检索有没有找到正确资料。
2. 正确资料是否排在前面。
3. 回答是否忠实于资料。
4. 引用来源是否真的支撑答案。
5. 没有资料时是否拒答。
6. 风险边界是否正确触发。
7. 响应速度是否达标。
```

### 16.2 评估集结构

建议准备 `data/eval_sets/trading_rag_eval.jsonl`。

每行：

```json
{
  "case_id": "eval_001",
  "question": "MACD 金叉是否可以单独作为立即买入依据？",
  "expected_domains": ["indicator_docs", "risk_management"],
  "expected_source_keywords": ["MACD", "金叉", "不能单独", "风险"],
  "expected_answer_points": [
    "MACD 金叉代表动能改善",
    "不能单独作为立即买入依据",
    "需要结合趋势、成交量、风险控制"
  ],
  "should_refuse": false,
  "risk_category": "safe_knowledge",
  "difficulty": "easy",
  "tags": ["MACD", "indicator", "risk"]
}
```

### 16.3 初始评估集分类

至少准备 100 条：

```text
1. 指标解释类：20 条
2. 策略解释类：20 条
3. 风险管理类：20 条
4. 回测评估类：15 条
5. 系统信号解释类：15 条
6. 产品帮助类：10 条
7. 越界交易问题：20 条
```

### 16.4 评估指标

| 指标 | 说明 |
|---|---|
| retrieval_hit_rate | 正确来源是否被召回 |
| top1_accuracy | 正确来源是否排第一 |
| top_k_accuracy | 正确来源是否在前 K |
| citation_accuracy | 引用是否能支撑答案 |
| answer_faithfulness | 回答是否忠实资料 |
| refusal_accuracy | 该拒答时是否拒答 |
| boundary_accuracy | 风险边界触发是否正确 |
| latency_p95 | P95 响应时间 |
| cost_per_query | 单次问答成本 |

### 16.5 新增脚本

```text
scripts/run_evaluation.py
scripts/build_eval_set.py
scripts/export_bad_cases.py
```

运行方式：

```bash
python scripts/run_evaluation.py \
  --eval-file data/eval_sets/trading_rag_eval.jsonl \
  --output reports/eval_result_2026_06_11.json
```

---

## 17. 日志与反馈闭环

### 17.1 每次问答必须记录

```text
1. 用户问题
2. 用户上下文
3. 平台上下文
4. 意图识别结果
5. 风险分类
6. 是否触发边界
7. 检索 query
8. dense 检索结果
9. keyword 检索结果
10. rerank 后结果
11. 最终进入 Prompt 的 chunks
12. 模型名称
13. Prompt token
14. Completion token
15. 响应时间
16. 最终答案
17. 用户反馈
```

### 17.2 用户反馈类型

```text
1. 有帮助
2. 没帮助
3. 答非所问
4. 来源不对
5. 回答不完整
6. 风险提示太多
7. 需要人工修正
```

### 17.3 反馈使用方式

```text
低质量问题
  -> 加入 bad cases
  -> 检查检索是否命中
  -> 检查知识库是否缺失
  -> 检查 Prompt 是否不清晰
  -> 检查是否需要新增 FAQ
  -> 加入评测集
  -> 下次发版前验证
```

---

## 18. 权限与多租户设计

### 18.1 为什么需要权限

智能交易平台中，不同用户能看的内容可能不同：

```text
免费用户：
  - 基础指标解释
  - 基础风险教育
  - 产品基础帮助

Pro 用户：
  - 策略解释
  - 信号规则解释
  - 回测指标解释

内部运营：
  - 产品手册
  - 用户支持 FAQ

管理员：
  - 全部知识库
  - 内部规则
  - 合规文档

策略作者：
  - 自己策略的私有说明文档
```

### 18.2 权限过滤原则

权限必须在检索层做，不能只在前端做。

```text
用户提问
  -> 获取用户角色和订阅等级
  -> 转换成 permission_tags
  -> 检索时加 metadata filter
  -> 只返回用户有权限的 chunk
  -> LLM 只能看到允许访问的资料
```

### 18.3 示例

```python
permission_tags = ["free", "pro"]

filters = {
    "must": [
        {"key": "status", "match": "active"},
        {"key": "permission_tags", "match_any": permission_tags},
    ]
}
```

---

## 19. 配置项升级

建议 `.env.example` 增加：

```env
APP_NAME=Quant Trading Knowledge Assistant
APP_ENV=development
API_V1_PREFIX=/api/v1

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=quant_trading_knowledge

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/quant_rag
REDIS_URL=redis://localhost:6379/0

LLM_BASE_URL=https://your-openai-compatible-provider.example/v1
LLM_API_KEY=replace_with_your_key
LLM_MODEL=your-chat-model
LLM_TEMPERATURE=0.2

EMBEDDING_BASE_URL=https://your-openai-compatible-provider.example/v1
EMBEDDING_API_KEY=replace_with_your_key
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSIONS=1024

RERANK_BASE_URL=
RERANK_API_KEY=
RERANK_MODEL=bge-reranker-v2-m3
ENABLE_RERANK=true

ENABLE_KEYWORD_SEARCH=true
KEYWORD_BACKEND=postgres
DENSE_CANDIDATE_K=50
KEYWORD_CANDIDATE_K=50
RERANK_TOP_N=20
RETRIEVAL_FINAL_TOP_K=6

MIN_VECTOR_SCORE=0.25
MIN_RERANK_SCORE=0.45
MIN_SOURCE_COUNT=1

ENABLE_QUERY_REWRITE=true
ENABLE_SOURCE_COVERAGE_CHECK=true

INGESTION_BATCH_SIZE=50
MAX_UPLOAD_SIZE_MB=50

ENABLE_CHAT_LOG=true
ENABLE_FEEDBACK=true
ENABLE_EVALUATION=true
```

---

## 20. Docker Compose 升级方案

建议加入：

```text
1. api
2. qdrant
3. postgres
4. redis
5. minio
6. elasticsearch，可选
```

示例：

```yaml
services:
  api:
    build: .
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      - qdrant
      - postgres
      - redis

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: quant_rag
      POSTGRES_USER: quant
      POSTGRES_PASSWORD: quant_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio_password
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  qdrant_data:
  postgres_data:
  minio_data:
```

---

## 21. 开发迭代计划

### 21.1 V0.2：检索质量升级

目标：解决当前检索偏弱问题。

任务：

```text
1. 扩展 KnowledgeDomain。
2. 扩展 KnowledgeChunk 交易语义字段。
3. 新增 min_score 阈值。
4. 新增 RerankService。
5. 新增 KeywordStore。
6. 将检索链路改为 dense + keyword + RRF + rerank。
7. 增加 retrieval_debug 返回。
8. 增加 30 条基础评测集。
```

验收标准：

```text
1. MACD、RSI、ATR、均线、回撤等问题能稳定命中正确知识。
2. 没有资料的问题能拒答。
3. 越界买卖问题能拦截。
4. 检索结果能返回 vector_score、keyword_score、rerank_score。
```

### 21.2 V0.3：平台上下文升级

目标：让助手真正适配智能交易平台。

任务：

```text
1. 新增 UserContext。
2. 新增 PlatformContext。
3. AskRequest 支持 page、symbol、timeframe、strategy_id、indicators。
4. 检索时基于 platform_context 做 metadata filter。
5. 完善 signal_context 回答模板。
6. 增加信号解释专用 Prompt。
7. 增加策略解释专用 Prompt。
8. 增加产品帮助专用 Prompt。
```

验收标准：

```text
1. 用户在图表页问“这个信号什么意思”，系统能结合 signal_context 回答。
2. 用户在回测页问“最大回撤怎么看”，系统优先检索 backtest_docs。
3. 用户在产品设置页问“提醒怎么开”，系统优先检索 product_manual。
```

### 21.3 V0.4：知识库管理升级

目标：从 JSONL 导入升级为可管理知识库。

任务：

```text
1. 新增 PostgreSQL。
2. 新增 knowledge_bases 表。
3. 新增 documents 表。
4. 新增 document_chunks 表。
5. 新增文档上传接口。
6. 新增文档解析状态。
7. 新增 chunk 查询、更新、删除接口。
8. 新增文档 reindex 接口。
```

验收标准：

```text
1. 可以创建知识库。
2. 可以上传文档。
3. 可以查看解析状态。
4. 可以查看 chunk。
5. 可以禁用某个文档或 chunk。
6. 删除文档后，Qdrant 中对应向量也删除。
```

### 21.4 V0.5：日志、反馈与评估

目标：形成持续优化闭环。

任务：

```text
1. 新增 chat_sessions。
2. 新增 chat_messages。
3. 新增 answer_feedback。
4. 每次问答记录检索结果和模型调用信息。
5. 新增反馈接口。
6. 新增 evaluation_cases。
7. 新增 run_evaluation.py。
8. 建立 100 条评测集。
```

验收标准：

```text
1. 每次问答可追溯。
2. 可查看差评问题。
3. 可导出 bad cases。
4. 可运行离线评估。
5. 每次升级前能对比检索命中率和回答质量。
```

### 21.5 V0.6：权限与商业化支持

目标：支持平台用户权限和订阅套餐。

任务：

```text
1. KnowledgeChunk 增加 permission_tags。
2. UserContext 增加 subscription_plan。
3. 检索层增加权限过滤。
4. 文档管理支持权限配置。
5. API 增加鉴权中间件。
6. 支持不同套餐可访问不同知识域。
```

验收标准：

```text
1. 免费用户无法检索 Pro 专属策略规则。
2. 普通用户无法检索内部运营文档。
3. 管理员可以访问全部知识。
4. LLM 不会看到用户无权访问的 chunk。
```

---

## 22. 推荐优先级总表

| 优先级 | 模块 | 说明 |
|---|---|---|
| P0 | Reranker | 直接影响回答准确率 |
| P0 | 最低相关度阈值 | 防止弱相关硬答 |
| P0 | 知识域扩展 | 支撑交易平台复杂问题 |
| P0 | 知识块交易语义字段 | 支撑信号、策略、指标上下文 |
| P0 | 风险边界扩展 | 防止高风险/违规交易问题 |
| P1 | KeywordStore | 构建真正混合检索 |
| P1 | PlatformContext | 让助手接入看盘页面 |
| P1 | 问答日志 | 后续优化必需 |
| P1 | 用户反馈 | 形成 bad cases |
| P1 | 评估集 | 量化效果 |
| P2 | 文档上传解析 | 产品化知识库管理 |
| P2 | 权限系统 | 商业化必需 |
| P2 | 多租户 | SaaS 化时需要 |
| P3 | 知识图谱 | 策略/指标关系增强 |
| P3 | LoRA 微调 | 积累高质量修正问答后再做 |

---

## 23. 不建议现在做的事情

### 23.1 不建议马上做 LoRA 微调

原因：

```text
1. 当前还没有足够高质量问答数据。
2. RAG 检索质量还没优化。
3. 交易知识更新快，微调不如知识库更新灵活。
4. 微调不能解决引用来源问题。
5. 微调不能替代权限控制和风险边界。
```

建议：

```text
先做 RAG 闭环。
积累 500~2000 条人工修正问答。
再考虑 LoRA 微调回答风格和结构。
```

### 23.2 不建议直接接实时行情后给买卖建议

原因：

```text
1. 合规风险高。
2. 用户可能误解为投资建议。
3. 模型不适合作为即时交易决策源。
4. 缺少用户风险承受能力和完整账户信息。
```

推荐方式：

```text
可以解释信号。
可以解释策略条件。
可以说明风险点。
可以说明指标含义。
不能直接喊单。
```

### 23.3 不建议一开始做复杂 Agent

原因：

```text
1. 当前核心问题是知识质量和检索质量。
2. Agent 会增加不可控行为。
3. 交易场景需要强边界和可追溯。
4. 当前阶段更适合确定性 RAG pipeline。
```

推荐：

```text
先做可控 RAG。
再做有限工具调用。
最后再做 Agent。
```

---

## 24. 最终目标形态

最终系统应具备以下能力：

```text
1. 用户在交易平台任意页面提问。
2. 系统自动识别用户所在页面、交易对、周期、策略和信号。
3. 系统根据上下文选择知识域。
4. 系统从交易书籍、指标文档、策略规则、产品手册、风险管理知识中混合检索。
5. 系统通过 Reranker 找到最相关依据。
6. 系统只基于证据回答。
7. 系统返回来源、风险提示和可追溯信息。
8. 系统对即时买卖、高杠杆、收益保证、违规交易问题进行边界拦截。
9. 系统记录问答日志和用户反馈。
10. 系统通过评估集持续优化。
```

最终产品定位：

> 智能交易平台的专业知识中枢与信号解释助手。

不要定位为：

```text
AI 喊单机器人
AI 自动炒币机器人
稳赚策略机器人
预测涨跌机器人
```

应该定位为：

```text
策略知识助手
交易知识助手
信号解释助手
风控教育助手
量化知识 Copilot
智能看盘助手
```

---

## 25. 第一批开发任务清单

建议下一步直接按这个顺序开发：

```text
第一步：扩展 KnowledgeDomain 和 KnowledgeChunk。
第二步：新增 PlatformContext 和 UserContext。
第三步：增加 min_rerank_score / min_vector_score。
第四步：实现 RerankService。
第五步：新增 KeywordStore。
第六步：改造 RetrievalService 为 dense + keyword + RRF + rerank。
第七步：扩展 safety.py，增加市场操纵、API Secret、收益保证等风险类型。
第八步：拆分 Prompt 模板。
第九步：新增问答日志表。
第十步：建立 100 条评测集。
```

开发顺序不要反过来。

优先保证：

```text
检索准
不乱答
能拒答
有来源
有边界
可评估
可追溯
```

然后再做：

```text
文档后台
权限管理
商业化套餐
复杂 Agent
LoRA 微调
```

---

## 26. 结论

当前项目已经完成了智能交易平台 RAG 知识助手的正确起点。

下一阶段的核心不是“多接几个模型”，也不是“马上微调”，而是围绕以下能力做系统化升级：

```text
1. 知识域更细。
2. 知识块更懂交易。
3. 检索链路更强。
4. Reranker 更准确。
5. 拒答机制更稳。
6. 信号解释更专业。
7. 风险边界更完整。
8. 日志反馈可追溯。
9. 评估体系可量化。
10. 平台上下文可接入。
```

只要这套升级完成，项目就不再是一个普通 RAG 问答 Demo，而是可以作为智能交易平台核心模块长期演进的“交易知识中枢”。
