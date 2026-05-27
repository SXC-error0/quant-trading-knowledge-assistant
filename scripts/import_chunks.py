import argparse
import asyncio
import json
from pathlib import Path

import httpx


async def import_jsonl(input_file: Path, api_url: str, batch_size: int) -> None:
    chunks = []
    with input_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"第 {line_number} 行不是有效 JSON：{exc}") from exc

    async with httpx.AsyncClient(timeout=120.0) as client:
        imported = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            endpoint = f"{api_url.rstrip('/')}/api/v1/knowledge/import"
            response = await client.post(endpoint, json={"chunks": batch})
            response.raise_for_status()
            imported += response.json()["imported_count"]
            print(f"已导入 {imported}/{len(chunks)} 个知识块")
    print("导入完成。")


def main() -> None:
    parser = argparse.ArgumentParser(description="导入切片系统产生的 JSONL 知识块。")
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    asyncio.run(import_jsonl(args.input_file, args.api_url, args.batch_size))


if __name__ == "__main__":
    main()
