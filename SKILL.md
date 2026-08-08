---
name: waliapi-skills
description: WaLiAPI 知识库与 Wiki 技能。通过 MCP 协议连接 WaLiAPI 本地服务，支持 RAG 语义搜索、RAG 问答、文档管理、Wiki 知识页面管理、Wiki 搜索与问答、知识图谱、标签检索等全生命周期操作。触发词：「知识库搜索」「知识库问答」「RAG 检索」「问我知识库」「搜索文档」「WaLiAPI 知识库」「创建知识库」「上传文档到知识库」「导入代码到知识库」「知识库统计」「构建索引」「Wiki 搜索」「Wiki 问答」「知识图谱」「Wiki 标签」「Wiki 页面」「列出 Wiki 项目」。当用户提到知识库、RAG、文档检索、语义搜索、向量搜索、Wiki、知识图谱、结构化知识等相关概念时触发。
license: MIT
metadata:
  author: fuzhengwei
  version: "2.0.0"
  category: knowledge-base
  homepage: https://github.com/fuzhengwei/waliapi-skills
---

# WaLiAPI 知识库与 Wiki 技能

通过 MCP (Model Context Protocol) 连接 WaLiAPI 本地服务，执行 RAG 语义搜索、RAG 问答、文档管理、Wiki 知识页面管理、Wiki 搜索与问答、知识图谱等操作。

## 两大能力域

WaLiAPI 有两个独立的知识系统：

| 能力域 | 说明 | MCP 工具前缀 | 适合场景 |
|--------|------|-------------|---------|
| **Knowledge Base (RAG)** | 文档分块 → 向量化 → 语义检索 | `*_knowledge_base` | 原始文档搜索、跨文档 RAG 问答 |
| **Wiki** | 文档摄入 → 结构化页面 → 知识图谱 | `*_wiki` / `list_wiki_*` | 结构化知识浏览、精确页面搜索、标签导航 |

两者互补：RAG 适合"找原始片段"，Wiki 适合"看结构化知识"。

## 前置条件

- WaLiAPI 桌面应用已安装并运行（默认端口 8777）
- 至少一个渠道已配置且可用（用于 embedding 和 RAG 问答）
- RAG：至少一个知识库已创建并启用 MCP 访问
- Wiki：至少一个 Wiki 项目已创建

## MCP 服务地址配置

### 首次使用

如果 `~/.qclaw/skills/waliapi-skills/config.json` 不存在或 `mcp_url` 为空，**必须先让用户提供 MCP 服务地址**。

询问用户：
> 请提供 WaLiAPI 的 MCP 服务地址。
> 默认格式：`http://127.0.0.1:8777/mcp`
> （WaLiAPI 默认端口 8777，MCP 端点为 /mcp）

用户提供后，将地址保存到配置文件：

```bash
cat > ~/.qclaw/skills/waliapi-skills/config.json << 'EOF'
{
  "mcp_url": "http://127.0.0.1:8777/mcp"
}
EOF
```

### 更换 MCP 服务地址

用户说「更换 MCP 地址」「切换 WaLiAPI 服务」「更新 MCP URL」等时，重新询问并写入配置文件。

## 工作流程

### Step 1: 读取配置

每次触发时，先读取 `~/.qclaw/skills/waliapi-skills/config.json` 获取 `mcp_url`。如果文件不存在或 `mcp_url` 为空，进入「首次使用」流程。

### Step 2: 执行 MCP 调用

所有 MCP 调用通过 `scripts/mcp_call.py` 执行。该脚本封装了 MCP JSON-RPC 协议（SSE transport），提供统一的命令行接口。

```bash
# 通用调用格式
python3 ~/.qclaw/skills/waliapi-skills/scripts/mcp_call.py <tool_name> '<json_arguments>'
```

### Step 3: 按需选择工具

根据用户意图选择合适的 MCP 工具。

---

## RAG 工具（Knowledge Base）

### 🔍 RAG 查询类（只读）

| 用户意图 | MCP 工具 | 说明 |
|---------|----------|------|
| 「列出知识库」「有哪些知识库」 | `list_knowledge_bases` | 首次使用时调用一次，缓存结果 |
| 「搜索 XXX」「查找 XXX」 | `search_knowledge_base` | 语义搜索，返回匹配片段+分数 |
| 「问一下知识库」「RAG 问答」 | `ask_knowledge_base` | **RAG 首选工具**，检索+生成 |
| 「看看这个文档全文」 | `read_document` | 读取完整文档内容 |
| 「知识库统计」「知识库状态」 | `get_knowledge_base_stats` | 文档数、切片数、Token 数、索引状态 |

### 📝 RAG 管理类（写入）

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

### RAG 工具调用详解

#### list_knowledge_bases — 列出知识库

```bash
python3 scripts/mcp_call.py list_knowledge_bases '{}'
```

