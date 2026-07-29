---
name: waliapi-rag
description: WaLiAPI 知识库 RAG 技能。通过 MCP 协议连接 WaLiAPI 本地知识库，支持语义搜索、RAG 问答、文档管理、知识库创建与维护等全生命周期操作。触发词：「知识库搜索」「知识库问答」「RAG 检索」「问我知识库」「搜索文档」「 WaLiAPI 知识库」「创建知识库」「上传文档到知识库」「导入代码到知识库」「知识库统计」「构建索引」。当用户提到知识库、RAG、文档检索、语义搜索、向量搜索等相关概念时触发。
license: MIT
metadata:
  author: fuzhengwei
  version: "1.0.0"
  category: knowledge-base
  homepage: https://github.com/fuzhengwei/waliapi-rag-skills
---

# WaLiAPI 知识库 RAG 技能

通过 MCP (Model Context Protocol) 连接 WaLiAPI 本地知识库服务，执行语义搜索、RAG 问答、文档管理等操作。

## 前置条件

- WaLiAPI 桌面应用已安装并运行（默认端口 8777）
- 至少一个渠道已配置且可用（用于 embedding 和 RAG 问答）
- 至少一个知识库已创建并启用 MCP 访问

## MCP 服务地址配置

### 首次使用

如果 `~/.qclaw/skills/waliapi-rag/config.json` 不存在或 `mcp_url` 为空，**必须先让用户提供 MCP 服务地址**。

询问用户：
> 请提供 WaLiAPI 的 MCP 服务地址。
> 默认格式：`http://127.0.0.1:8777/mcp`
> （WaLiAPI 默认端口 8777，MCP 端点为 /mcp）

用户提供后，将地址保存到配置文件：

```bash
cat > ~/.qclaw/skills/waliapi-rag/config.json << 'EOF'
{
  "mcp_url": "http://127.0.0.1:8777/mcp"
}
EOF
```

### 更换 MCP 服务地址

用户说「更换 MCP 地址」「切换 WaLiAPI 服务」「更新 MCP URL」等时，重新询问并写入配置文件。

## 工作流程

### Step 1: 读取配置

每次触发时，先读取 `~/.qclaw/skills/waliapi-rag/config.json` 获取 `mcp_url`。如果文件不存在或 `mcp_url` 为空，进入「首次使用」流程。

### Step 2: 执行 MCP 调用

所有 MCP 调用通过 `scripts/mcp_call.py` 执行。该脚本封装了 MCP JSON-RPC 协议（SSE transport），提供统一的命令行接口。

```bash
# 通用调用格式
python3 ~/.qclaw/skills/waliapi-rag/scripts/mcp_call.py <tool_name> '<json_arguments>'
```

### Step 3: 按需选择工具

根据用户意图选择合适的 MCP 工具：

## 工具使用指南

### 🔍 查询类（只读）

| 用户意图 | MCP 工具 | 说明 |
|---------|----------|------|
| 「列出知识库」「有哪些知识库」 | `list_knowledge_bases` | 首次使用时调用一次，缓存结果 |
| 「搜索 XXX」「查找 XXX」 | `search_knowledge_base` | 语义搜索，返回匹配片段+分数 |
| 「问一下知识库」「RAG 问答」 | `ask_knowledge_base` | **首选工具**，RAG 问答，返回 AI 回答+来源引用 |
| 「看看这个文档全文」 | `read_document` | 读取完整文档内容 |
| 「知识库统计」「知识库状态」 | `get_knowledge_base_stats` | 文档数、切片数、Token 数、索引状态 |

### 📝 管理类（写入）

| 用户意图 | MCP 工具 | 说明 |
|---------|----------|------|
| 「创建知识库」 | `create_knowledge_base` | 创建新知识库 |
| 「更新知识库配置」 | `update_knowledge_base` | 修改名称、分块大小、MCP 开关等 |
| 「删除知识库」 | `delete_knowledge_base` | 永久删除（不可恢复） |
| 「上传文档」 | `upload_document` | 上传后自动解析→分块→向量化→索引 |
| 「删除文档」 | `delete_document` | 删除指定文档 |
| 「列出文档」 | `list_documents` | 查看知识库中的所有文档 |
| 「构建索引」「重建索引」 | `build_index` | 构建/重建 HNSW 向量索引 |
| 「导入 Git 仓库」 | `import_source` | 从 Git/URL/本地目录批量导入 |

## 工具调用详解

### list_knowledge_bases — 列出知识库

```bash
python3 scripts/mcp_call.py list_knowledge_bases '{}'
```

无需参数。返回所有 MCP 启用的知识库 ID、名称、文档数、切片数。

### search_knowledge_base — 语义搜索

```bash
python3 scripts/mcp_call.py search_knowledge_base '{"query": "如何配置渠道", "top_k": 5, "search_mode": "hybrid"}'
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| query | string | ✅ | — | 搜索查询 |
| kb_id | string | ❌ | 搜索全部 | 指定知识库 ID |
| top_k | int | ❌ | 5 | 返回结果数 |
| search_mode | string | ❌ | hybrid | hybrid/vector/keyword |
| vector_weight | float | ❌ | 0.7 | 混合模式向量权重 |
| keyword_weight | float | ❌ | 0.3 | 混合模式关键词权重 |

### ask_knowledge_base — RAG 问答（首选）

```bash
python3 scripts/mcp_call.py ask_knowledge_base '{"question": "WaLiAPI 支持哪些渠道类型？", "kb_id": "xxx", "top_k": 5}'
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| question | string | ✅ | — | 问题 |
| kb_id | string | ❌ | 搜索全部 | 指定知识库 ID |
| top_k | int | ❌ | 5 | 检索片段数 |
| model | string | ❌ | 渠道默认 | LLM 模型 |
| search_mode | string | ❌ | hybrid | hybrid/vector/keyword |
| vector_weight | float | ❌ | 0.7 | 混合模式向量权重 |
| keyword_weight | float | ❌ | 0.3 | 混合模式关键词权重 |

