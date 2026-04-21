"""
Rule-based commit analyzer — classifies commits without requiring an AI API key.

Analyzes commit message, file changes, and diff patterns to produce:
  - change_type: feature/bugfix/refactor/test/docs/config/chore/security/performance
  - complexity_score: 0-100
  - risk_score: 0-100
  - message_alignment_score: 0-100
  - test_presence: bool
  - confidence: 0-1
"""

import re
import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# ── Change type detection patterns ──────────────────────────

CHANGE_TYPE_PATTERNS = {
    "security": [
        r"\b(security|vulnerab|cve|xss|csrf|inject|auth|authenticat|authori[zs]|secret|credential|token|exploit)\b",
    ],
    "bugfix": [
        r"\b(fix|bug|patch|hotfix|resolve|resolves|closes?|repair|crash|defect|issue|error|problem|fault)\b",
        r"\b(fix[es]*\s*#\d+)\b",
    ],
    "performance": [
        r"\b(performance|perf|optimize|optimi[zs]|speed|fast|slow|cache|lazy|eager|benchmark|profil)\b",
    ],
    "test": [
        r"\b(test|tests|testing|spec|e2e|unittest|pytest|jest|coverage|mock|fixture|assert)\b",
    ],
    "docs": [
        r"\b(doc[s]?|document|readme|changelog|contributing|license|comment|typo|spel|grammar)\b",
    ],
    "refactor": [
        r"\b(refactor|restructur|reorgani[zs]|clean|cleanup|simplif|extract|rename|move|rewrite|moderniz|deprecat)\b",
    ],
    "config": [
        r"\b(config|configuration|ci|cd|ci\/cd|workflow|pipeline|docker|deploy|build|makefile|setup|infra|dependenc|deps|upgrade|bump|version)\b",
    ],
    "feature": [
        r"\b(add|feat|feature|implement|new|introduc|creat|support|enabl|allow)\b",
    ],
    "chore": [
        r"\b(chore|housekeep|maintenance|misc|minor|trivial|format|lint|style|indent|whitespace)\b",
    ],
}

# File extension categories
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb",
    ".php", ".c", ".cpp", ".h", ".cs", ".swift", ".kt", ".scala", ".sql",
}
TEST_EXTENSIONS_PATTERN = re.compile(
    r"(test_|_test\.|\.test\.|\.spec\.|tests/|__tests__|spec/)",
    re.IGNORECASE,
)
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc", ".html", ".css"}
CONFIG_EXTENSIONS = {
    ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env",
    ".lock", ".dockerfile", ".dockerignore",
}
GENERATED_PATTERNS = re.compile(
    r"(package-lock\.json|yarn\.lock|Pipfile\.lock|poetry\.lock|"
    r"\.min\.|\.map$|__pycache__|\.pyc$|dist/|build/|node_modules/|"
    r"\.generated\.|\.g\.|\.pb\.go|migrations/)",
    re.IGNORECASE,
)


@dataclass
class AnalysisResult:
    """Structured output matching ai_commit_analysis schema."""
    change_type: str
    summary: str
    complexity_score: int
    risk_score: int
    message_alignment_score: int
    test_presence: bool
    confidence: float
    notes: list[str]


def analyze_commit(
    message: str,
    files: list[dict],
    additions: int = 0,
    deletions: int = 0,
    is_merge: bool = False,
) -> AnalysisResult:
    """
    Analyze a commit using rule-based heuristics.

    Args:
        message: Commit message text
        files: List of dicts with keys: filename, status, additions, deletions, patch, is_generated, is_lockfile
        additions: Total additions
        deletions: Total deletions
        is_merge: Whether this is a merge commit
    """
    msg = (message or "").strip()
    msg_lower = msg.lower()
    first_line = msg.split("\n")[0] if msg else ""

    # ── 1. Detect change type ────────────────────────────────
    change_type = _detect_change_type(msg_lower, files, is_merge)

    # ── 2. Generate summary ──────────────────────────────────
    summary = _generate_summary(first_line, change_type, files, additions, deletions)

    # ── 3. Complexity score ──────────────────────────────────
    complexity = _calc_complexity(files, additions, deletions)

    # ── 4. Risk score ────────────────────────────────────────
    risk = _calc_risk(files, additions, deletions, change_type, is_merge)

    # ── 5. Message alignment ────────────────────────────────
    alignment = _calc_message_alignment(msg, files, change_type, additions, deletions)

    # ── 6. Test presence ─────────────────────────────────────
    test_present = _detect_test_presence(files)

    # ── 7. Confidence ────────────────────────────────────────
    confidence = _calc_confidence(msg, files, additions, deletions)

    # ── 8. Notes ─────────────────────────────────────────────
    notes = _generate_notes(
        change_type, complexity, risk, alignment,
        test_present, files, additions, deletions, is_merge,
    )

    return AnalysisResult(
        change_type=change_type,
        summary=summary,
        complexity_score=complexity,
        risk_score=risk,
        message_alignment_score=alignment,
        test_presence=test_present,
        confidence=round(confidence, 2),
        notes=notes,
    )


