"""Tests for backend.ingest.parser.try_parse_python_dict (M6 Step 3).

Covers v3 §4.4.2:

- 基础 JSON dict: try_parse_python_dict('{"a": 1}') == {"a": 1}
- 基础 JSON list: try_parse_python_dict('[1, 2]') == [1, 2]
- Python literal dict: try_parse_python_dict("{'a': 1}") == {"a": 1}
- Python literal list: try_parse_python_dict("[1, 2]") == [1, 2]
- 失败场景: try_parse_python_dict('not json or python') is None
- 失败场景: try_parse_python_dict('') is None
- 顶层非 dict/list: try_parse_python_dict('"plain string"') is None
- 顶层非 dict/list: try_parse_python_dict('42') is None
- 嵌套: try_parse_python_dict('{"a": [1, 2]}') == {"a": [1, 2]}
- 顶层 bool/null (True/False/None 顶层应为 None)

Constraint: never raises; returns None on any failure or top-level non-container.
"""

from __future__ import annotations

import pytest

from backend.ingest.parser import try_parse_python_dict


# =============================================================================
# Section 1: 基础 JSON parsing (json.loads 路径)
# =============================================================================

class TestBasicJSONDict:
    def test_simple_dict(self):
        assert try_parse_python_dict('{"a": 1}') == {"a": 1}

    def test_dict_multiple_keys(self):
        assert try_parse_python_dict('{"a": 1, "b": "two", "c": 3.0}') == {
            "a": 1,
            "b": "two",
            "c": 3.0,
        }

    def test_empty_dict(self):
        assert try_parse_python_dict('{}') == {}

    def test_nested_dict(self):
        assert try_parse_python_dict('{"outer": {"inner": 42}}') == {
            "outer": {"inner": 42}
        }

    def test_dict_with_whitespace(self):
        assert try_parse_python_dict('  {"a": 1}  ') == {"a": 1}


class TestBasicJSONList:
    def test_simple_list(self):
        assert try_parse_python_dict('[1, 2]') == [1, 2]

    def test_list_of_strings(self):
        assert try_parse_python_dict('["a", "b", "c"]') == ["a", "b", "c"]

    def test_empty_list(self):
        assert try_parse_python_dict('[]') == []

    def test_nested_list(self):
        assert try_parse_python_dict('[[1, 2], [3, 4]]') == [[1, 2], [3, 4]]


# =============================================================================
# Section 2: Python literal parsing (ast.literal_eval fallback)
# =============================================================================

class TestPythonLiteralDict:
    def test_simple_dict_python_literal(self):
        # Single quotes are NOT valid JSON but ARE valid Python literals.
        assert try_parse_python_dict("{'a': 1}") == {"a": 1}

    def test_dict_with_python_syntax(self):
        assert try_parse_python_dict("{'a': 1, 'b': 'two'}") == {"a": 1, "b": "two"}

    def test_python_literal_nested_dict(self):
        assert try_parse_python_dict("{'outer': {'inner': 42}}") == {
            "outer": {"inner": 42}
        }


class TestPythonLiteralList:
    def test_simple_list_python_literal(self):
        assert try_parse_python_dict("[1, 2]") == [1, 2]

    def test_list_with_python_syntax(self):
        assert try_parse_python_dict("['a', 'b']") == ["a", "b"]


# =============================================================================
# Section 3: 嵌套 structures
# =============================================================================

class TestNesting:
    def test_dict_with_list_value(self):
        assert try_parse_python_dict('{"a": [1, 2]}') == {"a": [1, 2]}

    def test_list_with_dict_value(self):
        assert try_parse_python_dict('[{"a": 1}, {"b": 2}]') == [{"a": 1}, {"b": 2}]

    def test_deeply_nested(self):
        result = try_parse_python_dict('{"a": {"b": {"c": [1, [2, 3], {"d": 4}]}}}')
        assert result == {"a": {"b": {"c": [1, [2, 3], {"d": 4}]}}}

    def test_dict_with_python_literal_nested_list(self):
        # Mix JSON/Python literal syntax: outer Python, inner JSON.
        assert try_parse_python_dict("{'a': [1, 2]}") == {"a": [1, 2]}


# =============================================================================
# Section 4: 失败场景
# =============================================================================

class TestFailureCases:
    def test_invalid_string(self):
        assert try_parse_python_dict('not json or python') is None

    def test_empty_string(self):
        assert try_parse_python_dict('') is None

    def test_whitespace_only_string(self):
        assert try_parse_python_dict('   ') is None

    def test_garbage_with_braces(self):
        assert try_parse_python_dict('{garbage}') is None

    def test_unclosed_brace(self):
        assert try_parse_python_dict('{"a": 1') is None

    def test_trailing_comma_json(self):
        # JSON doesn't allow trailing commas; Python's ast.literal_eval does.
        # Either way, the function should succeed OR return None; never raise.
        result = try_parse_python_dict('{"a": 1,}')
        assert result is None or result == {"a": 1}

    def test_unicode_garbage(self):
        assert try_parse_python_dict('\\u0000\\xff\\xfe') is None

    def test_nested_failure_returns_none(self):
        # Outer is valid dict, inner value is malformed.
        result = try_parse_python_dict('{"a": not_a_value}')
        assert result is None

    def test_double_encoded_json_fails(self):
        # Nested JSON strings don't auto-decode; should fail.
        assert try_parse_python_dict('"{\\"a\\": 1}"') is None


