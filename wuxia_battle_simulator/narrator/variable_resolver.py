from typing import Any, Dict


class VariableResolver:
    """
    Resolves {dot.path} and {list[index]} placeholders against a context dict.
    - Dot segments traverse dicts/objects.
    - [index] supports integer indexing into lists/tuples.
    - Missing paths return "" (empty string) to keep narration flowing.
    """
    def resolve(self, path: str, context: Dict[str, Any]) -> Any:
        try:
            return self._resolve_path(path, context)
        except Exception:
            return ""

    def _resolve_path(self, path: str, context: Dict[str, Any]) -> Any:
        # Split by '.' but keep bracketed indices inside tokens
        tokens = self._split_tokens(path)
        cur: Any = context
        for tok in tokens:
            # Handle index suffixes like name[0][1]
            base, indices = self._split_indices(tok)
            if base:
                cur = self._get_attr_or_key(cur, base)
            for idx in indices:
                cur = self._get_index(cur, idx)
        return cur

    @staticmethod
    def _split_tokens(path: str) -> list:
        # Simple splitter that respects bracketed indices (no dots expected inside brackets)
        tokens = []
        buf = []
        depth = 0
        for ch in path:
            if ch == '.' and depth == 0:
                if buf:
                    tokens.append(''.join(buf))
                    buf = []
                continue
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth = max(0, depth - 1)
            buf.append(ch)
        if buf:
            tokens.append(''.join(buf))
        return tokens

    @staticmethod
    def _split_indices(token: str):
        # Extract base name and a list of integer indices
        base = ""
        indices = []
        i = 0
        # read base until '['
        while i < len(token) and token[i] != '[':
            base += token[i]
            i += 1
        # parse [number] blocks
        while i < len(token):
            if token[i] == '[':
                j = token.find(']', i + 1)
                if j == -1:
                    break
                num_str = token[i + 1:j]
                try:
                    idx = int(num_str)
                except ValueError:
                    idx = 0
                indices.append(idx)
                i = j + 1
            else:
                i += 1
        return base, indices

    @staticmethod
    def _get_attr_or_key(obj: Any, key: str) -> Any:
        if key == "":
            return obj
        if isinstance(obj, dict):
            return obj.get(key, "")
        # Support object attribute access
        if hasattr(obj, key):
            return getattr(obj, key)
        return ""

    @staticmethod
    def _get_index(obj: Any, idx: int) -> Any:
        try:
            return obj[idx]
        except Exception:
            return ""