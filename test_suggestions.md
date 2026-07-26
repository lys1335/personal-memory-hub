# Dashboard 测试建议

## ✅ 能命中记忆的问题（预期能找到相关记忆）

### 1. "codex"
**预期**: 找到 2-3 条记忆
**内容**: "codex为什么没有iphone版"
**AI 回复预期**: 会提到 codex 的相关讨论，可能说"记忆中你问过 codex 为什么没有 iPhone 版"

### 2. "cloudcli"
**预期**: 找到 2-3 条记忆
**内容**: "我启动了cloudcli，这个和codex和qwen3搭配吧。"
**AI 回复预期**: 会引用 cloudcli 与 codex/qwen3 的搭配讨论

### 3. "docker"
**预期**: 找到 2-3 条记忆
**内容**: "我还是不用openhands了。怎么卸载呢。docker留着吧，不自动启动就行了。"
**AI 回复预期**: 会提到 openhands 卸载和 docker 的配置

### 4. "paypay"
**预期**: 找到 2-3 条记忆
**内容**: "我发现一个问题啊。举个例子，在日本便利店支付时，我可以选择paypay的app支付..."
**AI 回复预期**: 会引用日本便利店支付和 paypay 的经验

### 5. "qwen"
**预期**: 找到 2-3 条记忆
**内容**: "有了A1可以用本地AI吗？比如qwen2.5 7B"
**AI 回复预期**: 会提到本地 AI 和 qwen2.5 7B 的讨论

## ❌ 搜不到结果的情况

### 多词组合搜索（如 "docker openhands"）
**原因**: Memory Hub 的 search_by_keyword 使用简单的 AND 匹配，多词需要同时出现在同一条记忆里
**解决**: 用单个关键词搜索效果更好

### "NISA"、"gpt-oss"
**原因**: 这些关键词在 memory_nodes.content 中不存在（只在 vector_documents 中有 embedding）
**说明**: 向量搜索依赖 embedding 质量，当前 embedding 索引可能需要重新训练

## 💡 最佳测试策略

1. **单关键词搜索** — 效果最好（codex / docker / paypay / qwen / cloudcli）
2. **自然语言提问** — AI 会理解意图并生成合理回复
3. **结合记忆上下文** — AI 会引用记忆中的具体对话内容

## 🔧 注意事项

- 所有记忆来自 ChatGPT 聊天记录导入（约 1644 条）
- 记忆内容主要是技术讨论：AI 工具配置、Docker、Ollama 等
- 部分记忆内容较短（仅标题/摘要），检索效果取决于内容长度
