# WaLiAPI MCP 工具完整参考

## MCP 协议

WaLiAPI 实现 MCP (Model Context Protocol) 2024-11-05 版本，支持 SSE (Server-Sent Events) 传输。

两大能力域：**Knowledge Base (RAG)** — 文档分块→向量化→语义检索；**Wiki** — 文档摄入→结构化页面→知识图谱。

### 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/mcp` | POST | JSON-RPC 请求（直接响应或 SSE 模式）|
| `/mcp` | GET | SSE 升级，建立长连接 |
| `/mcp/sse` | GET | SSE 长连接（兼容端点）|

### JSON-RPC 方法

- `initialize` — 初始化连接，返回 server info + instructions
- `tools/list` — 列出所有可用工具
- `tools/call` — 调用工具
- `ping` — 心跳

## 工具清单

### 只读工具

#### search_knowledge_base

语义搜索知识库，返回匹配文本片段 + 相似度分数。

**参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| query | string | ✅ | — | 自然语言搜索查询 |
| kb_id | string | ❌ | "" | 指定知识库 ID；空则搜索全部 MCP 启用的知识库 |
| top_k | integer | ❌ | 5 | 最大返回结果数 |
| search_mode | string | ❌ | "hybrid" | hybrid/vector/keyword |
| vector_weight | number | ❌ | 0.7 | 混合模式向量权重 (0.0-1.0) |
| keyword_weight | number | ❌ | 0.3 | 混合模式关键词权重 (0.0-1.0) |

**搜索模式：**

- `hybrid`：向量 + 关键词混合检索（默认，推荐）
  - 向量搜索：语义相似度，通过 HNSW 索引加速
  - 关键词搜索：FTS5 全文检索，CJK 双字分词
  - 最终分数 = vector_score × vector_weight + keyword_score × keyword_weight
- `vector`：纯语义搜索，仅使用向量相似度
- `keyword`：纯关键词搜索，仅使用 FTS5，不需要 embedding

**返回：**

```
[filename.md] (score: 0.85, vec: 0.92, kw: 0.68)
chunk content here...
```

跨知识库搜索时格式略有简化（不显示分项分数）。

---

#### list_knowledge_bases

列出所有 MCP 启用的知识库。首次使用时调用一次即可。

**参数：** 无

**返回：**

```
ID: kb_xxx
Name: 项目文档
Documents: 15
Chunks: 342
Description: WaLiAPI 项目文档库
```

---

#### read_document

读取知识库中指定文档的完整内容。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 知识库 ID |
| doc_id | string | ✅ | 文档 ID（从搜索结果获取）|

---

#### ask_knowledge_base

RAG 问答：检索相关片段 → LLM 生成回答 → 返回回答 + 来源引用 + 检索详情。

**参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| question | string | ✅ | — | 问题 |
| kb_id | string | ❌ | "" | 指定知识库；空则搜索全部 |
| top_k | integer | ❌ | 5 | 检索片段数 |
| model | string | ❌ | 渠道默认 | LLM 模型名 |
| search_mode | string | ❌ | "hybrid" | hybrid/vector/keyword |
| vector_weight | number | ❌ | 0.7 | 混合模式向量权重 |
| keyword_weight | number | ❌ | 0.3 | 混合模式关键词权重 |

**返回结构：**

1. AI 回答（基于检索到的上下文生成）
2. 来源引用列表（文件名、分数、片段摘要）
3. 检索详情（每个片段的向量分数、关键词分数、符号信息）

**模型选择逻辑：**

- 如果指定了 `model` 参数，使用该模型
- 否则自动从可用渠道中选择第一个非 embedding 模型
- 最终回退到 `gpt-4o`

---

#### get_knowledge_base_stats

获取知识库详细统计信息。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 知识库 ID |

**返回：** 知识库名称、文档数（总数/就绪数）、切片数、Token 总数

---

### 写入工具 — 知识库生命周期

#### create_knowledge_base

创建新知识库。

**参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| name | string | ✅ | — | 名称（1-100字符）|
| description | string | ❌ | — | 用途描述 |
| embedding_model | string | ❌ | text-embedding-3-small | 嵌入模型 |
| embedding_channel_id | string | ❌ | — | 自定义嵌入渠道 |

⚠️ 使用前先调用 `list_knowledge_bases` 查看已有库，避免重复创建。

---

#### update_knowledge_base

