# API Keys and other configurations
DEEPSEEK_API_KEY = "sk-kkkkkkkkkkkk"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# 邮件配置 (如果也希望集中管理)
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 587
SMTP_USER = "QQ邮箱"
SMTP_PASSWORD = "xxxxxxxxx"  # 注意：这里需要使用授权码
EMAIL_SENDER = "QQ邮箱"
EMAIL_RECEIVER = "接收邮箱"

# 企业微信 Webhook (如果也希望集中管理)
WECHAT_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=kkkkkkkkkkk"

# 文件过滤配置
# 忽略的文件夹列表 (相对于仓库根目录)
DEFAULT_IGNORED_FOLDERS = ["Pods/", "node_modules/", ".git/", ".idea/", "__pycache__/"]
# 允许的文件扩展名列表 (如果为空，则不按扩展名过滤，除非被文件夹规则排除)
DEFAULT_ALLOWED_FILE_EXTENSIONS = ['.py', '.js', '.java', '.m', '.swift', '.kt', '.go', '.c', '.cpp', '.h', '.hpp']
# 忽略的特定文件列表 (相对于仓库根目录)
DEFAULT_IGNORED_FILES = [
    ".DS_Store", 
    "README.md"
    # "emaosoho/Support File/main.m"  # 举例:忽略特定路径下的文件
]

# 新增：需要审查的文件夹路径列表配置
# 请根据您的实际需求修改这些路径，路径应该是绝对路径或者相对于项目根目录的路径
# 在 full_project_reviewer.py 中使用时，通常会转换为绝对路径
FOLDERS_TO_REVIEW = [
    "/path/to/your/folder1",
    "/path/to/your/folder2",
    # "relative/path/to/folder3" # 也可以是相对路径
]