# ── Change Type Detection ────────────────────────────────────

def _detect_change_type(msg: str, files: list[dict], is_merge: bool) -> str:
    if is_merge:
        return "chore"

    # Check conventional commit prefix
    conv_match = re.match(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)\b", msg)
    if conv_match:
        prefix = conv_match.group(1)
        conv_map = {
            "feat": "feature", "fix": "bugfix", "docs": "docs",
            "style": "chore", "refactor": "refactor", "perf": "performance",
            "test": "test", "build": "config", "ci": "config",
            "chore": "chore", "revert": "bugfix",
        }
        return conv_map.get(prefix, "chore")

    # Check file-based classification
    file_type = _classify_by_files(files)
    if file_type:
        return file_type

    # Pattern matching on message
    for change_type, patterns in CHANGE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, msg, re.IGNORECASE):
                return change_type

    return "feature"  # default assumption


def _classify_by_files(files: list[dict]) -> Optional[str]:
    """Classify based on which files were changed."""
    if not files:
        return None

    test_files = 0
    doc_files = 0
    config_files = 0
    code_files = 0

    for f in files:
        fn = (f.get("filename") or "").lower()
        if TEST_EXTENSIONS_PATTERN.search(fn):
            test_files += 1
        elif any(fn.endswith(e) for e in DOC_EXTENSIONS):
            doc_files += 1
        elif any(fn.endswith(e) for e in CONFIG_EXTENSIONS) or fn in {"dockerfile", "makefile", ".gitignore"}:
            config_files += 1
        elif any(fn.endswith(e) for e in CODE_EXTENSIONS):
            code_files += 1

    total = len(files)
    if total == 0:
        return None

    # If 80%+ of files are test files → test
    if test_files / total >= 0.8:
        return "test"
    # If 80%+ of files are docs → docs
    if doc_files / total >= 0.8:
        return "docs"
    # If 80%+ of files are config → config
    if config_files / total >= 0.8:
        return "config"

    return None


# ── Summary Generation ───────────────────────────────────────

def _generate_summary(first_line: str, change_type: str, files: list[dict], add: int, del_: int) -> str:
    """Generate a human-readable summary."""
    if first_line and len(first_line) >= 10:
        base = first_line[:200]
    else:
        file_names = [f.get("filename", "").split("/")[-1] for f in files[:3]]
        if file_names:
            base = f"{change_type}: changes to {', '.join(file_names)}"
        else:
            base = f"{change_type}: code changes (+{add}/-{del_})"

    return base


# ── Complexity Score ─────────────────────────────────────────

def _calc_complexity(files: list[dict], additions: int, deletions: int) -> int:
    """
    Complexity based on: total changes, file count, file diversity, patch patterns.
    0-100 scale.
    """
    total_lines = additions + deletions
    file_count = len(files)

    # Base from total lines changed
    if total_lines <= 10:
        line_score = 5
    elif total_lines <= 50:
        line_score = 15
    elif total_lines <= 200:
        line_score = 30
    elif total_lines <= 500:
        line_score = 50
    elif total_lines <= 1000:
        line_score = 70
    else:
        line_score = 85

    # File diversity bonus
    if file_count <= 1:
        file_bonus = 0
    elif file_count <= 3:
        file_bonus = 5
    elif file_count <= 10:
        file_bonus = 15
    else:
        file_bonus = 25

    # Unique directories
    dirs = set()
    for f in files:
        fn = f.get("filename", "")
        parts = fn.split("/")
        if len(parts) > 1:
            dirs.add(parts[0])
    dir_bonus = min(15, len(dirs) * 3)

    return min(100, line_score + file_bonus + dir_bonus)


# ── Risk Score ───────────────────────────────────────────────

def _calc_risk(files: list[dict], additions: int, deletions: int, change_type: str, is_merge: bool) -> int:
    """
    Risk based on: file sensitivity, deletion ratio, change size, missing tests.
    0-100 scale.
    """
    risk = 0

    # Merge commits are lower risk (already reviewed)
    if is_merge:
        return 10

    # Large changes are riskier
    total = additions + deletions
    if total > 1000:
        risk += 30
    elif total > 500:
        risk += 20
    elif total > 200:
        risk += 10

    # High deletion ratio
    if total > 0 and deletions / total > 0.7:
        risk += 15

    # Sensitive files
    sensitive_patterns = [
        r"(auth|security|password|secret|token|credential|encrypt|ssl|cert)",
        r"(migration|schema|database|model)",
        r"(config|\.env|settings|deploy)",
        r"(main\.py|app\.py|index\.|server\.)",
    ]
    for f in files:
        fn = (f.get("filename") or "").lower()
        for pat in sensitive_patterns:
            if re.search(pat, fn):
                risk += 5
                break

    # Security-related changes
    if change_type == "security":
        risk += 20

    # No test changes with code changes
    has_tests = any(TEST_EXTENSIONS_PATTERN.search(f.get("filename", "")) for f in files)
    has_code = any(
        any((f.get("filename") or "").endswith(e) for e in CODE_EXTENSIONS)
        for f in files
    )
    if has_code and not has_tests and total > 50:
        risk += 10

    return min(100, risk)