无需参数。返回所有 MCP 启用的知识库 ID、名称、文档数、切片数。

#### search_knowledge_base — 语义搜索

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

#### ask_knowledge_base — RAG 问答（RAG 首选）

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

#### create_knowledge_base — 创建知识库

```bash
python3 scripts/mcp_call.py create_knowledge_base '{"name": "项目文档", "description": "WaLiAPI 项目文档"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 知识库名称（1-100字符）|
| description | string | ❌ | 用途描述 |
| embedding_model | string | ❌ | 默认 text-embedding-3-small |
| embedding_channel_id | string | ❌ | 自定义嵌入渠道 |

#### upload_document — 上传文档

```bash
python3 scripts/mcp_call.py upload_document '{"kb_id": "xxx", "filename": "readme.md", "content": "<base64>"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ⚠️ | 未提供时返回可用知识库列表 |
| filename | string | ✅ | 文件名（含扩展名）|
| content | string | ✅ | Base64 编码的文件内容 |

支持格式：.txt .md .pdf .docx .doc .pptx .xlsx .csv .json .html .rs .py .js .ts .go .java .c .cpp .h .sh .yaml .yml .toml

#### import_source — 导入源

```bash
# 从 Git 仓库导入
python3 scripts/mcp_call.py import_source '{"kb_id": "xxx", "source_type": "git", "repo_url": "https://github.com/user/repo", "branch": "main"}'

# 从 URL 导入
python3 scripts/mcp_call.py import_source '{"kb_id": "xxx", "source_type": "url", "url": "https://example.com/doc"}'

# 从本地目录导入
python3 scripts/mcp_call.py import_source '{"kb_id": "xxx", "source_type": "local_dir", "dir_path": "/path/to/docs"}'
```

#### 其他 RAG 工具

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

---

## Wiki 工具

Wiki 是结构化知识系统：文档摄入后自动生成结构化 Wiki 页面（含 frontmatter、标签、wikilinks），支持知识图谱关联。

### 📖 Wiki 查询类（只读）

| 用户意图 | MCP 工具 | 说明 |
|---------|----------|------|
| 「列出 Wiki 项目」 | `list_wiki_projects` | 获取所有 Wiki 项目 |
| 「Wiki 项目详情」 | `get_wiki_project` | 统计、标签、页面概览 |
| 「列出 Wiki 页面」 | `list_wiki_pages` | 所有页面：路径、标题、类型 |
| 「读取 Wiki 页面」 | `get_wiki_page` | 完整 Markdown 内容 |
| 「搜索 Wiki」 | `search_wiki` | 按标题/路径/内容搜索页面 |
| 「问 Wiki」 | `ask_wiki` | Wiki Q&A：检索+LLM 生成 |
| 「Wiki 标签」 | `get_wiki_tags` | 标签列表（frontmatter 提取） |
| 「知识图谱」 | `get_wiki_graph` | 页面节点 + wikilinks 边 |
| 「Wiki 源资料」 | `list_wiki_sources` | 源文件及摄入状态 |

### 📝 Wiki 管理类（写入）

| 用户意图 | MCP 工具 | 说明 |
|---------|----------|------|
| 「保存 Wiki 页面」 | `save_wiki_page` | 创建/更新页面，自动提取标签和 wikilinks |
| 「摄入 Wiki 源」 | `ingest_wiki_source` | 触发源文件摄入 → 生成结构化页面 |

### Wiki 工具调用详解

#### list_wiki_projects — 列出 Wiki 项目

```bash
python3 scripts/mcp_call.py list_wiki_projects '{}'
```

无需参数。返回所有 Wiki 项目的 ID、名称、页面数、源数、描述。

#### get_wiki_project — 获取 Wiki 项目详情

```bash
python3 scripts/mcp_call.py get_wiki_project '{"project_id": "xxx"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

#### list_wiki_pages — 列出 Wiki 页面

```bash
python3 scripts/mcp_call.py list_wiki_pages '{"project_id": "xxx"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

返回所有页面的路径、标题、类型（entity/concept/summary/index/log）。

#### get_wiki_page — 读取 Wiki 页面

```bash
python3 scripts/mcp_call.py get_wiki_page '{"project_id": "xxx", "path": "guides/setup.md"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |
| path | string | ✅ | 页面路径（如 'index.md' 或 'guides/api.md'）|

#### save_wiki_page — 保存 Wiki 页面

```bash
python3 scripts/mcp_call.py save_wiki_page '{"project_id": "xxx", "path": "guides/api.md", "content": "# API Guide\n\n..."}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |
| path | string | ✅ | 页面路径 |
| content | string | ✅ | Markdown 内容（含 frontmatter）|

保存时自动提取 frontmatter 标签、wikilinks，更新知识图谱。

#### search_wiki — 搜索 Wiki 页面

