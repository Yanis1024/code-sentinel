# Code Sentinel 🛡️

> 🚀 基于大模型的智能代码审查工具，支持多种AI模型，让代码审查更高效、更智能！

## 📋 目录

- [项目介绍](#项目介绍)
- [支持的AI模型](#支持的ai模型)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [系统要求](#系统要求)
- [安装配置](#安装配置)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [文件过滤](#文件过滤)
- [使用示例](#使用示例)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 🎯 项目介绍

Code Sentinel 是一个基于大语言模型的智能代码审查工具，旨在帮助开发团队提高代码质量和开发效率。通过集成多种主流AI模型，它能够：

- 🔍 **智能发现问题**：自动识别潜在的Bug、安全漏洞和性能问题
- 📝 **提供改进建议**：给出具体的代码优化建议和最佳实践
- 🎨 **代码风格检查**：确保代码符合团队规范和行业标准
- 🚀 **提升效率**：减少人工审查时间，专注于核心业务逻辑

## 🤖 支持的AI模型

| AI模型 | 特点 | 适用场景 |
|--------|------|----------|
| **DeepSeek** | 专业代码模型，性价比高 | 日常代码审查，推荐首选 |
| **ChatGPT** | 通用性强，理解能力佳 | 复杂逻辑分析，架构建议 |
| **Gemini** | 多模态支持，上下文长 | 大文件审查，项目分析 |
| **Claude** | 安全性高，推理能力强 | 安全审查，代码重构 |
| **Grok** | 实时性好，创新思维 | 新技术栈，前沿实践 |

## ✨ 功能特性

### 🔄 双模式审查
- **分支对比审查**：审查当前分支与目标分支的差异代码
- **全项目审查**：对整个项目进行全面的代码质量检查

### 🎯 智能过滤
- **文件类型过滤**：支持按文件扩展名筛选
- **目录过滤**：忽略不必要的目录（如node_modules、.git等）
- **自定义规则**：灵活配置过滤规则，节省审查成本

### 📬 多渠道通知
- **邮件通知**：支持SMTP邮件发送审查报告
- **企业微信**：集成企业微信机器人推送
- **本地报告**：生成详细的本地审查报告文件

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/your-repo/code-sentinel.git
cd code-sentinel
```

### 2. 安装依赖
```bash
pip install requests
```

### 3. 配置API密钥
编辑 `config.py` 文件，配置您的AI模型API密钥：
```python
DEEPSEEK_API_KEY = "your-deepseek-api-key"
```

### 4. 运行审查
```bash
# 审查分支差异
python code_reviewer.py

# 审查整个项目
python full_project_reviewer.py
```

## 💻 系统要求

- **Python**: 3.6+
- **操作系统**: Windows, macOS, Linux
- **Git**: 用于获取代码差异
- **网络**: 需要访问AI模型API

### 依赖包
- `requests`: HTTP请求库
- `subprocess`: 系统命令执行（Python内置）
- `smtplib`: 邮件发送（Python内置）

## 🛠️ 安装配置

### 1. 环境准备
```bash
# 检查Python版本
python --version

# 安装依赖
pip install requests
```

### 2. 配置文件设置
复制并编辑配置文件：
```bash
cp config.py.example config.py  # 如果有示例文件
```

### 3. API密钥配置
在 `config.py` 中配置您的API密钥：
```python
# DeepSeek API配置（推荐）
DEEPSEEK_API_KEY = "sk-your-deepseek-api-key"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# 其他AI模型配置...
```

### 4. 通知配置（可选）
```python
# 邮件配置
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
EMAIL_SENDER = "your-email@gmail.com"
EMAIL_RECEIVER = "receiver@gmail.com"

# 企业微信配置
WECHAT_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key"
```

## 📖 使用指南

### 分支差异审查

1. **配置项目路径**
   ```python
   # 在 code_reviewer.py 中配置
   REPO_PATH = "/path/to/your/project"
   TARGET_BRANCH = "origin/master"
   CURRENT_BRANCH = "feature-branch"
   ```

2. **运行审查**
   ```bash
   python code_reviewer.py
   ```

3. **查看报告**
   - 控制台输出：实时审查进度
   - 本地文件：`code_review_issues.txt`
   - 邮件通知：详细审查报告
   - 企业微信：审查摘要

### 全项目审查

1. **配置审查范围**
   ```python
   # 在 full_project_reviewer.py 中配置
   REPO_TO_REVIEW = "/path/to/your/project"
   BRANCH_TO_REVIEW = "main"
   ```

2. **运行审查**
   ```bash
   python full_project_reviewer.py
   ```

3. **审查报告**
   - 生成文件：`full_project_review_report.txt`
   - 包含每个文件的详细审查意见

## ⚙️ 配置说明

### config.py 配置项

```python
# API配置
DEEPSEEK_API_KEY = "your-api-key"          # DeepSeek API密钥
DEEPSEEK_API_URL = "api-endpoint"          # API端点

# 邮件配置
SMTP_HOST = "smtp.server.com"              # SMTP服务器
SMTP_PORT = 587                            # SMTP端口
SMTP_USER = "username"                     # 邮箱用户名
SMTP_PASSWORD = "password"                 # 邮箱密码/授权码
EMAIL_SENDER = "sender@email.com"          # 发送者邮箱
EMAIL_RECEIVER = "receiver@email.com"      # 接收者邮箱

# 企业微信配置
WECHAT_WEBHOOK_URL = "webhook-url"         # 企业微信机器人URL

# 文件过滤配置
DEFAULT_IGNORED_FOLDERS = [                # 忽略的文件夹
    "node_modules/", ".git/", "__pycache__/", "Pods/"
]
DEFAULT_ALLOWED_FILE_EXTENSIONS = [        # 允许的文件扩展名
    '.py', '.js', '.java', '.cpp', '.c', '.h'
]
DEFAULT_IGNORED_FILES = [                  # 忽略的特定文件
    ".DS_Store", "README.md"
]

# 项目审查配置
FOLDERS_TO_REVIEW = [                      # 需要审查的文件夹
    "/path/to/folder1",
    "/path/to/folder2"
]
```

## 🔧 文件过滤

### 过滤规则配置

`file_filter.py` 提供了灵活的文件过滤功能：

```python
from file_filter import FileFilter

# 创建过滤器
filter = FileFilter(
    ignored_folders=["node_modules/", ".git/"],
    allowed_extensions=[".py", ".js", ".java"],
    ignored_files=[".DS_Store", "config.local.py"]
)

# 检查文件是否允许
if filter.is_allowed("src/main.py"):
    print("文件将被审查")
```

### 常用过滤配置

```python
# 前端项目
FRONTEND_FILTER = {
    "ignored_folders": ["node_modules/", "dist/", "build/"],
    "allowed_extensions": [".js", ".ts", ".jsx", ".tsx", ".vue"],
    "ignored_files": ["package-lock.json", ".env.local"]
}

# 后端项目
BACKEND_FILTER = {
    "ignored_folders": ["__pycache__/", "venv/", ".pytest_cache/"],
    "allowed_extensions": [".py", ".java", ".go", ".rs"],
    "ignored_files": ["requirements.txt", ".env"]
}

# 移动端项目
MOBILE_FILTER = {
    "ignored_folders": ["Pods/", "build/", "DerivedData/"],
    "allowed_extensions": [".swift", ".m", ".h", ".kt", ".java"],
    "ignored_files": ["Podfile.lock", ".DS_Store"]
}
```

## 💡 使用示例

### 示例1: 基本使用
```python
from code_reviewer import main

# 配置项目信息
REPO_PATH = "/Users/developer/my-project"
TARGET_BRANCH = "origin/main"
CURRENT_BRANCH = "feature/new-feature"

# 运行审查
main()
```

### 示例2: 自定义过滤器
```python
from file_filter import FileFilter
from full_project_reviewer import ProjectReviewer

# 创建自定义过滤器
custom_filter = FileFilter(
    ignored_folders=["vendor/", "cache/"],
    allowed_extensions=[".php", ".js"],
    ignored_files=["composer.lock"]
)

# 创建审查器
reviewer = ProjectReviewer(
    repo_path="/path/to/php-project",
    target_branch="main",
    # 其他配置...
)

# 运行审查
report, summary = reviewer.review_project()
```

### 示例3: 批量文件夹审查
```python
from full_project_reviewer import FolderReviewer

# 配置要审查的文件夹
folders = [
    "/path/to/project1/src",
    "/path/to/project2/app",
    "/path/to/project3/lib"
]

# 创建文件夹审查器
folder_reviewer = FolderReviewer(
    folder_paths_to_review=folders,
    deepseek_api_key="your-api-key",
    deepseek_api_url="https://api.deepseek.com/chat/completions"
)

# 运行审查
report, summary = folder_reviewer.review_folders()
```

## ❓ 常见问题

### Q1: API密钥配置问题
**Q**: 如何获取DeepSeek API密钥？
**A**: 访问 [DeepSeek官网](https://platform.deepseek.com) 注册账号并获取API密钥。

### Q2: 审查速度慢
**Q**: 审查大项目时速度很慢怎么办？
**A**: 
- 合理配置文件过滤规则，排除不必要的文件
- 使用分支差异审查而非全项目审查
- 调整API请求超时时间

### Q3: 邮件发送失败
**Q**: 邮件通知发送失败？
**A**: 
- 检查SMTP配置是否正确
- 确认邮箱密码是否为授权码（而非登录密码）
- 检查网络连接和防火墙设置

### Q4: Git命令执行失败
**Q**: 提示Git命令执行失败？
**A**: 
- 确认Git已正确安装并在PATH中
- 检查项目路径是否为有效的Git仓库
- 确认目标分支是否存在

### Q5: 审查报告质量
**Q**: 如何提高审查报告的质量？
**A**: 
- 选择合适的AI模型（推荐DeepSeek用于代码审查）
- 调整API参数（temperature、max_tokens等）
- 提供更多上下文信息

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献方式
1. **报告问题**：在Issues中报告bug或提出功能请求
2. **代码贡献**：提交Pull Request改进代码
3. **文档改进**：完善文档和示例
4. **功能建议**：提出新功能想法

### 开发流程
1. Fork项目到您的GitHub账号
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

### 代码规范
- 遵循PEP 8 Python代码规范
- 添加适当的注释和文档字符串
- 确保代码通过现有测试
- 新功能需要添加相应测试

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 📞 联系我们

- **项目主页**: [GitHub Repository](https://github.com/your-repo/code-sentinel)
- **问题反馈**: [GitHub Issues](https://github.com/your-repo/code-sentinel/issues)
- **邮件联系**: nxycyl@gmail.com

---

⭐ 如果这个项目对您有帮助，请给我们一个Star！

📝 **更新日志**: 查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新信息

🔄 **最后更新**: 2025年7月

---

*Code Sentinel - 让代码审查更智能，让开发更高效！*
