#!/usr/bin/env python3
"""
本地 Issue 管理器
在 .issues/ 目录下管理 Issues，使用 Git 追踪

用法:
  python3 manager.py create --title "任务标题" --body "描述" --priority P1 --labels bug fix
  python3 manager.py list [--status open|in-progress|closed] [--labels tag1 tag2]
  python3 manager.py show <id>
  python3 manager.py assign <id> <agent_name>
  python3 manager.py close <id> [--resolution "解决说明"]
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 自动检测工作区根目录：优先使用环境变量，否则向上查找 .issues/ 目录
import os
def find_workspace():
    """查找工作区根目录"""
    # 1. 环境变量
    env_ws = os.environ.get("WORKSPACE") or os.environ.get("OPENCLAW_WORKSPACE")
    if env_ws and Path(env_ws).exists():
        return Path(env_ws)
    
    # 2. 向上查找 .issues/ 目录
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".issues").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # 3. 默认当前工作目录
    return Path.cwd()

WORKSPACE = find_workspace()
ISSUES_DIR = WORKSPACE / ".issues"


class IssueManager:
    def __init__(self, workspace=None):
        if workspace:
            self.workspace = Path(workspace)
        else:
            self.workspace = WORKSPACE
        
        self.issues_dir = self.workspace / ".issues"
        self.open_dir = self.issues_dir / "open"
        self.in_progress_dir = self.issues_dir / "in-progress"
        self.closed_dir = self.issues_dir / "closed"
        
        # 确保目录存在
        for d in [self.open_dir, self.in_progress_dir, self.closed_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 索引文件
        self.index_file = self.issues_dir / "index.json"
        self.load_index()
    
    def load_index(self):
        """加载索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.index = {"issues": [], "next_id": 1}
        else:
            self.index = {"issues": [], "next_id": 1}
    
    def save_index(self):
        """保存索引"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def create(self, title, body="", priority="P2", labels=None, assignee=None):
        """创建 Issue"""
        if not title or not title.strip():
            print("❌ 标题不能为空")
            return None
        title = title.strip()
        
        if labels is None:
            labels = []
        
        issue_id = self.index["next_id"]
        self.index["next_id"] += 1
        timestamp = datetime.now().isoformat()
        
        issue = {
            "id": issue_id,
            "title": title,
            "priority": priority,
            "labels": labels if isinstance(labels, list) else [labels],
            "status": "open",
            "assignee": assignee or "unassigned",
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        # 文件名：ID-标题slug（保留中文字符）
        slug = title.lower().replace(" ", "-")
        # 保留字母、数字、中文、日文、韩文、连字符、下划线
        import re
        slug = re.sub(r'[^\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af-]', '', slug)[:50]
        filename = f"{issue_id:03d}-{slug}.md"
        filepath = self.open_dir / filename
        
        # 写入 Issue 文件
        content = f"""---
id: {issue_id}
title: {title}
priority: {priority}
labels: {', '.join(issue['labels'])}
status: open
assignee: {issue['assignee']}
created_at: {timestamp}
updated_at: {timestamp}
---

