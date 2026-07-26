# 🧠 记忆中枢 Dashboard

## 概述

这是Personal Memory Hub的专用管理界面，提供实时状态监控、记忆检索测试和系统管理功能。

## 功能特性

### 📊 系统状态监控
- 实时显示服务运行状态
- 存储空间使用情况
- 数据库连接状态
- 系统健康度指标

### 💬 记忆检索测试
- 交互式对话界面
- 查询历史记忆内容
- 查看相似度评分
- 临时会话记录（不存储）

### 🔄 活动日志
- 最近操作记录
- 实时更新显示
- 时间戳标记
- 操作类型分类

### 🔮 扩展面板（占位）
- 高级数据分析
- AI助手集成
- 数据同步管理
- 可视化展示

## 快速开始

1. **启动HTTP服务器**:
   ```bash
   cd F:/LI_YONGSHUN/AI/personal-memory-hub
   python3 -m http.server 8080
   ```

2. **访问Dashboard**:
   打开浏览器访问: http://localhost:8080/dashboard-main.html

3. **测试记忆检索**:
   - 在"记忆检索测试"面板输入问题
   - 点击"发送"按钮
   - 查看检索结果

## 技术架构

- **前端**: 纯HTML5/CSS3/JavaScript
- **样式**: CSS Grid + Flexbox布局
- **动画**: CSS3 transitions
- **响应式**: 自适应不同屏幕尺寸

## 文件结构

```
personal-memory-hub/
├── dashboard-main.html      # 主Dashboard界面
├── dashboard-test.html      # 简化版测试界面
├── DASHBOARD_README.md      # 使用说明
└── test_cases.md            # 测试用例
```

## 注意事项

- Dashboard仅用于管理和测试目的
- 对话内容不会保存到数据库
- 需要Memory Hub API正常运行
- 建议在Chrome/Firefox等现代浏览器中使用

## 未来规划

- [ ] 集成实时数据更新
- [ ] 添加更多统计图表
- [ ] 支持用户权限管理
- [ ] 移动端适配优化