更新知识库配置。仅更新提供的字段。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 知识库 ID |
| name | string | ❌ | 新名称 |
| description | string | ❌ | 新描述 |
| embedding_model | string | ❌ | 新嵌入模型（需重建索引）|
| embedding_channel_id | string | ❌ | 新嵌入渠道 |
| mcp_enabled | integer | ❌ | 1=启用 MCP, 0=禁用 |
| chunk_size | integer | ❌ | 分块大小（tokens，默认 512）|
| chunk_overlap | integer | ❌ | 分块重叠（tokens，默认 64）|

---

#### delete_knowledge_base

永久删除知识库及其所有文档、切片和索引。**不可恢复。**

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 知识库 ID |

---

### 写入工具 — 文档管理

#### upload_document

上传文档到知识库。上传后自动解析 → 分块 → 向量化 → 索引。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ⚠️ | 知识库 ID。未提供时返回可用列表 |
| filename | string | ✅ | 文件名（含扩展名）|
| content | string | ✅ | Base64 编码的文件内容 |

**支持格式：**

.txt .md .pdf .docx .doc .pptx .xlsx .csv .json .html .rs .py .js .ts .go .java .c .cpp .h .sh .yaml .yml .toml

**处理流程：**

1. 文件保存到磁盘
2. 文档类型解析（PDF 用 pdfplumber，代码按符号分块，其他用通用解析器）
3. 文本分块（默认 512 tokens，重叠 64 tokens）
4. 生成 embedding 向量
5. 插入 HNSW 索引 + FTS5 索引

处理是异步的，上传后立即返回，后台继续处理。

**去重：** 通过 SHA-256 哈希检测，相同内容不会重复上传。

---

#### delete_document

删除知识库中的指定文档及其所有切片和向量。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 知识库 ID |
| doc_id | string | ✅ | 文档 ID |

---

#### list_documents

列出知识库中所有文档及处理状态。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 知识库 ID |

**返回：** 文档名、ID、状态（pending/processing/ready/failed）、切片数、Token 数、文件大小

---

### 写入工具 — 索引管理

#### build_index

构建或重建 HNSW 向量索引。建议批量上传文档后调用。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 知识库 ID |

索引构建是异步的，通过 `get_knowledge_base_stats` 检查进度。

---

### 写入工具 — 源导入

#### import_source

从外部源批量导入文档到知识库。导入是异步的。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | string | ✅ | 目标知识库 ID |
| source_type | string | ✅ | git/url/local_dir |
| repo_url | string | ❌ | Git 仓库 URL（source_type=git）|
| branch | string | ❌ | Git 分支（默认 main）|
| token | string | ❌ | Git 访问令牌（私有仓库）|
| url | string | ❌ | URL（source_type=url）|
| dir_path | string | ❌ | 本地目录路径（source_type=local_dir）|
| excluded_dirs | array | ❌ | 排除目录名（如 ["node_modules", ".git"]）|
| included_files | array | ❌ | 包含文件扩展名（如 [".md", ".txt"]）|
| max_file_size | integer | ❌ | 最大文件大小（字节，默认 1MB）|

---

## Wiki 工具

Wiki 是结构化知识系统：文档摄入后自动生成结构化 Wiki 页面（含 frontmatter、标签、wikilinks），支持知识图谱关联。

### Wiki 只读工具

#### list_wiki_projects

列出所有 Wiki 项目。

**参数：** 无

**返回：** 项目 ID、名称、页面数、源数、描述

---

#### get_wiki_project

获取 Wiki 项目详情和统计。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

**返回：** 项目信息、页面数、源数、标签、最近摄入时间

---

#### list_wiki_pages

列出 Wiki 项目中的所有页面。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

**返回：** 页面路径、标题、类型（entity/concept/summary/index/log）

---

#### get_wiki_page

读取 Wiki 页面的完整 Markdown 内容。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |
| path | string | ✅ | 页面路径（如 'index.md' 或 'guides/api.md'）|

**返回：** 页面完整 Markdown 内容（含 frontmatter）

---

#### search_wiki

搜索 Wiki 页面。按标题、路径、内容匹配，返回摘要片段。

**参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| project_id | string | ✅ | — | Wiki 项目 ID |
| query | string | ✅ | — | 搜索关键词 |
| top_k | integer | ❌ | 10 | 最大返回结果数 |

**返回：** 匹配页面的 page_id、路径、标题、分数、摘要片段、页面类型

**搜索机制：**

- 标题和路径 LIKE 模糊匹配
- 逐文件读取内容做子串匹配
- 无 FTS5/向量检索（受限于 Wiki 页面粒度，非 chunk 粒度）
- 适合结构化知识检索，比 RAG chunk 更精确

---

#### ask_wiki

