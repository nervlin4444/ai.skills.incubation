#!/usr/bin/env python3
"""
---
title: "Project Agent Board"
name: "github-restful-api-connector"
description: "Agent 狀態看板管理：創建卡片、更新欄位、跨欄移動"
version: "0.1.0"
github_repository: "nervlin4444/ai.skills.devops"
target_branch: "main"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/github_project_agent.py"
    github_path: "/github-restful-api-connector/scripts/github_project_agent.py"
---
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

# 載入核心連接器
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))
from github_restful_core import graphql_query, rest_request, load_env, logger

# ============================================
# 配置
# ============================================
VERSION = "0.1.0"
CACHE_DIR = Path.home() / ".workbuddy" / "skills" / "github-restful-api-connector" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
FIELD_CACHE_PATH = CACHE_DIR / "field.cache.json"

# ============================================
# 快取管理
# ============================================
def load_field_cache() -> dict:
    if FIELD_CACHE_PATH.exists():
        with open(FIELD_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_field_cache(data: dict):
    with open(FIELD_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================
# 核心函數
# ============================================
def get_project_id(owner: str, project_number: int) -> str:
    """取得 Project node_id。"""
    q = """
    query($owner: String!, $number: Int!) {
      userOrOrganization(login: $owner) {
        projectV2(number: $number) { id }
      }
    }
    """
    result = graphql_query(q, {"owner": owner, "number": project_number})
    proj = result.get("userOrOrganization", {}).get("projectV2")
    if not proj:
        raise RuntimeError(f"Project #{project_number} not found for owner '{owner}'")
    return proj["id"]

def cache_project_fields(project_id: str) -> dict:
    """
    快取 Project 全部欄位 ID 與選項 ID。
    寫入 field.cache.json。
    """
    q = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2Field { id name }
              ... on ProjectV2SingleSelectField {
                id name
                options { id name }
              }
              ... on ProjectV2IterationField { id name }
            }
          }
        }
      }
    }
    """
    result = graphql_query(q, {"projectId": project_id})
    fields = result.get("node", {}).get("fields", {}).get("nodes", [])
    cache = {}
    for f in fields:
        fname = f.get("name", "").lower()
        cache[fname] = {"id": f.get("id"), "type": "text"}
        if "options" in f:
            cache[fname]["type"] = "single_select"
            cache[fname]["options"] = {o["name"].lower(): o["id"] for o in f["options"]}
    save_field_cache(cache)
    logger.info(f"Cached {len(cache)} fields for project {project_id}")
    return cache

def create_card(project_id: str, title: str, body: str = "") -> str:
    """
    在 Project 的 Todo 欄位創建 Draft Issue 卡片。
    返回卡片 node_id。
    """
    m = """
    mutation($projectId: ID!, $title: String!, $body: String) {
      addProjectV2DraftIssue(input: {
        projectId: $projectId
        title: $title
        body: $body
      }) {
        projectItem { id }
      }
    }
    """
    result = graphql_query(m, {"projectId": project_id, "title": title, "body": body})
    item = result.get("addProjectV2DraftIssue", {}).get("projectItem")
    if not item:
        raise RuntimeError("Failed to create card")
    card_id = item["id"]
    logger.info(f"Created card: {card_id} — {title}")
    return card_id

