with open(r"F:\LI_YONGSHUN\AI\personal-memory-hub\backend\pyproject.toml", "r", encoding="utf-8") as f:
    content = f.read()
# Look for [tool.ruff] section
import re
match = re.search(r'\[tool\.ruff\](.*?)(?:\n\[|\Z)', content, re.DOTALL)
if match:
    print("Ruff config found:")
    print(match.group(1)[:1000])
else:
    print("No [tool.ruff] section. Showing first 2000 chars of file:")
    print(content[:2000])