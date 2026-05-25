'''
---
title: "set_alert.py"
name: "currency-exchange-tracker"
description: "Set, list, deactivate, and delete exchange rate alerts for HKD/CNY and CNY/HKD. Stores alert configuration in assets/exchange_alerts.json."
version: "v2.0.1"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-25T16:45:00+08:00"
fixes: []
auth_config:
  provider: yahoo_finance
  auth_method: none
  token_env_var: ""
  env_file_path: ""
file_mapping:
  local_path: "{baseDir}/scripts/set_alert.py"
  github_path: "currency-exchange-tracker/scripts/set_alert.py"
---
'''

# -*- coding: utf-8 -*-

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
ASSETS_DIR = SCRIPT_DIR.parent / "assets"
ALERTS_FILE = ASSETS_DIR / "exchange_alerts.json"

VALID_CONDITIONS = ["above", "below", "cross-above", "cross-below"]
VALID_DIRECTIONS = ["hkd-to-cny", "cny-to-hkd"]

def ensure_assets_dir():
    """Ensure assets directory exists."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def load_alerts():
    """Load existing alerts."""
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"alerts": []}
    return {"alerts": []}

def save_alerts(data):
    """Save alerts to file."""
    ensure_assets_dir()
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_alert(direction, target, condition, note=None):
    """Add a new exchange rate alert."""
    if direction not in VALID_DIRECTIONS:
        print(f"Error: Invalid direction '{direction}'. Must be one of: {VALID_DIRECTIONS}")
        sys.exit(1)

    if condition not in VALID_CONDITIONS:
        print(f"Error: Invalid condition '{condition}'. Must be one of: {VALID_CONDITIONS}")
        sys.exit(1)

    alerts = load_alerts()

    new_alert = {
        "id": f"alert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "direction": direction,
        "target": float(target),
        "condition": condition,
        "created": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "note": note or ""
    }

    alerts["alerts"].append(new_alert)
    save_alerts(alerts)

    print(f"Alert created successfully")
    print(f"   ID: {new_alert['id']}")
    print(f"   Direction: {direction}")
    print(f"   Target: {target}")
    print(f"   Condition: {condition}")
    if note:
        print(f"   Note: {note}")
    print(f"   Status: Active")

def list_alerts():
    """List all active alerts."""
    alerts = load_alerts()

    if not alerts["alerts"]:
        print("No alerts configured.")
        return

    print(f"Exchange Rate Alerts ({len(alerts['alerts'])} total)")
    print("=" * 60)

    for alert in alerts["alerts"]:
        status = "Active" if alert["active"] else "Inactive"
        print(f"\nID: {alert['id']}")
        print(f"  Direction: {alert['direction']}")
        print(f"  Target: {alert['target']}")
        print(f"  Condition: {alert['condition']}")
        print(f"  Status: {status}")
        print(f"  Created: {alert['created']}")
        if alert.get("note"):
            print(f"  Note: {alert['note']}")

def deactivate_alert(alert_id):
    """Deactivate an alert by ID."""
    alerts = load_alerts()

    for alert in alerts["alerts"]:
        if alert["id"] == alert_id:
            alert["active"] = False
            save_alerts(alerts)
            print(f"Alert {alert_id} deactivated")
            return

    print(f"Alert {alert_id} not found")
    sys.exit(1)

def delete_alert(alert_id):
    """Delete an alert by ID."""
    alerts = load_alerts()

    original_count = len(alerts["alerts"])
    alerts["alerts"] = [a for a in alerts["alerts"] if a["id"] != alert_id]

    if len(alerts["alerts"]) < original_count:
        save_alerts(alerts)
        print(f"Alert {alert_id} deleted")
    else:
        print(f"Alert {alert_id} not found")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Manage exchange rate alerts")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    add_parser = subparsers.add_parser("add", help="Add a new alert")
    add_parser.add_argument("--direction", choices=VALID_DIRECTIONS, required=True)
    add_parser.add_argument("--target", type=float, required=True)
    add_parser.add_argument("--condition", choices=VALID_CONDITIONS, required=True)
    add_parser.add_argument("--note", type=str, help="Optional note")

    list_parser = subparsers.add_parser("list", help="List all alerts")

    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate an alert")
    deactivate_parser.add_argument("id", help="Alert ID")

    delete_parser = subparsers.add_parser("delete", help="Delete an alert")
    delete_parser.add_argument("id", help="Alert ID")

    args = parser.parse_args()

    if args.command == "add":
        add_alert(args.direction, args.target, args.condition, args.note)
    elif args.command == "list":
        list_alerts()
    elif args.command == "deactivate":
        deactivate_alert(args.id)
    elif args.command == "delete":
        delete_alert(args.id)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
