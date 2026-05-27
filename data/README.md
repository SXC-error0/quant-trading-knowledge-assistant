# 数据目录说明

本目录只存放**格式样例**和可公开使用的测试资料，不提交商业书籍原文或用户私有资料。

## 目录建议

```text
data/
├── samples/       # 可提交至 Git 的非版权示例数据
├── private/       # 本地原始资料或切片结果，已被 .gitignore 忽略
└── imported/      # 本地导入中间结果，已被 .gitignore 忽略
```

正式数据建议从你的切片系统导出至 `data/private/`，确认字段格式后，通过 `scripts/import_chunks.py` 导入服务。
