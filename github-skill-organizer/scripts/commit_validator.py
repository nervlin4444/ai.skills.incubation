"""
---
title: "Commit Message Validator"
name: "github-skill-organizer"
description: "Validates commit messages against Conventional Commits specification. Used by github-skill-organizer daemon."
version: "v1.1.0"
github_repository: "nervlin4444/ai.skills.incubation"
target_branch: "main"
updated_at: "2026-05-19T19:35:00+08:00"

auth_config:
  provider: "github"
  auth_method: "token"
  token_env_var: "GITHUB_TOKEN"
  env_file_path: "{baseDir}/.env"

file_mapping:
  - local_path: "{baseDir}/scripts/commit_validator.py"
    github_path: "github-skill-organizer/scripts/commit_validator.py"
---
"""

"""
Commit Message Validator for Conventional Commits.
Validates commit messages against the specification used by semantic-release.

Usage:
    python commit_validator.py --message "feat(scorer): add 429-aware rating"
    python commit_validator.py --file /path/to/commit_msg.txt
    python commit_validator.py --batch /path/to/commits.json

Exit codes:
    0 = valid
    1 = invalid (prints specific rejection reason)
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Conventional Commits regex pattern
# Format: <type>(<scope>): <subject>
# Types: feat, fix, chore, docs, test, style, refactor, perf
# Subject: imperative mood, max 50 chars for first line
COMMIT_PATTERN = re.compile(
    r'^(?P<type>feat|fix|chore|docs|test|style|refactor|perf)'
    r'(?P<scope>\([a-z0-9_-]+\))?'
    r'(?P<breaking>!)?: '
    r'(?P<subject>.{1,50})'
    r'$',
    re.MULTILINE
)

# Extended validation for full message (with body)
# Allows body and BREAKING CHANGE footer
FULL_MESSAGE_PATTERN = re.compile(
    r'^(?P<type>feat|fix|chore|docs|test|style|refactor|perf)'
    r'(?P<scope>\([a-z0-9_-]+\))?'
    r'(?P<breaking>!)?: '
    r'(?P<subject>.{1,50})'
    r'(\n\n(?P<body>[\s\S]*?))?'
    r'(\n\n(?P<footer>BREAKING CHANGE[\s\S]*?))?'
    r'$'
)

VALID_TYPES = {'feat', 'fix', 'chore', 'docs', 'test', 'style', 'refactor', 'perf'}
MAX_SUBJECT_LENGTH = 50
MAX_BODY_LINE_LENGTH = 72


def validate_single_line(subject: str) -> tuple[bool, str]:
    """Validate a single-line commit subject."""
    match = COMMIT_PATTERN.match(subject)
    if not match:
        # Determine specific error
        if not any(subject.startswith(t) for t in VALID_TYPES):
            return False, f"Invalid type. Must be one of: {', '.join(sorted(VALID_TYPES))}"

        if ':' not in subject:
            return False, "Missing colon separator after type/scope. Format: <type>: <subject>"

        parts = subject.split(':', 1)
        type_part = parts[0]

        # Check scope format
        if '(' in type_part:
            scope_match = re.match(r'^[a-z]+\([a-z0-9_-]+\)$', type_part)
            if not scope_match:
                return False, "Invalid scope format. Use lowercase letters, numbers, hyphens, underscores only."

        subject_text = parts[1].strip() if len(parts) > 1 else ""
        if not subject_text:
            return False, "Empty subject after colon."

        if len(subject) > MAX_SUBJECT_LENGTH:
            return False, f"Subject too long ({len(subject)} chars, max {MAX_SUBJECT_LENGTH})."

        if subject_text.endswith('.'):
            return False, "Subject should not end with a period."

        if subject_text[0:1].isupper():
            return False, "Subject should start with lowercase (imperative mood)."

        return False, "Format error. Expected: <type>(<scope>): <imperative-description>"

    # Additional checks even if regex passes
    subject_text = match.group('subject')
    if subject_text.endswith('.'):
        return False, "Subject should not end with a period."
    if subject_text[0:1].isupper():
        return False, "Subject should start with lowercase (imperative mood)."

    return True, "Valid"


def validate_full_message(message: str) -> tuple[bool, str, dict]:
    """Validate a full commit message including body and footer."""
    lines = message.strip().split('\n')
    if not lines:
        return False, "Empty message", {}

    subject = lines[0]
    valid, reason = validate_single_line(subject)
    if not valid:
        return False, reason, {}

    # Check body line lengths
    if len(lines) > 1:
        body_started = False
        for i, line in enumerate(lines[1:], start=2):
            if line.strip() == '':
                body_started = True
                continue
            if body_started and len(line) > MAX_BODY_LINE_LENGTH:
                return False, f"Body line {i} too long ({len(line)} chars, max {MAX_BODY_LINE_LENGTH}).", {}

    # Parse components
    match = FULL_MESSAGE_PATTERN.match(message.strip())
    result = {
        'type': match.group('type') if match else None,
        'scope': match.group('scope').strip('()') if match and match.group('scope') else None,
        'breaking': bool(match.group('breaking')) if match else False,
        'subject': match.group('subject') if match else None,
        'has_body': bool(match.group('body')) if match else False,
        'has_footer': bool(match.group('footer')) if match else False,
    }

    return True, "Valid", result


def validate_batch(json_path: str) -> tuple[int, int, list]:
    """Validate a batch of commit messages from JSON file."""
    path = Path(json_path)
    if not path.exists():
        print(f"[ERROR] File not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    commits = data.get('commits', []) if isinstance(data, dict) else data
    valid_count = 0
    invalid_count = 0
    results = []

    for item in commits:
        msg = item.get('message', '') if isinstance(item, dict) else str(item)
        valid, reason, parsed = validate_full_message(msg)

        result = {
            'message': msg[:80] + '...' if len(msg) > 80 else msg,
            'valid': valid,
            'reason': reason if not valid else None,
            'parsed': parsed if valid else None
        }
        results.append(result)

        if valid:
            valid_count += 1
        else:
            invalid_count += 1

    return valid_count, invalid_count, results


def main():
    parser = argparse.ArgumentParser(
        description='Validate commit messages against Conventional Commits specification.'
    )
    parser.add_argument('--message', '-m', type=str, help='Single commit message to validate')
    parser.add_argument('--file', '-f', type=str, help='File containing commit message')
    parser.add_argument('--batch', '-b', type=str, help='JSON file containing batch of commit messages')
    parser.add_argument('--json', '-j', action='store_true', help='Output result as JSON')

    args = parser.parse_args()

    if args.message:
        valid, reason, parsed = validate_full_message(args.message)

        if args.json:
            output = {
                'valid': valid,
                'reason': reason if not valid else None,
                'parsed': parsed if valid else None
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            if valid:
                print(f"[VALID] {parsed['type']}{f'({parsed["scope"]})' if parsed['scope'] else ''}: {parsed['subject']}")
                if parsed.get('breaking'):
                    print("[BREAKING CHANGE] This commit will trigger a MAJOR version bump.")
            else:
                print(f"[INVALID] {reason}")

        sys.exit(0 if valid else 1)

    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"[ERROR] File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

        with open(path, 'r', encoding='utf-8') as f:
            message = f.read()

        valid, reason, parsed = validate_full_message(message)

        if args.json:
            output = {
                'valid': valid,
                'reason': reason if not valid else None,
                'parsed': parsed if valid else None
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            if valid:
                print(f"[VALID] {parsed['type']}{f'({parsed["scope"]})' if parsed['scope'] else ''}: {parsed['subject']}")
            else:
                print(f"[INVALID] {reason}")

        sys.exit(0 if valid else 1)

    elif args.batch:
        valid_count, invalid_count, results = validate_batch(args.batch)

        if args.json:
            print(json.dumps({
                'summary': {
                    'total': valid_count + invalid_count,
                    'valid': valid_count,
                    'invalid': invalid_count
                },
                'results': results
            }, ensure_ascii=False, indent=2))
        else:
            print(f"Batch validation: {valid_count} valid, {invalid_count} invalid (total: {valid_count + invalid_count})")
            for r in results:
                status = "✓" if r['valid'] else "✗"
                print(f"  {status} {r['message']}")
                if not r['valid']:
                    print(f"      → {r['reason']}")

        sys.exit(0 if invalid_count == 0 else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