# =============================================================================
# Section 5: 顶层非 dict/list
# =============================================================================

class TestTopLevelNonContainer:
    """Top-level result must be dict or list. Anything else returns None."""

    def test_plain_string_returns_none(self):
        assert try_parse_python_dict('"plain string"') is None

    def test_integer_returns_none(self):
        assert try_parse_python_dict('42') is None

    def test_float_returns_none(self):
        assert try_parse_python_dict('3.14') is None

    def test_true_returns_none(self):
        # True is a top-level bool, not a container.
        assert try_parse_python_dict('True') is None

    def test_false_returns_none(self):
        assert try_parse_python_dict('False') is None

    def test_none_returns_none(self):
        # None is a top-level None, not a container.
        assert try_parse_python_dict('None') is None

    def test_null_json_returns_none(self):
        # JSON null is top-level None.
        assert try_parse_python_dict('null') is None


# =============================================================================
# Section 6: 顶层 bool/null 严格验证
# =============================================================================

class TestTopLevelBoolNull:
    """Comprehensive coverage of top-level non-container types — must all
    return None, never the underlying value."""

    @pytest.mark.parametrize("value", [
        "True", "False", "true", "false",  # bool variants
        "None", "null",                      # null variants
        "42", "3.14", "-1", "0",            # numeric
        '"hello"', "'hello'",                # string variants
    ])
    def test_top_level_non_container_returns_none(self, value):
        """Any top-level non-container must return None (v2 修正 4)."""
        assert try_parse_python_dict(value) is None, (
            f"Expected None for top-level non-container {value!r}"
        )


# =============================================================================
# Section 7: 不抛异常 (never-raise contract)
# =============================================================================

class TestNeverRaises:
    """The function must never raise — always returns None on failure."""

    @pytest.mark.parametrize("value", [
        "",                                    # empty
        "   ",                                 # whitespace
        "not json or python",                  # garbage
        "{",                                   # partial
        "}",                                   # partial
        "[",                                   # partial
        "]",                                   # partial
        "{\"unbalanced",                       # unclosed
        "1+2j",                                # complex (Python literal but not container)
        "b'bytes'",                            # bytes literal
        "def f(): pass",                       # function def (invalid)
        "{1: 2}",                              # int key — invalid JSON, but valid Python
        '{"a": 1, "a": 2}',                   # duplicate JSON keys (allowed)
    ])
    def test_never_raises_on_input(self, value):
        """Each input must return a value (not raise). Result may be None
        or a parsed container — both are acceptable."""
        try:
            result = try_parse_python_dict(value)
        except Exception as e:
            pytest.fail(f"try_parse_python_dict raised on input {value!r}: {e}")
        # When input parses to a top-level dict/list with non-int keys, return value.
        # When input fails or is non-container, return None.
        assert result is None or isinstance(result, (dict, list)), (
            f"Unexpected non-container result for {value!r}: {result!r}"
        )


# =============================================================================
# Section 8: JSON 优先级 — JSON-first then Python literal fallback
# =============================================================================

class TestJSONFirstPriority:
    """When input is valid JSON, the JSON parser is used (json.loads). When
    JSON fails, ast.literal_eval is tried. This documents the precedence."""

    def test_valid_json_does_not_need_python_fallback(self):
        # Standard JSON should parse fine.
        assert try_parse_python_dict('{"a": 1}') == {"a": 1}

    def test_python_literal_only(self):
        # Single quotes not valid JSON, must fallback to ast.literal_eval.
        assert try_parse_python_dict("{'a': 1}") == {"a": 1}

    def test_json_with_python_only_syntax(self):
        # Tuples are Python literals but NOT JSON. Should parse via fallback.
        # Note: result is a tuple, not list/dict → returns None (top-level check).
        assert try_parse_python_dict("(1, 2, 3)") is None

    def test_python_set_literal_returns_none(self):
        # Sets are Python literals but not dict/list → returns None.
        assert try_parse_python_dict("{1, 2, 3}") is None


# =============================================================================
# Section 9: 边界 — empty containers, special JSON
# =============================================================================

class TestBoundaryContainers:
    def test_empty_dict_via_json(self):
        assert try_parse_python_dict('{}') == {}

    def test_empty_list_via_json(self):
        assert try_parse_python_dict('[]') == []

    def test_empty_dict_via_python_literal(self):
        assert try_parse_python_dict('{}') == {}

    def test_empty_list_via_python_literal(self):
        assert try_parse_python_dict('[]') == []

    def test_dict_with_empty_string_value(self):
        assert try_parse_python_dict('{"a": ""}') == {"a": ""}

    def test_dict_with_null_value(self):
        assert try_parse_python_dict('{"a": null}') == {"a": None}

    def test_dict_with_bool_value(self):
        # bool values INSIDE a dict are fine (top-level bool → None).
        assert try_parse_python_dict('{"a": true}') == {"a": True}
        assert try_parse_python_dict('{"a": false}') == {"a": False}