```bash
python3 scripts/mcp_call.py search_wiki '{"project_id": "xxx", "query": "渠道配置", "top_k": 10}'
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| project_id | string | ✅ | — | Wiki 项目 ID |
| query | string | ✅ | — | 搜索关键词 |
| top_k | int | ❌ | 10 | 最大返回结果数 |

返回匹配页面的标题、路径、摘要片段。适合结构化知识检索，比 RAG chunk 更精确。

#### ask_wiki — Wiki 问答

```bash
python3 scripts/mcp_call.py ask_wiki '{"project_id": "xxx", "question": "如何配置渠道？", "top_k": 5}'
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| project_id | string | ✅ | — | Wiki 项目 ID |
| question | string | ✅ | — | 问题 |
| top_k | int | ❌ | 5 | 检索页面数 |
| model | string | ❌ | 项目配置 | LLM 模型 |

基于完整 Wiki 页面而非 chunk 的 LLM 问答，返回回答 + 来源引用。

#### get_wiki_tags — 获取 Wiki 标签

```bash
python3 scripts/mcp_call.py get_wiki_tags '{"project_id": "xxx", "limit": 15}'
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| project_id | string | ✅ | — | Wiki 项目 ID |
| limit | int | ❌ | 15 | 返回标签数 |

标签从页面 frontmatter 自动提取，按频率排序。

#### get_wiki_graph — 获取知识图谱

```bash
python3 scripts/mcp_call.py get_wiki_graph '{"project_id": "xxx"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

返回节点（页面）和边（wikilinks 关联），用于可视化知识关联。

#### list_wiki_sources — 列出 Wiki 源资料

```bash
python3 scripts/mcp_call.py list_wiki_sources '{"project_id": "xxx"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

返回源文件列表及摄入状态（pending/ingested/failed）。

#### ingest_wiki_source — 摄入 Wiki 源

```bash
python3 scripts/mcp_call.py ingest_wiki_source '{"project_id": "xxx", "source_id": "yyy"}'
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |
| source_id | string | ✅ | 源资料 ID |

触发源文件摄入：自动解析文档 → 生成结构化 Wiki 页面 → 提取标签和 wikilinks。

---

## 使用模式

### 模式 A: RAG 直接问答（最常见）

用户：「问一下知识库，WaLiAPI 支持哪些协议？」

1. 读取配置获取 `mcp_url`
2. （首次）调用 `list_knowledge_bases` 获取可用知识库
3. 调用 `ask_knowledge_base`，传入用户问题
4. 返回 AI 回答 + 来源引用

### 模式 B: Wiki 问答

用户：「问一下 Wiki，渠道怎么配置？」

1. （首次）调用 `list_wiki_projects` 获取可用项目
2. 调用 `ask_wiki`，传入问题和 project_id
3. 返回基于结构化 Wiki 页面的 AI 回答

### 模式 C: Wiki 标签导航

用户：「Wiki 里有哪些标签？」

1. 调用 `get_wiki_tags` 获取标签列表
2. 用户选择标签后，用 `search_wiki` 搜索相关页面

### 模式 D: Wiki 页面浏览

用户：「看看 Wiki 的 index 页面」

1. 调用 `list_wiki_pages` 获取页面列表
2. 调用 `get_wiki_page` 读取指定页面内容

### 模式 E: 文档管理

用户：「把这份 PDF 上传到知识库」

1. 读取文件，Base64 编码
2. 调用 `upload_document`
3. 返回处理状态

### 模式 F: 批量导入

用户：「把这个 Git 仓库导入知识库」

1. 调用 `import_source`，传入仓库 URL
2. 返回导入任务状态（异步执行）

---

## 最佳实践

1. **优先用 `ask_knowledge_base` / `ask_wiki`**：它们内部已做检索+生成，不需要先 search 再总结
2. **RAG vs Wiki 选择**：
   - RAG：原始文档搜索、跨文档问答、不需要结构化
   - Wiki：结构化知识浏览、精确页面搜索、标签导航、知识图谱
3. **缓存列表**：首次调用 `list_knowledge_bases` / `list_wiki_projects` 后记住结果，不要重复调用
4. **搜索模式选择（RAG）**：
   - `hybrid`（默认）：向量+关键词混合，适合大多数场景
   - `vector`：纯语义搜索，适合概念性查询
   - `keyword`：纯关键词，适合精确匹配代码/标识符
5. **大文件上传后等待处理**：上传是异步的，解析→分块→向量化需要时间
6. **导入后用 `get_knowledge_base_stats` / `list_wiki_pages` 检查进度**

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
| Wiki 无页面 | 先添加源资料并执行摄入 |
| embedding 失败 | 确认至少一个渠道支持 embedding 模型 |
| RAG/Wiki 回答失败 | 确认至少一个渠道支持 chat 模型 |
| 搜索无结果 | 尝试调整 `top_k` 或切换 `search_mode`（RAG）|