### create_knowledge_base — 创建知识库

```bash
python3 scripts/mcp_call.py create_knowledge_base '{"name": "项目文档", "description": "WaLiAPI 项目文档"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 知识库名称（1-100字符）|
| description | string | ❌ | 用途描述 |
| embedding_model | string | ❌ | 默认 text-embedding-3-small |
| embedding_channel_id | string | ❌ | 自定义嵌入渠道 |

### upload_document — 上传文档

```bash
python3 scripts/mcp_call.py upload_document '{"kb_id": "xxx", "filename": "readme.md", "content": "<base64>"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ⚠️ | 未提供时返回可用知识库列表 |
| filename | string | ✅ | 文件名（含扩展名）|
| content | string | ✅ | Base64 编码的文件内容 |

支持格式：.txt .md .pdf .docx .doc .pptx .xlsx .csv .json .html .rs .py .js .ts .go .java .c .cpp .h .sh .yaml .yml .toml

### import_source — 导入源

```bash
# 从 Git 仓库导入
python3 scripts/mcp_call.py import_source '{"kb_id": "xxx", "source_type": "git", "repo_url": "https://github.com/user/repo", "branch": "main"}'

# 从 URL 导入
python3 scripts/mcp_call.py import_source '{"kb_id": "xxx", "source_type": "url", "url": "https://example.com/doc"}'

# 从本地目录导入
python3 scripts/mcp_call.py import_source '{"kb_id": "xxx", "source_type": "local_dir", "dir_path": "/path/to/docs"}'
```

### 其他工具

```bash
# 读取文档
python3 scripts/mcp_call.py read_document '{"kb_id": "xxx", "doc_id": "yyy"}'

# 知识库统计
python3 scripts/mcp_call.py get_knowledge_base_stats '{"kb_id": "xxx"}'

# 更新知识库
python3 scripts/mcp_call.py update_knowledge_base '{"kb_id": "xxx", "name": "新名称"}'

# 删除知识库
python3 scripts/mcp_call.py delete_knowledge_base '{"kb_id": "xxx"}'

# 列出文档
python3 scripts/mcp_call.py list_documents '{"kb_id": "xxx"}'

# 删除文档
python3 scripts/mcp_call.py delete_document '{"kb_id": "xxx", "doc_id": "yyy"}'

# 构建索引
python3 scripts/mcp_call.py build_index '{"kb_id": "xxx"}'
```

## 使用模式

### 模式 A: 直接问答（最常见）

用户：「问一下知识库，WaLiAPI 支持哪些协议？」

1. 读取配置获取 `mcp_url`
2. （首次）调用 `list_knowledge_bases` 获取可用知识库
3. 调用 `ask_knowledge_base`，传入用户问题
4. 返回 AI 回答 + 来源引用

### 模式 B: 搜索原始片段

用户：「搜索一下渠道配置相关的内容」

1. 调用 `search_knowledge_base`，使用用户关键词
2. 返回匹配的文本片段和相似度分数

### 模式 C: 文档管理

用户：「把这份 PDF 上传到知识库」

1. 读取文件，Base64 编码
2. 调用 `upload_document`
3. 返回处理状态

### 模式 D: 批量导入

用户：「把这个 Git 仓库导入知识库」

1. 调用 `import_source`，传入仓库 URL
2. 返回导入任务状态（异步执行）

## 最佳实践

1. **优先用 `ask_knowledge_base`**：它内部已做 RAG（检索+生成），不需要先 search 再总结
2. **缓存知识库列表**：首次调用 `list_knowledge_bases` 后记住结果，不要重复调用
3. **搜索模式选择**：
   - `hybrid`（默认）：向量+关键词混合，适合大多数场景
   - `vector`：纯语义搜索，适合概念性查询
   - `keyword`：纯关键词，适合精确匹配代码/标识符
4. **上传文档时指定 `kb_id`**：不指定会返回列表要求选择，多一次交互
5. **大文件上传后等待处理**：上传是异步的，解析→分块→向量化需要时间
6. **导入后用 `get_knowledge_base_stats` 检查进度**

## 脚本依赖

- Python 3.8+
- `requests` 库（用于 SSE + HTTP 调用）

如果 `requests` 未安装，脚本会自动尝试 `pip install requests`。

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| 连接被拒绝 | 确认 WaLiAPI 正在运行，端口正确 |
| MCP 工具不存在 | 确认 WaLiAPI 版本支持 MCP（v0.1.1+）|
| 知识库为空 | 先创建知识库并上传文档 |
| embedding 失败 | 确认至少一个渠道支持 embedding 模型 |
| RAG 回答失败 | 确认至少一个渠道支持 chat 模型 |
| 搜索无结果 | 尝试调整 `top_k` 或切换 `search_mode` |
