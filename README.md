<div align="center">

# waliapi-rag-skills

### WaLiAPI 知识库 RAG 技能 · 通过 MCP 连接本地知识库

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-blue.svg)](https://modelcontextprotocol.io)
[![WaLiAPI](https://img.shields.io/badge/WaLiAPI-0.1.1%2B-orange.svg)](https://github.com/fuzhengwei/WaLiAPI)

</div>

> **waliapi-rag-skills** 是 [WaLiAPI](https://github.com/fuzhengwei/WaLiAPI) 的配套技能包。通过 MCP (Model Context Protocol) 连接 WaLiAPI 本地知识库服务，让 AI Agent 具备语义搜索、RAG 问答、文档管理等能力。

---

## 📑 目录

- [这是什么](#-这是什么)
- [前置条件](#-前置条件)
- [快速开始](#-快速开始)
- [技能能力](#-技能能力)
- [工作原理](#-工作原理)
- [项目结构](#-项目结构)
- [配置说明](#-配置说明)
- [使用示例](#-使用示例)
- [故障排除](#-故障排除)
- [许可证](#-许可证)

---

## 🎯 这是什么

**WaLiAPI** 是一款本地运行的 LLM API 网关桌面软件，内置知识库与 RAG 能力，支持多渠道模型管理、协议转换、安全审计等功能。

**waliapi-rag-skills** 是 WaLiAPI 的配套技能包，专门用于在 AI Agent（如 QClaw）中调用 WaLiAPI 的知识库 MCP 服务。它封装了 MCP JSON-RPC 协议（SSE 传输），提供统一的命令行接口，让 Agent 可以：

- 🔍 **语义搜索** — 向量 + 关键词混合检索
- 🤖 **RAG 问答** — 检索 + LLM 生成，一步到位
- 📄 **文档管理** — 上传、读取、删除、批量导入
- 📚 **知识库管理** — 创建、更新、删除、索引构建

```
┌──────────────┐     MCP/SSE     ┌──────────────┐     HTTP      ┌──────────────┐
│  AI Agent    │ ◄──────────────► │   WaLiAPI    │ ◄───────────► │  上游模型    │
│  (QClaw等)   │   /mcp 端点      │  本地网关     │   OpenAI协议   │  (多渠道)    │
└──────────────┘                  └──────────────┘               └──────────────┘
                                         │
                                         │ SQLite + HNSW + FTS5
                                         ▼
                                  ┌──────────────┐
                                  │   知识库      │
                                  │  文档/向量/索引│
                                  └──────────────┘
```

---

## 📋 前置条件

| 条件 | 说明 |
|:---|:---|
| **WaLiAPI 已安装并运行** | 下载地址：[WaLiAPI Releases](https://github.com/fuzhengwei/WaLiAPI/releases) |
| **WaLiAPI 版本 ≥ 0.1.1** | MCP 知识库服务从 v0.1.1 开始支持 |
| **至少一个渠道已配置** | 需要支持 embedding 的渠道（用于文档向量化）和 chat 渠道（用于 RAG 问答） |
| **至少一个知识库已创建** | 在 WaLiAPI 中创建知识库并启用 MCP 访问 |
| **Python 3.8+** | 技能脚本运行环境 |
| **requests 库** | MCP 调用脚本依赖（未安装时自动安装） |

---

## 🚀 快速开始

### 1. 安装技能

将本技能包安装到 Agent 的 skills 目录：

```bash
# QClaw 用户
cp -r . ~/.qclaw/skills/waliapi-rag/
```

### 2. 启动 WaLiAPI

打开 WaLiAPI 桌面应用，确认服务正在运行（默认端口 8777）。

### 3. 配置 MCP 地址

首次使用时，Agent 会询问 MCP 服务地址。默认为：

```
http://127.0.0.1:8777/mcp
```

也可以手动写入配置文件：

```bash
cat > ~/.qclaw/skills/waliapi-rag/config.json << 'EOF'
{
  "mcp_url": "http://127.0.0.1:8777/mcp"
}
EOF
```

### 4. 开始使用

在 Agent 对话中直接说出你的需求：

- 「问一下知识库，WaLiAPI 支持哪些协议？」
- 「搜索一下渠道配置相关的内容」
- 「把这个文件上传到知识库」
- 「列出所有知识库」

---

## 🛠 技能能力

### 🔍 查询类（只读）

| 能力 | MCP 工具 | 说明 |
|:---|:---|:---|
| 列出知识库 | `list_knowledge_bases` | 获取所有 MCP 启用的知识库 |
| 语义搜索 | `search_knowledge_base` | 向量 + 关键词混合检索，返回匹配片段 + 分数 |
| RAG 问答 | `ask_knowledge_base` | **首选工具**，检索 + LLM 生成，返回回答 + 来源引用 |
| 读取文档 | `read_document` | 读取知识库中指定文档的完整内容 |
| 知识库统计 | `get_knowledge_base_stats` | 文档数、切片数、Token 数、索引状态 |

### 📝 管理类（写入）

| 能力 | MCP 工具 | 说明 |
|:---|:---|:---|
| 创建知识库 | `create_knowledge_base` | 创建新知识库，可指定 embedding 模型 |
| 更新配置 | `update_knowledge_base` | 修改名称、分块大小、MCP 开关等 |
| 删除知识库 | `delete_knowledge_base` | 永久删除（不可恢复） |
| 上传文档 | `upload_document` | 自动解析 → 分块 → 向量化 → 索引 |
| 删除文档 | `delete_document` | 删除指定文档及其所有切片 |
| 列出文档 | `list_documents` | 查看知识库中所有文档及处理状态 |
| 构建索引 | `build_index` | 构建/重建 HNSW 向量索引 |
| 导入源 | `import_source` | 从 Git/URL/本地目录批量导入 |

---

## 🔧 工作原理

```
用户对话
  │
  ▼
Agent 读取 SKILL.md → 匹配用户意图 → 选择 MCP 工具
  │
  ▼
scripts/mcp_call.py <tool_name> '<json_args>'
  │
  ▼
HTTP POST → WaLiAPI /mcp 端点 (SSE 传输)
  │
  ▼
WaLiAPI 执行知识库操作 → 返回 JSON-RPC 响应
  │
  ▼
Agent 格式化结果 → 回复用户
```

### 搜索模式

| 模式 | 说明 | 适用场景 |
|:---|:---|:---|
| `hybrid`（默认） | 向量 + 关键词混合检索 | 大多数场景，概念性查询 |
| `vector` | 纯语义搜索 | 模糊语义查询 |
| `keyword` | 纯关键词搜索 (FTS5) | 精确代码/标识符查找 |

混合模式最终分数 = `向量分数 × vector_weight + 关键词分数 × keyword_weight`

---

## 📁 项目结构

```
waliapi-rag-skills/
├── SKILL.md                        # 技能定义文件（Agent 读取入口）
├── README.md                       # 本文件
├── LICENSE                         # MIT 许可证
├── config.json                     # MCP 服务地址配置
├── scripts/
│   └── mcp_call.py                 # MCP 调用脚本（封装 JSON-RPC + SSE）
└── references/
    └── mcp-tools-reference.md      # MCP 工具完整参数参考文档
```

---

## ⚙️ 配置说明

### config.json

```json
{
  "mcp_url": "http://127.0.0.1:8777/mcp"
}
```

| 字段 | 说明 | 默认值 |
|:---|:---|:---|
| `mcp_url` | WaLiAPI 的 MCP 服务端点 | `http://127.0.0.1:8777/mcp` |

> 如果 WaLiAPI 运行在非默认端口，请修改 `mcp_url` 中的端口号。

### 支持的文档格式

上传文档时支持以下格式：

| 类型 | 格式 |
|:---|:---|
| 文档 | `.txt` `.md` `.pdf` `.docx` `.doc` `.pptx` `.xlsx` `.csv` `.json` `.html` |
| 代码 | `.rs` `.py` `.js` `.ts` `.go` `.java` `.c` `.cpp` `.h` `.sh` |
| 配置 | `.yaml` `.yml` `.toml` |

---

## 💡 使用示例

### RAG 问答（最常用）

```
用户：问一下知识库，WaLiAPI 支持哪些渠道类型？

Agent：
  → ask_knowledge_base(question="WaLiAPI 支持哪些渠道类型")
  ← WaLiAPI 支持 10 种渠道类型：OpenAI、DeepSeek、Claude、Gemini...
     来源：readme.md (score: 0.92)
```

### 语义搜索

```
用户：搜索一下协议转换相关的内容

Agent：
  → search_knowledge_base(query="协议转换", search_mode="hybrid", top_k=5)
  ← 5 条匹配片段，按相似度排序...
```

### 上传文档

```
用户：把这份 PDF 上传到知识库

Agent：
  → upload_document(kb_id="xxx", filename="report.pdf", content="<base64>")
  ← 上传成功，后台正在解析和索引...
```

### 批量导入 Git 仓库

```
用户：把这个 Git 仓库导入知识库

Agent：
  → import_source(kb_id="xxx", source_type="git", repo_url="https://github.com/user/repo")
  ← 导入任务已启动，异步处理中...
```

---

## 🐛 故障排除

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| 连接被拒绝 | WaLiAPI 未运行 | 启动 WaLiAPI 桌面应用 |
| MCP 工具不存在 | WaLiAPI 版本过低 | 升级到 v0.1.1 或更高版本 |
| 知识库为空 | 未创建知识库 | 在 WaLiAPI 中创建知识库 |
| embedding 失败 | 无可用 embedding 渠道 | 配置支持 embedding 的渠道（如 OpenAI） |
| RAG 回答失败 | 无可用 chat 渠道 | 配置支持 chat 的渠道 |
| 搜索无结果 | 关键词不匹配或知识库为空 | 调整搜索词，或先上传文档 |
| Python 脚本报错 | 缺少 requests 库 | `pip install requests` |

---

## 📄 License

[MIT](./LICENSE)

---

## 🔗 相关链接

- **WaLiAPI**（配套软件）：[https://github.com/fuzhengwei/WaLiAPI](https://github.com/fuzhengwei/WaLiAPI)
- **MCP 协议规范**：[https://modelcontextprotocol.io](https://modelcontextprotocol.io)

---

<div align="center">
  <sub>Built with ❤️ for the WaLiAPI ecosystem</sub>
</div>
