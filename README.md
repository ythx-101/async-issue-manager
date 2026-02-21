# 🎯 Async Issue Manager

**上班前丢任务，下班后看结果。** 纯本地异步任务管理系统，让 AI Agent 在你不在线时自动工作。

## 为什么需要这个？

大多数人用 AI Agent 的方式是"坐在电脑前，一问一答"。但如果你是上班族呢？

```
❌ 传统方式：人盯着 Agent 干活，效率 = 你在线的时间
✅ 异步方式：丢任务就走，Agent 自己调度、执行、归档
```

这个系统让你的 Agent 像一个**自动运转的小团队**：

| 角色 | 做什么 |
|------|--------|
| 🦞 指挥官 (Opus) | 判断任务派给谁 |
| 🔬 分析师 (Sonnet) | 深度分析、架构设计 |
| ✍️ 写手 (MiniMax) | 中文写作、教程 |
| 🔍 探索者 (Gemini) | 搜索、信息收集 |
| ⚡ 临时工 (Haiku) | 简单任务 |

## 工作流

```
                    ┌─────────────────┐
                    │  🌅 早上出门前   │
                    │  跟龙虾说几句话  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  📋 自动建 Issue │
                    │  排优先级 + 打标签│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ 🤖 每小时自动调度 │
                    │  Opus 判断派给谁 │
                    └───┬───┬───┬───┬─┘
                        │   │   │   │
                   ┌────▼┐ ┌▼──┐┌▼──┐┌▼────┐
                   │分析师│ │写手││探索││临时工│
                   │Sonnet│ │M2.5││Gem.││Haiku│
                   └──┬───┘ └─┬─┘└─┬─┘└──┬──┘
                      │       │    │     │
                    ┌─▼───────▼────▼─────▼─┐
                    │   ✅ .issues/closed/  │
                    └──────────┬────────────┘
                               │
                    ┌──────────▼────────────┐
                    │   🌙 晚上下班         │
                    │   看结果 → 发推        │
                    └───────────────────────┘
```

旁路还有：
- **🔍 巡查系统**：自动发现代码问题，能修的直接修
- **📦 Git 管理**：纯本地，不依赖外部服务

## 特性

- **纯本地** — `.issues/` 目录 + Git，不依赖 GitHub Issues / Jira / Notion
- **自动巡查** — 每天自动扫描代码问题、文档过期、未使用资源
- **智能调度** — 不是死板规则，指挥官 Agent 根据上下文判断派活
- **自动去重** — 相同问题不会重复建 Issue
- **文档同步检查** — 代码改了文档没更新？自动检测并建 Issue
- **Git 可追溯** — 每个 Issue 的生命周期完整记录

## 快速开始

### 1. 安装

```bash
# 在 OpenClaw 工作区创建目录结构
mkdir -p .issues/{open,in-progress,closed}

# 方式 A: 作为 Skill 安装（推荐）
cp -r async-issue-manager/ <your-workspace>/skills/

# 方式 B: 直接复制脚本到工作区
cp -r async-issue-manager/scripts/* <your-workspace>/scripts/issues/
```

### 2. 创建第一个 Issue

```bash
python3 scripts/manager.py create \
  --title "测试异步任务系统" \
  --body "验证 Issue 创建 → 分配 → 关闭的完整流程" \
  --priority P2 \
  --labels test
```

### 3. 配置 Cron 自动调度

在 OpenClaw 中配置 cron：

```json
{
  "schedule": { "kind": "cron", "expr": "0 * * * *" },
  "payload": { "kind": "systemEvent", "text": "issue-hourly-dispatch" },
  "sessionTarget": "main"
}
```

或使用系统 crontab：

```
0 * * * * cd /workspace && bash scripts/auto-dispatch.sh
```

### 4. 查看结果

```bash
# 看有哪些任务
python3 scripts/manager.py list --status open
python3 scripts/manager.py list --status closed

# 看某个任务详情
python3 scripts/manager.py show 1
```

## 目录结构

```
.issues/                          # Issue 存储
├── open/                         # 待处理
├── in-progress/                  # 进行中
├── closed/                       # 已完成
└── index.json                    # 索引

scripts/
├── manager.py              # Issue CRUD 核心（307行）
├── broadcast.py            # Agent 订阅 & 广播（103行）
├── inspector.py            # 巡查系统（183行）
└── auto-dispatch.sh        # 自动调度入口（47行）
```

总计约 **640 行**代码，纯 Python + Bash，零外部依赖。

## Issue 生命周期

```
创建 → open/ → 分配 → in-progress/ → 完成 → closed/
                                        ↑
                            巡查系统自动创建
```

每次状态变更：
1. 文件从一个目录移动到另一个目录
2. YAML front matter 自动更新
3. `index.json` 同步更新
4. Git commit 记录变更

## 巡查系统详解

巡查系统是这个方案的精华——**Agent 不只执行任务，还能自己发现问题。**

| 检查项 | 描述 | 发现后 |
|--------|------|--------|
| 未实现功能 | 代码中的 `not_implemented` stub | 自动建 Issue |
| 文档过期 | 代码改了，README 没更新 | 自动建 Issue |
| 闲置资源 | 30 天未修改的 Skill | 自动建 Issue |
| 记忆膨胀 | MEMORY.md > 10KB | 自动建 Issue |
| 冥想缺失 | Agent 昨天没产出 | 自动建 Issue |

巡查器（`inspector.py`）内置 4 项检查，可轻松扩展自定义规则。

## 自定义

### 修改 Agent 订阅

编辑 `scripts/broadcast.py` 中的 `AGENT_SUBSCRIPTIONS`：

```python
AGENT_SUBSCRIPTIONS = {
    "your_agent": {
        "labels": ["your-label"],
        "priority": ["P1", "P2"]
    }
}
```

### 添加巡查规则

在 `scripts/inspector.py` 的 `Inspector` 类中添加新方法：

```python
def check_your_custom_rule(self):
    """你的自定义检查"""
    # 检查逻辑...
    if problem_found:
        self.issues.append({
            "type": "warning",
            "priority": "P2",
            "title": "发现问题",
            "body": "问题描述",
            "labels": ["your-label"]
        })
```

然后在 `run()` 方法中调用它。

## 真实数据

这个系统在我们的 OpenClaw 实例上运行了 2 周的成果：

- **35 个 Issue** 被创建（自动 + 手动）
- **30+ 个已关闭**（完成率 > 85%）
- **巡查系统**自动发现并修复了文档过期、代码 stub、资源闲置等问题
- **零外部依赖** — 纯文件系统 + Git

## 灵感来源

- OpenClaw 的 `sessions_spawn` 机制（子 Agent 自动执行）
- steipete 的"人才是瓶颈"哲学（不搞复杂编排，指挥官直接判断）
- GitHub Issues（文件格式借鉴，但不依赖 GitHub 平台）

## License

MIT

## Author

**林月 (@YuLin807)** — [x.com/YuLin807](https://x.com/YuLin807)

---

*人在工位，龙虾在家干活。这才是人机协作该有的样子。*
