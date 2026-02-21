#!/usr/bin/env python3
"""
Issue 广播系统
根据 Agent 订阅配置，将 open Issues 匹配给合适的 Agent

用法:
  python3 broadcast.py              # 广播所有 open Issues
  python3 broadcast.py --json       # JSON 输出
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 导入 Issue 管理器
sys.path.insert(0, str(Path(__file__).parent))
from manager import IssueManager

# Agent 订阅配置 — 根据你的 Agent 团队自定义
# 标签或优先级匹配任一即推送
AGENT_SUBSCRIPTIONS = {
    "analyst": {
        "labels": ["bug", "performance", "analysis", "enhancement", "architecture"],
        "priority": ["P0", "P1"],
        "description": "深度分析、架构设计"
    },
    "writer": {
        "labels": ["docs", "writing", "tutorial", "content"],
        "priority": ["P1", "P2"],
        "description": "中文写作、教程、文档"
    },
    "discovery": {
        "labels": ["research", "cleanup", "exploration"],
        "priority": ["P2", "P3"],
        "description": "信息收集、搜索、整理"
    }
}


def broadcast(json_output=False):
    """广播 open Issues 给匹配的 Agent"""
    mgr = IssueManager()
    open_issues = mgr.list_issues(status="open")
    
    if not open_issues:
        if not json_output:
            print("✅ 无待处理 Issues")
        return {}
    
    if not json_output:
        print(f"\n📢 广播 {len(open_issues)} 个 open Issues...")
    
    matches = {}
    
    for agent, subs in AGENT_SUBSCRIPTIONS.items():
        matched = []
        for issue in open_issues:
            issue_labels = issue.get("labels", [])
            issue_priority = issue.get("priority", "P2")
            
            label_match = any(l in issue_labels for l in subs.get("labels", []))
            priority_match = issue_priority in subs.get("priority", [])
            
            if label_match or priority_match:
                matched.append(issue)
        
        if matched:
            matches[agent] = matched
            if not json_output:
                print(f"\n  🎯 {agent} ({subs.get('description', '')}): {len(matched)} 个")
                for issue in matched:
                    print(f"     #{issue['id']:03d} [{issue['priority']}] {issue['title']}")
    
    # 未匹配的 Issues
    matched_ids = set()
    for issues in matches.values():
        matched_ids.update(i["id"] for i in issues)
    
    unmatched = [i for i in open_issues if i["id"] not in matched_ids]
    if unmatched and not json_output:
        print(f"\n  ⚠️ 未匹配: {len(unmatched)} 个（需要指挥官手动分配）")
        for issue in unmatched:
            print(f"     #{issue['id']:03d} [{issue['priority']}] {issue['title']}")
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "total_open": len(open_issues),
        "total_matched": len(matched_ids),
        "total_unmatched": len(unmatched),
        "matches": {k: [{"id": i["id"], "title": i["title"], "priority": i["priority"]} for i in v] for k, v in matches.items()},
        "unmatched": [{"id": i["id"], "title": i["title"]} for i in unmatched]
    }
    
    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result


if __name__ == "__main__":
    json_mode = "--json" in sys.argv
    broadcast(json_output=json_mode)
