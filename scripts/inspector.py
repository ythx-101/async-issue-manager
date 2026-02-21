#!/usr/bin/env python3
"""
日常巡查系统 — 自动发现问题，创建 Issue

检查项：
  1. 代码中的 not-implemented stub
  2. 文档与代码不同步
  3. 30 天未修改的 Skills
  4. MEMORY.md 过大（>10KB）

用法:
  python3 inspector.py              # 运行全部检查
  python3 inspector.py --dry-run    # 只检查不建 Issue
  python3 inspector.py --json       # JSON 输出
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# 导入 Issue 管理器
sys.path.insert(0, str(Path(__file__).parent))
from manager import IssueManager, find_workspace

WORKSPACE = find_workspace()


class Inspector:
    def __init__(self, dry_run=False):
        self.issues = []
        self.timestamp = datetime.now().isoformat()
        self.dry_run = dry_run
    
    def check_not_implemented(self):
        """检查代码中的 not-implemented stub"""
        print("🔍 检查 not-implemented stubs...")
        
        stub_files = []
        for pattern in ["scripts/**/*.py", "scripts/**/*.sh"]:
            for script in WORKSPACE.glob(pattern):
                if script.is_file() and script.name not in ("inspector.py", "daily_check.py"):
                    try:
                        content = script.read_text(encoding='utf-8')
                        if "not_implemented" in content.lower() or "todo:" in content.lower():
                            stub_files.append(str(script.relative_to(WORKSPACE)))
                    except (UnicodeDecodeError, IOError):
                        pass
        
        if stub_files:
            self.issues.append({
                "priority": "P1",
                "title": f"实现 {len(stub_files)} 个未完成功能",
                "body": f"以下文件包含未实现的 stub:\n\n" + "\n".join(f"- `{f}`" for f in stub_files),
                "labels": ["enhancement"]
            })
    
    def check_docs_sync(self):
        """检查文档是否和代码同步"""
        print("🔍 检查文档同步...")
        
        # 检查 TOOLS.md 引用的文件是否存在
        tools_md = WORKSPACE / "TOOLS.md"
        if not tools_md.exists():
            return
        
        import re
        content = tools_md.read_text(encoding='utf-8')
        raw_paths = re.findall(r'`([^`]+\.(?:py|sh|js|ts))`', content)
        
        missing = []
        for p in raw_paths:
            # 跳过带参数的命令
            if ' --' in p or ' -' in p or ' ' in p:
                continue
            full = Path(p) if p.startswith('/') else WORKSPACE / p
            if not full.exists():
                missing.append(p)
        
        if missing:
            self.issues.append({
                "priority": "P2",
                "title": f"TOOLS.md 引用了 {len(missing)} 个不存在的文件",
                "body": "以下引用不存在:\n\n" + "\n".join(f"- `{f}`" for f in missing),
                "labels": ["docs"]
            })
    
    def check_unused_skills(self):
        """检查 30 天未修改的 Skills"""
        print("🔍 检查闲置 Skills...")
        
        skills_dir = WORKSPACE / "skills/our"
        if not skills_dir.exists():
            return
        
        cutoff = datetime.now() - timedelta(days=30)
        unused = []
        
        for d in skills_dir.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                mtime = datetime.fromtimestamp(d.stat().st_mtime)
                if mtime < cutoff:
                    unused.append(d.name)
        
        if unused:
            self.issues.append({
                "priority": "P3",
                "title": f"{len(unused)} 个 Skills 超过 30 天未使用",
                "body": "考虑归档或删除:\n\n" + "\n".join(f"- `skills/our/{s}`" for s in unused),
                "labels": ["cleanup"]
            })
    
    def check_memory_size(self):
        """检查 MEMORY.md 大小"""
        print("🔍 检查 MEMORY.md 大小...")
        
        memory_md = WORKSPACE / "MEMORY.md"
        if not memory_md.exists():
            return
        
        size_kb = memory_md.stat().st_size / 1024
        if size_kb > 10:
            self.issues.append({
                "priority": "P2",
                "title": f"MEMORY.md 过大 ({size_kb:.1f} KB)",
                "body": f"当前 {size_kb:.1f} KB，建议精简到 10 KB 以下。",
                "labels": ["cleanup", "performance"]
            })
    
    def run(self):
        """运行全部检查"""
        print(f"{'='*50}")
        print(f"🔍 巡查 @ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*50}")
        
        self.check_not_implemented()
        self.check_docs_sync()
        self.check_unused_skills()
        self.check_memory_size()
        
        # 创建 Issues（除非 dry-run）
        created = []
        if self.issues and not self.dry_run:
            mgr = IssueManager()
            # 获取已有标题，避免重复
            existing = set()
            for status in ["open", "in-progress", "closed"]:
                for i in mgr.list_issues(status=status):
                    existing.add(i["title"])
            
            for issue in self.issues:
                if issue["title"] in existing:
                    print(f"  ⏭️ 跳过（已存在）: {issue['title']}")
                    continue
                created.append(mgr.create(
                    title=issue["title"],
                    body=issue["body"],
                    priority=issue["priority"],
                    labels=issue["labels"]
                ))
        
        print(f"\n📊 发现 {len(self.issues)} 个问题，新建 {len(created)} 个 Issue")
        
        return {
            "timestamp": self.timestamp,
            "issues_found": len(self.issues),
            "issues_created": len(created),
            "issues": self.issues
        }


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    json_mode = "--json" in sys.argv
    
    inspector = Inspector(dry_run=dry_run)
    result = inspector.run()
    
    if json_mode:
        print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
    
    sys.exit(1 if result["issues_found"] > 0 else 0)