Wiki 问答：检索相关页面 → 读取完整页面内容 → LLM 生成回答。

**参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| project_id | string | ✅ | — | Wiki 项目 ID |
| question | string | ✅ | — | 问题 |
| top_k | integer | ❌ | 5 | 检索页面数 |
| model | string | ❌ | 项目配置 | LLM 模型名 |

**返回结构：**

1. AI 回答（基于完整 Wiki 页面内容生成，非 chunk）
2. 来源引用列表（页面路径、标题、分数、摘要）
3. Token 使用统计

**与 `ask_knowledge_base` 的区别：**

- `ask_knowledge_base`：基于 chunk（~512 tokens）检索 + 向量相似度
- `ask_wiki`：基于完整页面（~2000 chars）检索 + LLM 生成，上下文更完整

**模型选择逻辑：**

- 如果指定了 `model` 参数，使用该模型
- 否则使用 Wiki 项目配置的 `chat_model`
- 最终回退到 `gpt-4o`

---

#### get_wiki_tags

获取 Wiki 项目的标签列表。标签从页面 frontmatter 自动提取。

**参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| project_id | string | ✅ | — | Wiki 项目 ID |
| limit | integer | ❌ | 15 | 返回标签数 |

**返回：** 标签词、出现次数（按频率降序）

---

#### get_wiki_graph

获取 Wiki 项目的知识图谱数据。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

**返回：**

- 节点列表（id、label、path、node_type、link_count）
- 边列表（source、target、edge_type、weight）

用于可视化知识关联网络。

---

#### list_wiki_sources

列出 Wiki 项目的源资料及摄入状态。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |

**返回：** 源资料 ID、文件名、类型、状态、页面数、错误信息

---

### Wiki 写入工具

#### save_wiki_page

创建或更新 Wiki 页面。保存时自动提取 frontmatter 标签、wikilinks，更新知识图谱。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |
| path | string | ✅ | 页面路径 |
| content | string | ✅ | Markdown 内容（含 frontmatter）|

**处理流程：**

1. 解析 frontmatter（YAML）
2. 提取标签（frontmatter tags 字段）
3. 提取 wikilinks（`[[page]]` 格式）
4. 估算 token 数
5. 计算内容 hash
6. 判定页面类型（entity/concept/summary/index/log）
7. 写入数据库 + 文件系统

---

#### ingest_wiki_source

触发 Wiki 源资料摄入。源文件解析 → 生成结构化 Wiki 页面 → 提取标签和 wikilinks。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | string | ✅ | Wiki 项目 ID |
| source_id | string | ✅ | 源资料 ID（从 `list_wiki_sources` 获取）|

**返回：** 创建页面数、页面路径列表

摄入是异步的，通过 `list_wiki_pages` 检查进度。

---

## 配置参数调优（RAG）

### 搜索模式选择指南（RAG）

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 概念性查询（"如何做X"）| hybrid | 语义 + 关键词双重匹配 |
| 精确代码查找（"function foo"）| keyword | 代码标识符精确匹配 |
| 模糊语义查询（"类似X的概念"）| vector | 纯语义相似度 |
| 中文自然语言 | hybrid | CJK 双字分词 + 向量 |
| 默认 | hybrid | 覆盖大多数场景 |

### 权重调优（RAG）

- `vector_weight=0.7, keyword_weight=0.3`（默认）：语义优先，关键词补充
- `vector_weight=0.5, keyword_weight=0.5`：均衡模式
- `vector_weight=0.3, keyword_weight=0.7`：关键词优先（代码库搜索）

### top_k 调优（RAG）

- `top_k=3`：快速查询，只看最相关的
- `top_k=5`（默认）：标准查询
- `top_k=10`：深度查询，需要更多上下文
- `top_k>10`：不推荐，增加噪声

## 错误码

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| -32601 | 未知方法 | 检查 MCP 协议版本 |
| -32603 | 内部错误 | 查看具体错误信息 |
| 连接被拒绝 | WaLiAPI 未运行 | 启动 WaLiAPI 应用 |
| 超时 | 网络或服务问题 | 检查服务状态 |
| embedding 失败 | 无可用 embedding 渠道 | 配置支持 embedding 的渠道 |
| RAG 回答失败 | 无可用 chat 渠道 | 配置支持 chat 的渠道 |
| Wiki 无页面 | 先添加源资料并执行摄入 | 调用 `list_wiki_sources` + `ingest_wiki_source` |
| Wiki 项目不存在 | 项目 ID 错误或项目未创建 | 调用 `list_wiki_projects` 确认 |
