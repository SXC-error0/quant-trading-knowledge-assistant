#!/usr/bin/env python3
"""Generate Q&A training pairs from knowledge chunks using the configured LLM.

Reads the same JSONL format produced by process_books.py / import_chunks.py
and outputs a JSONL file in ShareGPT format (for LLaMA-Factory fine-tuning).

Usage:
    python scripts/generate_qa.py data/quant_chunks.jsonl \\
        --qa-per-chunk 3 \\
        --output data/training/qa_pairs.jsonl \\
        --max-chunks 500

Output format (ShareGPT / LLaMA-Factory):
    {"conversations": [
        {"from": "system", "value": "<system prompt>"},
        {"from": "human",  "value": "MACD 金叉的含义是什么？"},
        {"from": "gpt",    "value": "## 结论\\n...\\n## 风险提示\\n..."}
    ]}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

# Allow running as a script from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.prompts import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Prompts for Q&A generation
# ---------------------------------------------------------------------------

_GEN_SYSTEM = (
    "你是一个量化交易领域的专业题目生成器。"
    "根据提供的文本内容，生成真实用户会提出的专业问题，以及基于原文的详细标准回答。"
    "回答必须严格遵循指定格式，不得超出原文信息范围。"
)

_GEN_USER_TMPL = """请基于以下量化交易知识片段，生成 {n} 对问答。

来源：{title} / {chapter}
内容：
{content}

要求：
1. 问题应是用户在学习量化交易或使用看盘工具时会真实提出的问题。
2. 回答只能基于上方"内容"中的信息，不可添加原文没有的说法。
3. 回答格式严格遵循：
   ## 结论
   （一句话核心结论）
   ## 原理解释
   （详细解释）
   ## 使用注意
   （注意事项）
   ## 风险提示
   本回答用于解释交易知识与系统规则，不构成对具体数字资产当前时点的确定性买卖建议、收益承诺或投资保证。

仅输出 JSON 数组，不要其他任何文字：
[
  {{"question": "...", "answer": "..."}},
  ...
]"""

_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


async def generate_qa_for_chunk(
    client: AsyncOpenAI,
    model: str,
    chunk: dict,
    n: int,
) -> list[dict[str, str]]:
    user_msg = _GEN_USER_TMPL.format(
        n=n,
        title=chunk.get("document_title", ""),
        chapter=chunk.get("chapter", ""),
        content=chunk["content"],
    )
    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": _GEN_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content or "[]"
        m = _JSON_ARRAY.search(raw)
        if not m:
            return []
        pairs = json.loads(m.group())
        return [p for p in pairs if isinstance(p, dict) and "question" in p and "answer" in p]
    except Exception as exc:
        print(f"  [warn] chunk {chunk.get('chunk_id', '?')}: {exc}", file=sys.stderr)
        return []


def to_sharegpt(qa: dict[str, str]) -> dict:
    return {
        "conversations": [
            {"from": "system", "value": SYSTEM_PROMPT.strip()},
            {"from": "human", "value": qa["question"].strip()},
            {"from": "gpt", "value": qa["answer"].strip()},
        ]
    }


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    if not settings.llm_configuration_ready():
        sys.exit("LLM 未配置。请先设置 .env 中的 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL。")

    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    input_path = Path(args.input_file)
    chunks: list[dict] = []
    with input_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    if args.max_chunks:
        chunks = chunks[: args.max_chunks]

    print(f"读取 {len(chunks)} 个知识块，每块生成 {args.qa_per_chunk} 对问答…")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with output_path.open("w", encoding="utf-8") as out:
        for i, chunk in enumerate(chunks, start=1):
            pairs = await generate_qa_for_chunk(client, settings.llm_model, chunk, args.qa_per_chunk)
            for pair in pairs:
                out.write(json.dumps(to_sharegpt(pair), ensure_ascii=False) + "\n")
                total += 1
            if i % 20 == 0 or i == len(chunks):
                print(f"  [{i}/{len(chunks)}] 已生成 {total} 对")

    print(f"\n完成。共生成 {total} 对问答 → {output_path}")

    # Also write a LLaMA-Factory dataset_info entry
    dataset_info_path = output_path.parent / "dataset_info.json"
    dataset_name = output_path.stem
    entry = {
        dataset_name: {
            "file_name": output_path.name,
            "formatting": "sharegpt",
            "columns": {"messages": "conversations"},
            "tags": {"role_tag": "from", "content_tag": "value", "user_tag": "human", "assistant_tag": "gpt", "system_tag": "system"},
        }
    }
    existing: dict = {}
    if dataset_info_path.exists():
        existing = json.loads(dataset_info_path.read_text(encoding="utf-8"))
    existing.update(entry)
    dataset_info_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"LLaMA-Factory dataset_info 已写入 → {dataset_info_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ShareGPT Q&A training data from knowledge chunks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_file", help="JSONL chunks file (from process_books.py).")
    parser.add_argument("--qa-per-chunk", type=int, default=3, help="Q&A pairs to generate per chunk.")
    parser.add_argument(
        "--output",
        default="data/training/qa_pairs.jsonl",
        help="Output ShareGPT JSONL path.",
    )
    parser.add_argument("--max-chunks", type=int, default=None, help="Limit number of chunks processed.")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
