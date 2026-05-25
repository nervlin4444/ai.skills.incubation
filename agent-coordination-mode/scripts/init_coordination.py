#!/usr/bin/env python3
'''---
title: Coordination Mode Initializer
name: agent-coordination-mode
description: Initializes coordination mode settings and creates success rate tracking file for negotiation expert coordination.
version: v1.3.0
github_repository: nervlin4444/ai.skills.incubation
target_branch: main
updated_at: 2026-05-25T09:26:53+08:00
fixes: []
auth_config:
  provider: none
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/init_coordination.py"
  github_path: "agent-coordination-mode/scripts/init_coordination.py"
---
'''

"""
初始化談判專家協調模式
"""

import os
import json
from datetime import datetime

def init_coordination_mode():
    """初始化協調模式設置"""
    print("初始化談判專家協調模式...")
    
    # 創建成功率追蹤文件
    success_rate_file = os.path.join(
        os.path.expanduser("~"), 
        ".workbuddy", 
        "skills", 
        "negotiation_expert_coordination", 
        "success_rates.json"
    )
    
    initial_data = {
        "created_at": datetime.now().isoformat(),
        "planner_success_rate": 0.0,
        "generator_success_rate": 0.0,
        "evaluator_success_rate": 0.0,
        "collaboration_success_rate": 0.0,
        "execution_history": []
    }
    
    with open(success_rate_file, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f, indent=2, ensure_ascii=False)
    
    print(f"成功率追蹤文件已創建: {success_rate_file}")
    return success_rate_file

if __name__ == "__main__":
    init_coordination_mode()