# ── Message Alignment Score ──────────────────────────────────

def _calc_message_alignment(msg: str, files: list[dict], change_type: str, add: int, del_: int) -> int:
    """
    How well the commit message describes the actual changes.
    0-100 scale.
    """
    if not msg:
        return 0

    first_line = msg.split("\n")[0]
    score = 0

    # 1. Message length quality
    if len(first_line) >= 20:
        score += 25
    elif len(first_line) >= 10:
        score += 15
    elif len(first_line) >= 5:
        score += 5

    # 2. Not a generic/lazy message
    lazy_patterns = [
        r"^(update|fix|changes?|wip|tmp|todo|stuff|misc|asdf|test)$",
        r"^(initial commit|first commit|commit|save|push|upload)$",
    ]
    is_lazy = any(re.match(p, first_line.strip(), re.IGNORECASE) for p in lazy_patterns)
    if not is_lazy:
        score += 20
    else:
        score -= 10

    # 3. Has body/description
    lines = msg.strip().split("\n")
    if len(lines) >= 3:
        score += 15
    elif len(lines) >= 2:
        score += 5

    # 4. Mentions files/areas affected
    file_parts = set()
    for f in files:
        fn = f.get("filename", "")
        parts = fn.split("/")
        file_parts.update(p.lower() for p in parts)
    msg_words = set(re.findall(r"\w+", msg.lower()))
    overlap = file_parts & msg_words
    if overlap:
        score += min(20, len(overlap) * 5)

    # 5. Conventional commit format bonus
    if re.match(r"^(feat|fix|docs|refactor|perf|test|build|ci|chore)\b", first_line.lower()):
        score += 10

    # 6. References issue/PR
    if re.search(r"#\d+", msg):
        score += 10

    return max(0, min(100, score))


# ── Test Presence ────────────────────────────────────────────

def _detect_test_presence(files: list[dict]) -> bool:
    """Check if any test files were added or modified."""
    for f in files:
        fn = f.get("filename", "")
        if TEST_EXTENSIONS_PATTERN.search(fn):
            return True
    return False


# ── Confidence ───────────────────────────────────────────────

def _calc_confidence(msg: str, files: list[dict], additions: int, deletions: int) -> float:
    """
    How confident we are in the analysis.
    0.0 - 1.0 scale.
    """
    conf = 0.5  # base

    # Better data = higher confidence
    if msg and len(msg) >= 10:
        conf += 0.1
    if files:
        conf += 0.1
    if additions + deletions > 0:
        conf += 0.1

    # Patches available = much higher confidence
    has_patches = any(f.get("patch") for f in files)
    if has_patches:
        conf += 0.15

    # Multiple signals align = higher confidence
    if msg and files and (additions + deletions) > 0:
        conf += 0.05

    return min(1.0, conf)


# ── Notes Generation ─────────────────────────────────────────

def _generate_notes(
    change_type: str, complexity: int, risk: int, alignment: int,
    test_present: bool, files: list[dict], add: int, del_: int, is_merge: bool,
) -> list[str]:
    """Generate insights about the commit."""
    notes = []

    if is_merge:
        notes.append("Merge commit — risk reduced as changes were likely reviewed.")

    if complexity >= 70:
        notes.append(f"High complexity ({complexity}/100): large, multi-file change.")
    elif complexity <= 15:
        notes.append(f"Low complexity ({complexity}/100): small, focused change.")

    if risk >= 50:
        notes.append(f"Elevated risk ({risk}/100): consider extra review.")

    if alignment <= 30 and not is_merge:
        notes.append("Poor commit message — does not describe the change well.")
    elif alignment >= 75:
        notes.append("Good commit message — clearly describes the change.")

    # Generated/lockfile dominance
    gen_count = sum(1 for f in files if f.get("is_generated") or f.get("is_lockfile"))
    if gen_count > 0 and gen_count == len(files):
        notes.append("All files are generated/lockfiles — low scoring weight recommended.")
    elif gen_count > len(files) * 0.5:
        notes.append(f"{gen_count}/{len(files)} files are generated/lockfiles.")

    if change_type == "test" or test_present:
        notes.append("Includes test changes — positive signal for quality.")

    total = add + del_
    if total > 0 and del_ / total > 0.8:
        notes.append("Mostly deletions — likely cleanup or removal.")

    return notes[:5]
