from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

# jsonschema v4 dropped version-specific validator class exports from top-level.
# Use get_validator with metaschema id instead of Draft2020Validator symbol.
try:
    import jsonschema
    from jsonschema.validators import validator_for as _validator_for
except Exception:  # pragma: no cover
    jsonschema = None  # type: ignore
    _validator_for = None  # type: ignore


class ValidationError(Exception):
    """Raised when a dataset fails JSON Schema validation."""
    pass


@dataclass
class SchemaSpec:
    name: str
    path: str
    schema: Optional[Dict[str, Any]] = None


class Validator:
    """
    Strict validator using JSON Schema Draft 2020-12.

    Usage:
      v = Validator(schema_dir="wuxia_battle_simulator/schemas")
      v.load_schemas()
      v.validate("characters", data)
    """

    def __init__(self, schema_dir: str) -> None:
        self.schema_dir = schema_dir
        self._schemas: Dict[str, SchemaSpec] = {}

    @staticmethod
    def _check_schema(schema: Dict[str, Any]) -> None:
        """
        Validate that the provided schema is itself a valid JSON Schema.
        Uses the metaschema advertised by the schema's $schema property.
        """
        if _validator_for is None or jsonschema is None:
            return
        # get appropriate validator class for this schema's metaschema
        validator_cls = _validator_for(schema)  # type: ignore
        # This raises jsonschema.exceptions.SchemaError if invalid
        validator_cls.check_schema(schema)      # type: ignore

    def load_schemas(self) -> None:
        # Known schema files
        mapping = {
            "characters": "characters.schema.json",
            "skills": "skills.schema.json",
            "templates": "templates.schema.json",
            "config": "config.schema.json",
        }
        for name, filename in mapping.items():
            full = os.path.join(self.schema_dir, filename)
            if not os.path.exists(full):
                raise FileNotFoundError(f"Schema file not found: {full}")
            with open(full, "r", encoding="utf-8") as f:
                schema = json.load(f)
            # Pre-validate schema itself (only if jsonschema is available)
            if _validator_for is not None and jsonschema is not None:
                Validator._check_schema(schema)
            self._schemas[name] = SchemaSpec(name=name, path=full, schema=schema)

    def validate(self, dataset_name: str, data: Any) -> None:
        if _validator_for is None or jsonschema is None:
            raise ImportError("jsonschema is required for validation (Draft 2020-12).")

        # Accept both logical keys and direct schema filenames
        mapping = {
            "characters": "characters.schema.json",
            "skills": "skills.schema.json",
            "templates": "templates.schema.json",
            "config": "config.schema.json",
        }

        # Some existing code calls validate(schema_dict, "characters.schema.json")
        # Normalize arguments accordingly.
        if isinstance(dataset_name, dict) and isinstance(data, str):
            # swap arguments
            data, dataset_name = dataset_name, data

        if not isinstance(dataset_name, str):
            raise TypeError("dataset_name must be str key or schema filename")

        key = dataset_name
        filename = mapping.get(dataset_name, dataset_name)
        spec = self._schemas.get(key)
        if not spec or not spec.schema:
            full = os.path.join(self.schema_dir, filename)
            if not os.path.exists(full):
                raise KeyError(f"Schema not loaded and file not found for dataset: {dataset_name}")
            with open(full, "r", encoding="utf-8") as f:
                schema = json.load(f)
            Validator._check_schema(schema)
            spec = SchemaSpec(name=key, path=full, schema=schema)
            self._schemas[key] = spec

        # If caller wrapped payload inside a top-level key (e.g., {"characters": [...]})
        # but the schema expects an array at root, unwrap when it matches the logical key.
        if isinstance(data, dict) and key in mapping and key in data and isinstance(data[key], (list, dict)):
            data = data[key]

        validator_cls = _validator_for(spec.schema)  # type: ignore
        validator = validator_cls(spec.schema)       # type: ignore
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            first = errors[0]
            loc = "/".join([str(p) for p in first.path]) if first.path else "<root>"
            raise ValidationError(f"Validation failed for '{key}' at {loc}: {first.message}")