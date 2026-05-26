"""Detection rule corpus loader (FR-041)."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class DetectionRule:
    id: str
    name: str
    vulnerability_class: str
    cwe: Optional[str]
    applicable_languages: list[str]
    prompt_template: str
    severity_hint: str = "medium"
    scope: str = "function"


class RuleCorpusLoader:
    def __init__(self, corpus_path: str | Path) -> None:
        self.corpus_path = Path(corpus_path)

    def load(self) -> list[DetectionRule]:
        rules: list[DetectionRule] = []
        if not self.corpus_path.exists():
            return rules
        for rule_file in sorted(self.corpus_path.glob("*.yml")):
            with open(rule_file) as f:
                raw = yaml.safe_load(f)
            if not raw or not all(k in raw for k in ("id", "name", "vulnerability_class", "prompt_template")):
                continue
            rules.append(DetectionRule(
                id=raw["id"],
                name=raw["name"],
                vulnerability_class=raw["vulnerability_class"],
                cwe=raw.get("cwe"),
                applicable_languages=raw.get("applicable_languages", ["python"]),
                prompt_template=raw["prompt_template"],
                severity_hint=raw.get("severity_hint", "medium"),
                scope=raw.get("scope", "function"),
            ))
        return rules