{body}
"""
        filepath.write_text(content, encoding='utf-8')
        
        # 更新索引
        issue["file"] = str(filepath.relative_to(self.workspace))
        self.index["issues"].append(issue)
        self.save_index()
        
        print(f"✅ Issue #{issue_id} 创建: {title}")
        return issue
    
    def list_issues(self, status="open", labels=None, priority=None, assignee=None):
        """列出 Issues（支持过滤）"""
        results = []
        for issue in self.index["issues"]:
            if status and issue.get("status") != status:
                continue
            if labels and not any(l in issue.get("labels", []) for l in labels):
                continue
            if priority and issue.get("priority") != priority:
                continue
            if assignee and issue.get("assignee") != assignee:
                continue
            results.append(issue)
        return results
    
    def get(self, issue_id):
        """获取单个 Issue 详情"""
        issue = self._find(issue_id)
        if not issue:
            return None
        filepath = self.workspace / issue["file"]
        if filepath.exists():
            issue["content"] = filepath.read_text(encoding='utf-8')
        return issue
    
    def assign(self, issue_id, assignee):
        """分配 Issue 给某个 Agent"""
        issue = self._find(issue_id)
        if not issue:
            print(f"❌ Issue #{issue_id} 不存在")
            return None
        
        old_path = self.workspace / issue["file"]
        new_path = self.in_progress_dir / old_path.name
        
        # 更新文件内容
        if old_path.exists():
            content = old_path.read_text(encoding='utf-8')
            content = content.replace(f"assignee: {issue.get('assignee', 'unassigned')}", f"assignee: {assignee}")
            content = content.replace("status: open", "status: in-progress")
            new_path.write_text(content, encoding='utf-8')
            old_path.unlink()
        
        # 更新索引
        issue["assignee"] = assignee
        issue["status"] = "in-progress"
        issue["updated_at"] = datetime.now().isoformat()
        issue["file"] = str(new_path.relative_to(self.workspace))
        self.save_index()
        
        print(f"✅ Issue #{issue_id} → {assignee}")
        return issue
    
    def close(self, issue_id, resolution=""):
        """关闭 Issue"""
        issue = self._find(issue_id)
        if not issue:
            print(f"❌ Issue #{issue_id} 不存在")
            return None
        
        old_path = self.workspace / issue["file"]
        new_path = self.closed_dir / old_path.name
        
        closed_at = datetime.now().isoformat()
        
        if old_path.exists():
            content = old_path.read_text(encoding='utf-8')
            # 更新状态
            for old_status in ["status: open", "status: in-progress"]:
                content = content.replace(old_status, "status: closed")
            # 追加解决方案
            if resolution:
                content += f"\n\n## 解决方案\n\n{resolution}\n\n关闭时间: {closed_at}\n"
            new_path.write_text(content, encoding='utf-8')
            old_path.unlink()
        
        # 更新索引
        issue["status"] = "closed"
        issue["closed_at"] = closed_at
        issue["resolution"] = resolution
        issue["file"] = str(new_path.relative_to(self.workspace))
        self.save_index()
        
        print(f"✅ Issue #{issue_id} 已关闭")
        return issue
    
    def stats(self):
        """统计概览"""
        total = len(self.index["issues"])
        by_status = {}
        for issue in self.index["issues"]:
            s = issue.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        return {"total": total, "by_status": by_status, "next_id": self.index["next_id"]}
    
    def _find(self, issue_id):
        """按 ID 查找"""
        for issue in self.index["issues"]:
            if issue["id"] == int(issue_id):
                return issue
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="本地 Issue 管理器")
    sub = parser.add_subparsers(dest="cmd")
    
    # create
    p = sub.add_parser("create")
    p.add_argument("--title", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--priority", default="P2")
    p.add_argument("--labels", nargs="+", default=[])
    
    # list
    p = sub.add_parser("list")
    p.add_argument("--status", default="open")
    p.add_argument("--labels", nargs="+")
    p.add_argument("--priority")
    p.add_argument("--assignee")
    
    # show
    p = sub.add_parser("show")
    p.add_argument("issue_id", type=int)
    
    # assign
    p = sub.add_parser("assign")
    p.add_argument("issue_id", type=int)
    p.add_argument("assignee")
    
    # close
    p = sub.add_parser("close")
    p.add_argument("issue_id", type=int)
    p.add_argument("--resolution", default="")
    
    # stats
    sub.add_parser("stats")
    
    args = parser.parse_args()
    mgr = IssueManager()
    
    if args.cmd == "create":
        mgr.create(args.title, args.body, args.priority, args.labels)
    elif args.cmd == "list":
        issues = mgr.list_issues(args.status, args.labels, args.priority, getattr(args, 'assignee', None))
        print(f"\n{'='*50}")
        print(f"📋 {args.status} Issues ({len(issues)})")
        print(f"{'='*50}")
        for i in issues:
            labels_str = ", ".join(i.get("labels", []))
            print(f"  #{i['id']:03d} [{i['priority']}] {i['title']}")
            print(f"        {i['status']} | {i.get('assignee','?')} | {labels_str}")
    elif args.cmd == "show":
        issue = mgr.get(args.issue_id)
        if issue:
            print(issue.get("content", ""))
        else:
            print(f"❌ Issue #{args.issue_id} 不存在")
    elif args.cmd == "assign":
        mgr.assign(args.issue_id, args.assignee)
    elif args.cmd == "close":
        mgr.close(args.issue_id, args.resolution)
    elif args.cmd == "stats":
        s = mgr.stats()
        print(f"\n📊 Issue 统计")
        print(f"  总计: {s['total']} | 下一个 ID: #{s['next_id']}")
        for status, count in s["by_status"].items():
            print(f"  {status}: {count}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
