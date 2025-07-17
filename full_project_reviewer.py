import subprocess
import re
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import requests
except ImportError:
    raise ImportError("请先使用pip安装requests模块: pip install requests")

# 从 file_filter.py 导入 FileFilter 类
from file_filter import FileFilter

# 从 config.py 导入配置
from config import DEEPSEEK_API_KEY as CONFIG_DEEPSEEK_API_KEY
from config import DEEPSEEK_API_URL as CONFIG_DEEPSEEK_API_URL
from config import WECHAT_WEBHOOK_URL as CONFIG_WECHAT_WEBHOOK_URL
from config import (
    SMTP_HOST as CONFIG_SMTP_HOST,
    SMTP_PORT as CONFIG_SMTP_PORT,
    SMTP_USER as CONFIG_SMTP_USER,
    SMTP_PASSWORD as CONFIG_SMTP_PASSWORD,
    EMAIL_SENDER as CONFIG_EMAIL_SENDER,
    EMAIL_RECEIVER as CONFIG_EMAIL_RECEIVER,
    DEFAULT_IGNORED_FOLDERS,
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_IGNORED_FILES,
    FOLDERS_TO_REVIEW # <--- 新增导入
)

# --- 默认配置 (可以在实例化 ProjectReviewer 时覆盖) ---
DEFAULT_REPO_PATH = "."  # 默认为当前目录
DEFAULT_DEEPSEEK_API_KEY = CONFIG_DEEPSEEK_API_KEY
DEFAULT_DEEPSEEK_API_URL = CONFIG_DEEPSEEK_API_URL
DEFAULT_SMTP_CONFIG = {
    "host": CONFIG_SMTP_HOST,
    "port": CONFIG_SMTP_PORT,
    "user": CONFIG_SMTP_USER,
    "password": CONFIG_SMTP_PASSWORD,
    "sender": CONFIG_EMAIL_SENDER,
    "receiver": CONFIG_EMAIL_RECEIVER
}
DEFAULT_WECHAT_WEBHOOK_URL = CONFIG_WECHAT_WEBHOOK_URL
DEFAULT_FILE_EXTENSIONS = DEFAULT_ALLOWED_FILE_EXTENSIONS # 使用 config 中的默认扩展名
DEFAULT_IGNORED_FOLDERS_CONFIG = DEFAULT_IGNORED_FOLDERS # 使用 config 中的默认忽略文件夹
DEFAULT_IGNORED_FILES_CONFIG = DEFAULT_IGNORED_FILES # 使用 config 中的默认忽略文件

