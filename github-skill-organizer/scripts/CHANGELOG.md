# Scripts Change Log

All modifications to scripts/ files are recorded here.

## 2026-05-17

- Fixed bug in `skill_installer.py`: AttributeError: 'SkillOrganizerConfig' object has no attribute 'main_repo'
  - Modified `_derive_local_path_from_github_path` method to accept optional `repo_name` parameter
  - Updated calls to pass repo name extracted from frontmatter's github_repository
  - This allows proper handling of github_path with repository prefixes

## 2026-05-17

- Initial version of CHANGELOG.md created