def move_card(project_id: str, card_id: str, target_status: str, cache: dict = None) -> bool:
    """
    將卡片移至目標欄位。
    target_status 限於 todo / in progress / done / failed。
    """
    if cache is None:
        cache = load_field_cache()
    status_field = cache.get("status")
    if not status_field:
        raise RuntimeError("Status field not found in cache. Run --cache-fields first.")
    option_id = status_field.get("options", {}).get(target_status.lower())
    if not option_id:
        raise RuntimeError(f"Status option '{target_status}' not found.")
    m = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId
        itemId: $itemId
        fieldId: $fieldId
        value: { singleSelectOptionId: $optionId }
      }) {
        projectV2Item { id }
      }
    }
    """
    graphql_query(m, {
        "projectId": project_id,
        "itemId": card_id,
        "fieldId": status_field["id"],
        "optionId": option_id,
    })
    logger.info(f"Moved card {card_id} to '{target_status}'")
    return True

def update_card_field(project_id: str, card_id: str, field_name: str, value: str, cache: dict = None) -> bool:
    """
    更新卡片自定義欄位。
    目前僅支援 text / number 類型欄位。
    """
    if cache is None:
        cache = load_field_cache()
    field = cache.get(field_name.lower())
    if not field:
        raise RuntimeError(f"Field '{field_name}' not found in cache.")
    field_id = field["id"]
    field_type = field.get("type", "text")
    if field_type == "single_select":
        option_id = field.get("options", {}).get(value.lower())
        if not option_id:
            raise RuntimeError(f"Option '{value}' not found for field '{field_name}'")
        m = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { singleSelectOptionId: $optionId }
          }) {
            projectV2Item { id }
          }
        }
        """
        graphql_query(m, {
            "projectId": project_id, "itemId": card_id,
            "fieldId": field_id, "optionId": option_id
        })
    else:
        # Assume text/number
        m = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { text: $value }
          }) {
            projectV2Item { id }
          }
        }
        """
        graphql_query(m, {
            "projectId": project_id, "itemId": card_id,
            "fieldId": field_id, "value": str(value)
        })
    logger.info(f"Updated card {card_id} field '{field_name}' = '{value}'")
    return True

def list_cards_by_status(project_id: str, status: str, owner: str, project_number: int, cache: dict = None) -> list:
    """
    讀取指定欄位全部卡片。
    返回卡片列表，每項含 id、title、current_status。
    """
    if cache is None:
        cache = load_field_cache()
    q = """
    query($owner: String!, $number: Int!) {
      userOrOrganization(login: $owner) {
        projectV2(number: $number) {
          items(first: 100) {
            nodes {
              id
              content {
                ... on DraftIssue { title body }
                ... on Issue { title number }
                ... on PullRequest { title number }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    field { name }
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    result = graphql_query(q, {"owner": owner, "number": project_number})
    items = result.get("userOrOrganization", {}).get("projectV2", {}).get("items", {}).get("nodes", [])
    cards = []
    for item in items:
        current_status = ""
        for fv in item.get("fieldValues", {}).get("nodes", []):
            if fv.get("field", {}).get("name", "").lower() == "status":
                current_status = fv.get("name", "").lower()
        if current_status == status.lower():
            content = item.get("content", {})
            cards.append({
                "id": item["id"],
                "title": content.get("title", "Untitled"),
                "body": content.get("body", ""),
                "status": current_status,
            })
    logger.info(f"Listed {len(cards)} cards in status '{status}'")
    return cards

# ============================================
# CLI 入口
# ============================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Project Agent Board — F-002")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--cache-fields", action="store_true", help="Cache project field IDs")
    parser.add_argument("--create-card", action="store_true", help="Create a new card")
    parser.add_argument("--title", type=str, default="")
    parser.add_argument("--body", type=str, default="")
    parser.add_argument("--agent-name", type=str, default="")
    parser.add_argument("--move-card", action="store_true", help="Move card to target status")
    parser.add_argument("--card-id", type=str, default="")
    parser.add_argument("--target-status", type=str, default="", choices=["Todo", "In Progress", "Done", "Failed"])
    parser.add_argument("--update-field", action="store_true", help="Update a custom field")
    parser.add_argument("--field-name", type=str, default="")
    parser.add_argument("--field-value", type=str, default="")
    parser.add_argument("--list-cards", action="store_true", help="List cards by status")
    parser.add_argument("--status", type=str, default="", choices=["Todo", "In Progress", "Done", "Failed"])
    args = parser.parse_args()

    if args.version:
        print(f"github_project_agent.py v{VERSION}")
        return

    load_env()
    owner = os.environ.get("GITHUB_OWNER", "").strip()
    project_number = int(os.environ.get("GITHUB_PROJECT_NUMBER", "0").strip() or 0)
    if not owner or not project_number:
        logger.error("GITHUB_OWNER and GITHUB_PROJECT_NUMBER required.")
        sys.exit(1)

    project_id = get_project_id(owner, project_number)

    if args.cache_fields:
        cache_project_fields(project_id)
        return

    cache = load_field_cache()
    if not cache:
        logger.info("Field cache empty. Caching now...")
        cache = cache_project_fields(project_id)

    if args.create_card:
        if not args.title:
            logger.error("--title required for --create-card")
            sys.exit(1)
        card_id = create_card(project_id, args.title, args.body)
        if args.agent_name:
            update_card_field(project_id, card_id, "agent_name", args.agent_name, cache)
        # Move to Todo by default
        move_card(project_id, card_id, "Todo", cache)
        print(f"Created card: {card_id}")
        return

    if args.move_card:
        if not args.card_id or not args.target_status:
            logger.error("--card-id and --target-status required")
            sys.exit(1)
        move_card(project_id, args.card_id, args.target_status, cache)
        print(f"Moved card {args.card_id} to {args.target_status}")
        return

    if args.update_field:
        if not args.card_id or not args.field_name or not args.field_value:
            logger.error("--card-id, --field-name, --field-value required")
            sys.exit(1)
        update_card_field(project_id, args.card_id, args.field_name, args.field_value, cache)
        print(f"Updated field {args.field_name}")
        return

    if args.list_cards:
        if not args.status:
            logger.error("--status required for --list-cards")
            sys.exit(1)
        cards = list_cards_by_status(project_id, args.status, owner, project_number, cache)
        print(json.dumps(cards, indent=2, ensure_ascii=False))
        return

    parser.print_help()

if __name__ == "__main__":
    main()