class ProjectReviewer:
    def __init__(self, repo_path=DEFAULT_REPO_PATH,
                 deepseek_api_key=DEFAULT_DEEPSEEK_API_KEY,
                 deepseek_api_url=DEFAULT_DEEPSEEK_API_URL,
                 smtp_config=None,
                 wechat_webhook_url=DEFAULT_WECHAT_WEBHOOK_URL,
                 file_extensions=None, # 将被 FileFilter 中的 allowed_extensions 替代
                 target_branch=None,
                 ignored_folders=None,
                 ignored_files=None,
                 allowed_extensions_override=None # 新增，用于覆盖config中的allowed_extensions
                 ):
        self.repo_path = os.path.abspath(repo_path)
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_api_url = deepseek_api_url
        self.smtp_config = smtp_config if smtp_config else DEFAULT_SMTP_CONFIG.copy() #确保是副本
        self.wechat_webhook_url = wechat_webhook_url
        
        # 初始化 FileFilter
        _ignored_folders = ignored_folders if ignored_folders is not None else DEFAULT_IGNORED_FOLDERS_CONFIG
        _ignored_files = ignored_files if ignored_files is not None else DEFAULT_IGNORED_FILES_CONFIG
        _allowed_extensions = allowed_extensions_override if allowed_extensions_override is not None else DEFAULT_ALLOWED_FILE_EXTENSIONS
        
        self.file_filter = FileFilter(
            ignored_folders=_ignored_folders,
            allowed_extensions=_allowed_extensions,
            ignored_files=_ignored_files
        )
        # self.file_extensions 保留用于可能的向后兼容或特定逻辑，但主要过滤由 self.file_filter 完成
        self.file_extensions = _allowed_extensions 
        
        if not self.deepseek_api_key or self.deepseek_api_key == "YOUR_DEEPSEEK_API_KEY":
            print("警告: DeepSeek API Key 未配置或使用的是默认占位符。")

        self.target_branch = target_branch if target_branch else self._get_current_branch()
        if not self.target_branch:
            raise ValueError("无法确定目标分支，请明确指定 target_branch。")
        print(f"项目审查器已初始化，目标仓库: {self.repo_path}, 目标分支: {self.target_branch}")

    def _run_command(self, command, cwd=None):
        """执行 shell 命令并返回输出"""
        effective_cwd = cwd if cwd else self.repo_path
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=effective_cwd, text=True, encoding='utf-8')
            stdout, stderr = process.communicate(timeout=60) # 增加超时
            if process.returncode != 0:
                print(f"命令执行错误: {command}")
                print(f"Stderr: {stderr}")
                return None
            return stdout
        except subprocess.TimeoutExpired:
            print(f"命令执行超时: {command}")
            process.kill()
            return None
        except Exception as e:
            print(f"执行命令时发生异常 {command}: {e}")
            return None

    def _get_current_branch(self):
        """获取当前的 Git 分支名称"""
        command = "git rev-parse --abbrev-ref HEAD"
        branch_name = self._run_command(command)
        return branch_name.strip() if branch_name else None

    def get_project_files(self):
        """获取项目中符合条件的文件列表"""
        command = f"git ls-tree -r --name-only {self.target_branch}"
        print(f"正在获取分支 '{self.target_branch}' 下的文件列表...")
        all_files_output = self._run_command(command)

        if not all_files_output:
            print(f"无法获取分支 '{self.target_branch}' 下的文件列表。请检查仓库状态和分支名称。")
            return []

        all_repo_files = all_files_output.strip().splitlines()
        
        filtered_files = []
        ignored_count = 0
        for file_path in all_repo_files:
            if self.file_filter.is_allowed(file_path):
                filtered_files.append(file_path)
            else:
                ignored_count += 1
        
        if ignored_count > 0:
            print(f"已根据过滤规则忽略了 {ignored_count} 个文件。")
        
        print(f"从 {len(all_repo_files)} 个总文件中，筛选出 {len(filtered_files)} 个文件进行审查。")
        return filtered_files

    def _call_deepseek_api(self, messages):
        """调用 DeepSeek API"""
        if not self.deepseek_api_key or self.deepseek_api_key == "YOUR_DEEPSEEK_API_KEY": # 此处的 "YOUR_DEEPSEEK_API_KEY" 检查可能需要调整或移除，因为默认值已来自 config
            # 如果 config.py 中的值是占位符，则此警告仍然有效
            # 如果 config.py 中的值是真实的 key，则此警告逻辑可能需要调整
            # 例如，可以检查 self.deepseek_api_key 是否等于 config.py 中的占位符（如果 config.py 可能包含占位符）
            print("警告: DeepSeek API Key 未配置或使用的是默认占位符。请检查 config.py 或环境变量。")
            # return "错误: DeepSeek API Key 未配置。" # 保持原有逻辑或调整

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        payload = {
            "model": "deepseek-coder",
            "messages": messages,
            "max_tokens": 3000,
            "temperature": 0.3,
        }
        try:
            response = requests.post(self.deepseek_api_url, headers=headers, json=payload, timeout=180)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"DeepSeek API 请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"API 响应内容: {e.response.text}")
            return f"DeepSeek API 请求失败: {e}"
        except (KeyError, IndexError) as e:
            print(f"解析 DeepSeek API 响应失败: {e}")
            return f"解析 DeepSeek API 响应失败: {e}"

    def get_review_for_file_content(self, file_path, file_content):
        """使用 DeepSeek 对单个文件的完整内容进行审查"""
        if not file_content.strip():
            return "文件内容为空，跳过审查。"

        # 限制文件内容长度，避免超出API限制或处理过大文件
        max_content_length = 15000 # 字符数，根据API和需求调整
        if len(file_content) > max_content_length:
            print(f"警告: 文件 {file_path} 内容过长 ({len(file_content)} chars)，将截断至 {max_content_length} chars 进行审查。")
            file_content = file_content[:max_content_length]

        prompt = f"""
        请对以下位于项目路径 '{file_path}' 中的代码文件进行全面的代码审查。
        文件内容如下:
        ```
        {file_content}
        ```
        请重点关注以下方面，并给出具体的、可操作的审查意见：
        1.  **潜在的 Bug 和逻辑错误**: 识别代码中可能存在的错误、边界条件问题或不正确的逻辑。
        2.  **安全漏洞**: 检查是否存在常见的安全风险，如注入、XSS、数据泄露等（根据代码语言和上下文判断）。
        3.  **代码可读性和可维护性**: 评估代码的清晰度、注释质量、命名规范、模块化程度等。是否有过于复杂或难以理解的部分？
        4.  **性能问题**: 分析是否存在可能的性能瓶颈，如低效算法、不当的资源使用等。
        5.  **编程最佳实践和代码风格**: 代码是否遵循了该语言和项目的通用最佳实践和编码规范？
        6.  **具体改进建议**: 对发现的每个问题，提供清晰的改进方案或代码示例。
        7.  **总结**: 简要总结文件的主要功能和整体代码质量。

        请以 Markdown 格式返回您的审查意见，使用标题、列表等使报告易于阅读。
        如果文件内容看起来不像是源代码（例如纯文本、配置文件、二进制文件等），请指出。
        """
        messages = [{"role": "user", "content": prompt}]
        return self._call_deepseek_api(messages)

    def review_project(self):
        """审查项目中的所有选定文件"""
        project_files = self.get_project_files()
        if not project_files:
            print("没有找到要审查的文件。")
            return "没有找到要审查的文件。"

        review_report_parts = [f"项目整体代码审查报告 - 分支: {self.target_branch}\n"]
        total_files = len(project_files)
        
        for i, file_rel_path in enumerate(project_files):
            full_file_path = os.path.join(self.repo_path, file_rel_path)
            print(f"\n正在审查文件 [{i+1}/{total_files}]: {file_rel_path}")
            
            try:
                with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            except FileNotFoundError:
                print(f"  错误: 文件 {full_file_path} 未找到。")
                review_report_parts.append(f"--- 文件: {file_rel_path} ---\n错误: 文件未找到。\n")
                continue
            except Exception as e:
                print(f"  错误: 读取文件 {full_file_path} 失败: {e}")
                review_report_parts.append(f"--- 文件: {file_rel_path} ---\n错误: 读取文件失败 - {e}\n")
                continue

            review_report_parts.append(f"--- 文件: {file_rel_path} ---")
            
            if not file_content.strip():
                review_report_parts.append("文件内容为空，跳过审查。\n")
                print("  文件内容为空，跳过。")
                continue

            review_comments = self.get_review_for_file_content(file_rel_path, file_content)
            review_report_parts.append("AI 代码审查意见:\n" + review_comments + "\n")
            print(f"  审查完成 (部分意见): {review_comments[:100].replace(os.linesep, ' ').strip()}...")
        
        final_report = "\n".join(review_report_parts)
        report_summary = f"项目整体代码审查完成。共审查 {total_files} 个文件。"
        print(f"\n{report_summary}")
        return final_report, report_summary

    def save_report(self, report_content, report_file_name="full_project_review_report.txt"):
        """将报告保存到文件"""
        # 确保报告保存在项目审查器脚本所在的目录，或者指定一个绝对路径
        # 这里我们保存在当前工作目录
        save_path = os.path.join(os.getcwd(), report_file_name)
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"审查报告已保存至: {save_path}")
            return save_path
        except Exception as e:
            print(f"保存审查报告到文件失败: {e}")
            return None

    def send_email_notification(self, subject, body):
        """发送邮件通知"""
        if not self.smtp_config or not all([self.smtp_config.get(k) for k in ['host', 'user', 'password', 'sender', 'receiver']]):
            print("SMTP 配置不完整，跳过发送邮件。")
            return

        cfg = self.smtp_config
        msg = MIMEMultipart()
        msg['From'] = cfg['sender']
        msg['To'] = cfg['receiver']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP(cfg['host'], cfg.get('port', 587))
            if cfg.get('port', 587) == 587: # 通常 587 端口使用 STARTTLS
                 server.starttls()
            server.login(cfg['user'], cfg['password'])
            text = msg.as_string()
            server.sendmail(cfg['sender'], cfg['receiver'], text)
            server.quit()
            print(f"邮件已成功发送至 {cfg['receiver']}")
        except Exception as e:
            print(f"发送邮件失败: {e}")

    def send_wechat_notification(self, message):
        """发送企业微信通知"""
        if not self.wechat_webhook_url or self.wechat_webhook_url == "YOUR_WECHAT_WEBHOOK_URL": # 如果 config.py 中的值可能是占位符，此检查仍有用
            # 或者，如果确信 config.py 中的值总是有效的，可以简化为:
            # if not self.wechat_webhook_url:
            print("企业微信 Webhook URL 未配置或仍为占位符，跳过发送通知。")
            return

        headers = {'Content-Type': 'application/json'}
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": message
            }
        }
        try:
            response = requests.post(self.wechat_webhook_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") == 0:
                print("企业微信通知发送成功")
            else:
                print(f"企业微信通知发送失败: {result.get('errmsg')}")
        except requests.exceptions.RequestException as e:
            print(f"发送企业微信通知时发生网络错误: {e}")
        except Exception as e:
            print(f"发送企业微信通知时发生未知错误: {e}")

# --- 新增 FolderReviewer 类 ---
class FolderReviewer:
    def __init__(self,
                 folder_paths_to_review, # 要审查的文件夹绝对路径列表
                 deepseek_api_key,
                 deepseek_api_url,
                 ignored_folders_config=None,
                 allowed_extensions_config=None,
                 ignored_files_config=None,
                 smtp_config=None,
                 wechat_webhook_url=None):
        
        if not isinstance(folder_paths_to_review, list):
            raise ValueError("folder_paths_to_review 必须是一个列表")
        self.folder_paths_to_review = [os.path.abspath(p) for p in folder_paths_to_review]
        
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_api_url = deepseek_api_url
        self.smtp_config = smtp_config if smtp_config else {}
        self.wechat_webhook_url = wechat_webhook_url

        # 初始化 FileFilter
        # 如果未提供配置，则使用 config.py 中的默认值
        _ignored_folders = ignored_folders_config if ignored_folders_config is not None else DEFAULT_IGNORED_FOLDERS
        _allowed_extensions = allowed_extensions_config if allowed_extensions_config is not None else DEFAULT_ALLOWED_FILE_EXTENSIONS
        _ignored_files = ignored_files_config if ignored_files_config is not None else DEFAULT_IGNORED_FILES
        
        self.file_filter = FileFilter(
            ignored_folders=_ignored_folders,
            allowed_extensions=_allowed_extensions,
            ignored_files=_ignored_files
        )

        if not self.deepseek_api_key or self.deepseek_api_key == "YOUR_DEEPSEEK_API_KEY":
            print("警告 (FolderReviewer): DeepSeek API Key 未配置或使用的是默认占位符。")

        print(f"文件夹审查器已初始化，目标文件夹: {self.folder_paths_to_review}")

    def _call_deepseek_api(self, messages):
        """调用 DeepSeek API (与 ProjectReviewer 中的类似)"""
        if not self.deepseek_api_key or self.deepseek_api_key == "YOUR_DEEPSEEK_API_KEY":
            print("警告 (FolderReviewer): DeepSeek API Key 未配置或使用的是默认占位符。")
            # return "错误: DeepSeek API Key 未配置。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        payload = {
            "model": "deepseek-coder",
            "messages": messages,
            "max_tokens": 8192, # 与 ProjectReviewer 保持一致或按需调整
            "temperature": 0.3,
        }
        try:
            response = requests.post(self.deepseek_api_url, headers=headers, json=payload, timeout=180)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"DeepSeek API 请求失败 (FolderReviewer): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"API 响应内容: {e.response.text}")
            return f"DeepSeek API 请求失败: {e}"
        except (KeyError, IndexError) as e:
            print(f"解析 DeepSeek API 响应失败 (FolderReviewer): {e}")
            return f"解析 DeepSeek API 响应失败: {e}"

    def get_review_for_file_content(self, file_display_path, file_content):
        """使用 DeepSeek 对单个文件的完整内容进行审查 (与 ProjectReviewer 中的类似)"""
        if not file_content.strip():
            return "文件内容为空，跳过审查。"

        max_content_length = 15000 
        if len(file_content) > max_content_length:
            print(f"警告 (FolderReviewer): 文件 {file_display_path} 内容过长 ({len(file_content)} chars)，将截断至 {max_content_length} chars 进行审查。")
            file_content = file_content[:max_content_length]

        prompt = f"""
        请对以下位于路径 '{file_display_path}' 中的代码文件进行全面的代码审查。
        文件内容如下:
        ```
        {file_content}
        ```
        请重点关注以下方面，并给出具体的、可操作的审查意见：
        1.  **潜在的 Bug 和逻辑错误**
        2.  **安全漏洞**
        3.  **代码可读性和可维护性**
        4.  **性能问题**
        5.  **编程最佳实践和代码风格**
        6.  **具体改进建议**
        7.  **总结**

        请以 Markdown 格式返回您的审查意见。
        """
        messages = [{"role": "user", "content": prompt}]
        return self._call_deepseek_api(messages)

    def review_folders(self):
        """审查配置的文件夹列表中的所有符合条件的文件"""
        review_report_parts = ["文件夹批量代码审查报告\n"]
        total_files_scanned = 0
        total_files_processed = 0

        for base_folder_path in self.folder_paths_to_review:
            if not os.path.isdir(base_folder_path):
                print(f"警告: 路径 {base_folder_path} 不是一个有效的文件夹，跳过。")
                review_report_parts.append(f"\n--- 目标文件夹 (无效或无法访问): {base_folder_path} ---\n")
                continue
            
            review_report_parts.append(f"\n--- 开始审查文件夹: {base_folder_path} ---\n")
            files_in_current_folder_processed = 0

            for root, _, files in os.walk(base_folder_path):
                for file_name in files:
                    full_file_path = os.path.join(root, file_name)
                    # 文件路径相对于当前审查的 base_folder_path，用于过滤和报告
                    relative_file_path_to_base = os.path.relpath(full_file_path, base_folder_path)
                    
                    total_files_scanned += 1

                    if not self.file_filter.is_allowed(relative_file_path_to_base):
                        # print(f"  文件 {relative_file_path_to_base} (在 {base_folder_path} 中) 被过滤规则忽略。")
                        continue
                    
                    total_files_processed += 1
                    files_in_current_folder_processed +=1
                    
                    # 用于报告和API提示的路径可以是相对于base_folder的，也可以是完整的
                    # 这里我们使用相对于 base_folder_path 的路径，因为它更简洁
                    display_path = os.path.join(os.path.basename(base_folder_path), relative_file_path_to_base)


                    print(f"\n正在审查文件 [{total_files_processed}]: {full_file_path}")
                    
                    try:
                        with open(full_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            file_content = f.read()
                    except FileNotFoundError: # 理论上 os.walk 不会返回不存在的文件，但以防万一
                        print(f"  错误: 文件 {full_file_path} 未找到。")
                        review_report_parts.append(f"--- 文件: {display_path} ---\n错误: 文件未找到。\n")
                        continue
                    except Exception as e:
                        print(f"  错误: 读取文件 {full_file_path} 失败: {e}")
                        review_report_parts.append(f"--- 文件: {display_path} ---\n错误: 读取文件失败 - {e}\n")
                        continue

                    review_report_parts.append(f"--- 文件: {display_path} ---")
                    
                    if not file_content.strip():
                        review_report_parts.append("文件内容为空，跳过审查。\n")
                        print("  文件内容为空，跳过。")
                        continue

                    review_comments = self.get_review_for_file_content(display_path, file_content)
                    review_report_parts.append("AI 代码审查意见:\n" + review_comments + "\n")
                    print(f"  审查完成 (部分意见): {review_comments[:100].replace(os.linesep, ' ').strip()}...")
            
            review_report_parts.append(f"--- 文件夹 {base_folder_path} 审查完毕，共处理 {files_in_current_folder_processed} 个文件 ---\n")

        final_report = "\n".join(review_report_parts)
        report_summary = f"文件夹批量代码审查完成。共扫描约 {total_files_scanned} 个文件，实际处理并审查 {total_files_processed} 个文件。"
        print(f"\n{report_summary}")
        return final_report, report_summary

    def save_report(self, report_content, report_file_name="folder_review_report.txt"):
        """将报告保存到文件 (与 ProjectReviewer 中的类似)"""
        save_path = os.path.join(os.getcwd(), report_file_name)
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"文件夹审查报告已保存至: {save_path}")
            return save_path
        except Exception as e:
            print(f"保存文件夹审查报告到文件失败: {e}")
            return None

    def send_email_notification(self, subject, body):
        """发送邮件通知 (与 ProjectReviewer 中的类似)"""
        if not self.smtp_config or not all([self.smtp_config.get(k) for k in ['host', 'user', 'password', 'sender', 'receiver']]):
            print("SMTP 配置不完整 (FolderReviewer)，跳过发送邮件。")
            return
        # (邮件发送逻辑与 ProjectReviewer 相同，此处省略以保持简洁，实际应复制或重构)
        cfg = self.smtp_config
        msg = MIMEMultipart()
        msg['From'] = cfg['sender']
        msg['To'] = cfg['receiver']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            server = smtplib.SMTP(cfg['host'], cfg.get('port', 587))
            if cfg.get('port', 587) == 587:
                 server.starttls()
            server.login(cfg['user'], cfg['password'])
            text = msg.as_string()
            server.sendmail(cfg['sender'], cfg['receiver'], text)
            server.quit()
            print(f"邮件已成功发送至 {cfg['receiver']} (FolderReviewer)")
        except Exception as e:
            print(f"发送邮件失败 (FolderReviewer): {e}")


    def send_wechat_notification(self, message):
        """发送企业微信通知 (与 ProjectReviewer 中的类似)"""
        if not self.wechat_webhook_url or self.wechat_webhook_url == "YOUR_WECHAT_WEBHOOK_URL":
            print("企业微信 Webhook URL 未配置或仍为占位符 (FolderReviewer)，跳过发送通知。")
            return
        # (企业微信通知逻辑与 ProjectReviewer 相同，此处省略以保持简洁，实际应复制或重构)
        headers = {'Content-Type': 'application/json'}
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": message
            }
        }
        try:
            response = requests.post(self.wechat_webhook_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("errcode") == 0:
                print("企业微信通知发送成功 (FolderReviewer)")
            else:
                print(f"企业微信通知发送失败 (FolderReviewer): {result.get('errmsg')}")
        except requests.exceptions.RequestException as e:
            print(f"发送企业微信通知时发生网络错误 (FolderReviewer): {e}")
        except Exception as e:
            print(f"发送企业微信通知时发生未知错误 (FolderReviewer): {e}")


if __name__ == "__main__":
    # --- 用户配置 ---
    # ProjectReviewer 配置
    REPO_TO_REVIEW = "/Users/yl/emaosoho"
    BRANCH_TO_REVIEW = "feat_1024"
    # 可以按需配置忽略的文件夹和文件
    CUSTOM_IGNORED_FOLDERS = ["Pods/", "build/", "DerivedData/"] 
    CUSTOM_IGNORED_FILES = [".DS_Store", "Localizable.strings"]
    # 如果需要覆盖config中的allowed_extensions，可以在这里设置
    CUSTOM_ALLOWED_EXTENSIONS = None # 例如 ['.m', '.h'] 或保持 None 使用config默认

    api_key_env = os.getenv("DEEPSEEK_API_KEY")
    
    # 如果环境变量中没有，则 ProjectReviewer 会使用 DEFAULT_DEEPSEEK_API_KEY (来自 config.py)
    # 如果希望在 __main__ 中明确传递，可以这样做：
    # current_api_key = api_key_env if api_key_env else DEFAULT_DEEPSEEK_API_KEY
    # 但由于 ProjectReviewer 构造函数已有此逻辑，直接传递 api_key_env (如果存在) 或让其使用默认值即可

    if api_key_env:
        print(f"使用环境变量中的 DEEPSEEK_API_KEY。")
        current_api_key = api_key_env
    else:
        print(f"环境变量 DEEPSEEK_API_KEY 未设置，将使用 config.py 中定义的默认值: {DEFAULT_DEEPSEEK_API_KEY[:10]}...") # 显示部分key用于确认
        current_api_key = DEFAULT_DEEPSEEK_API_KEY # 明确使用从config导入的

    if not current_api_key or current_api_key == "YOUR_DEEPSEEK_API_KEY": # 再次检查最终使用的key是否为占位符
         print("警告: 最终使用的 DeepSeek API Key 可能是占位符。请检查 config.py 或环境变量。")

    # SMTP 配置 (可以从环境变量或配置文件加载)
    # 为简化，这里可能使用脚本中定义的 DEFAULT_SMTP_CONFIG
    # 实际应用中，敏感信息如密码不应硬编码
    smtp_cfg = DEFAULT_SMTP_CONFIG # 或者从更安全的地方加载配置

    # 企业微信 Webhook URL (通常从环境变量获取)
    wechat_url_env = os.getenv("WECHAT_WEBHOOK_URL")
    current_wechat_url = wechat_url_env if wechat_url_env else DEFAULT_WECHAT_WEBHOOK_URL

    if not current_wechat_url or current_wechat_url == "YOUR_WECHAT_WEBHOOK_URL": # 检查最终的 webhook url
        print("警告: 企业微信 Webhook URL 未配置或使用的是默认占位符。请检查 config.py 或环境变量。")


    print(f"准备审查项目: {REPO_TO_REVIEW}, 分支: {BRANCH_TO_REVIEW}")

    reviewer = ProjectReviewer(
        repo_path=REPO_TO_REVIEW,
        target_branch=BRANCH_TO_REVIEW,
        deepseek_api_key=current_api_key, # 传递最终决定的 API key
        # deepseek_api_url 将使用 DEFAULT_DEEPSEEK_API_URL (来自 config.py) 如果未显式传递
        smtp_config=smtp_cfg,
        wechat_webhook_url=current_wechat_url # 修正参数名：wechat_url -> wechat_webhook_url
        # 如果有其他参数如 file_extensions，请确保它们也在这里传递
        # file_extensions=DEFAULT_FILE_EXTENSIONS # 例如
    )

    try:
        report_content, summary = reviewer.review_project()

        if report_content and summary: # 确保 review_project 返回了有效内容
            # 生成报告文件名，包含分支信息，避免覆盖
            safe_branch_name = BRANCH_TO_REVIEW.replace('/', '_').replace('\\', '_')
            report_file_name = f"full_project_review_report_{safe_branch_name}.txt"
            saved_path = reviewer.save_report(report_content, report_file_name)

            if saved_path:
                email_subject = f"项目整体代码审查报告 - {reviewer.repo_path} - 分支: {BRANCH_TO_REVIEW}"
                # 邮件内容可以包含摘要和报告路径
                email_body = f"{summary}\n\n详细报告已生成并保存至: {os.path.abspath(saved_path)}\n\n---报告预览 (部分)---\n{report_content[:2000]}..."
                reviewer.send_email_notification(email_subject, email_body)

                wechat_message = (f"#### 项目整体代码审查报告\n"
                                  f"**仓库**: `{reviewer.repo_path}`\n"
                                  f"**分支**: `{BRANCH_TO_REVIEW}`\n"
                                  f"**状态**: {summary}\n"
                                  f"报告已保存: `{os.path.abspath(saved_path)}`")
                reviewer.send_wechat_notification(wechat_message)
            else:
                print("报告内容已生成但保存失败。")
        elif isinstance(report_content, str) and "没有找到要审查的文件" in report_content : # 特殊处理 review_project 返回的提示信息
             print(report_content)
             # 可以选择为此情况发送通知
             wechat_message = (f"#### 项目整体代码审查提醒\n"
                               f"**仓库**: `{REPO_TO_REVIEW}`\n"
                               f"**分支**: `{BRANCH_TO_REVIEW}`\n"
                               f"**状态**: {report_content}")
             if reviewer.wechat_webhook_url and reviewer.wechat_webhook_url != DEFAULT_WECHAT_WEBHOOK_URL:
                 reviewer.send_wechat_notification(wechat_message)
        else:
            print("未能生成有效的审查报告或没有返回预期的报告内容。")

    except ValueError as ve:
        print(f"初始化审查器或执行审查时出错: {ve}")
    except Exception as e:
        print(f"执行项目审查过程中发生意外错误: {e}")
        # 可以考虑发送一个错误通知
        error_message = (f"#### 项目整体代码审查失败\n"
                         f"**仓库**: `{REPO_TO_REVIEW}`\n"
                         f"**分支**: `{BRANCH_TO_REVIEW}`\n"
                         f"**错误**: {e}")
        if reviewer.wechat_webhook_url and reviewer.wechat_webhook_url != DEFAULT_WECHAT_WEBHOOK_URL:
            reviewer.send_wechat_notification(error_message)

    print("\n项目整体代码审查流程结束。")

# 假设您有一个类似这样的函数来运行文件夹审查
# 或者这部分逻辑在 if __name__ == "__main__": 块中
def run_specific_folder_review(): # 函数名可能不同
    print("开始特定文件夹审查...")

    # 使用从 config.py 导入的 FOLDERS_TO_REVIEW
    folders_to_check = FOLDERS_TO_REVIEW

    if not folders_to_check:
        print("错误：没有在 config.py 中配置 FOLDERS_TO_REVIEW，或者列表为空。")
        return

    reviewer = FolderReviewer(
        folder_paths_to_review=folders_to_check, # <--- 使用配置项
        deepseek_api_key=DEFAULT_DEEPSEEK_API_KEY,
        deepseek_api_url=DEFAULT_DEEPSEEK_API_URL,
        ignored_folders_config=DEFAULT_IGNORED_FOLDERS,
        allowed_extensions_config=DEFAULT_ALLOWED_FILE_EXTENSIONS,
        ignored_files_config=DEFAULT_IGNORED_FILES,
        smtp_config=DEFAULT_SMTP_CONFIG,
        wechat_webhook_url=DEFAULT_WECHAT_WEBHOOK_URL
    )

    report_content, report_summary = reviewer.review_folders()

    if report_content:
        saved_report_path = reviewer.save_report(report_content, "specific_folder_review_report.txt")
        email_subject = "特定文件夹代码审查报告"
        
        # 发送邮件和微信通知
        if saved_report_path:
            email_body = f"{report_summary}\n\n详细报告已保存至: {saved_report_path}\n\n部分内容预览:\n{report_content[:2000]}"
            reviewer.send_email_notification(email_subject, email_body)
            
            wechat_message = f"#### 特定文件夹代码审查报告\n**状态**: {report_summary}\n报告已生成，请查收邮件或查看文件: `{os.path.basename(saved_report_path)}`"
            reviewer.send_wechat_notification(wechat_message)
        else:
            reviewer.send_email_notification(email_subject, report_summary + "\n\n报告保存失败。\n" + report_content)
            wechat_message = f"#### 特定文件夹代码审查报告\n**状态**: {report_summary}\n报告保存失败。"
            reviewer.send_wechat_notification(wechat_message)

    print("\n特定文件夹审查流程结束。")

if __name__ == "__main__":
    # ... 可能有其他调用 ...
    
    # 如果您想运行文件夹审查，可以这样调用：
    # run_specific_folder_review() 
    
    # 或者，如果您直接在 main 块中实例化 FolderReviewer:
    # print("开始文件夹审查 (直接在 main)...")
    # folders_to_check_main = FOLDERS_TO_REVIEW
    # if folders_to_check_main:
    #     folder_reviewer_main = FolderReviewer(
    #         folder_paths_to_review=folders_to_check_main,
    #         # ... 其他参数 ...
    #     )
    #     # ... 执行审查 ...
    # else:
    #     print("错误：没有在 config.py 中配置 FOLDERS_TO_REVIEW 用于主流程。")
    pass # 保留您原有的 main 逻辑

    print("\n项目整体代码审查流程结束。")