import subprocess
import re
import smtplib
try:
    import requests
except ImportError:
    # 如果无法导入requests模块,提示安装
    raise ImportError("请先使用pip安装requests模块: pip install requests")
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 从 file_filter.py 导入 FileFilter 类
from file_filter import FileFilter

# 从 config.py 导入配置
from config import (
    DEEPSEEK_API_KEY, 
    DEEPSEEK_API_URL, 
    WECHAT_WEBHOOK_URL,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    EMAIL_SENDER,
    EMAIL_RECEIVER,
    # 导入新的过滤配置
    DEFAULT_IGNORED_FOLDERS,
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_IGNORED_FILES
)

# --- 配置信息 ---
REPO_PATH = "/Users/XXX/XXX"  # Git 项目路径
TARGET_BRANCH = "origin/master"  # 比较的目标分支，设置为 master
CURRENT_BRANCH = "feat_1024" # 当前分支，设置为 feat_1024

# --- 初始化 FileFilter ---
# 您可以在这里或 main 函数中根据需要自定义这些列表
# 使用 config.py 中的默认值
file_filter = FileFilter(
    ignored_folders=DEFAULT_IGNORED_FOLDERS,
    allowed_extensions=DEFAULT_ALLOWED_FILE_EXTENSIONS,
    ignored_files=DEFAULT_IGNORED_FILES
)

# --- 辅助函数 ---

def run_command(command, cwd=None):
    """执行 shell 命令并返回输出"""
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=cwd, text=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            print(f"命令执行错误: {command}")
            print(f"Stderr: {stderr}")
            return None
        return stdout
    except Exception as e:
        print(f"执行命令时发生异常 {command}: {e}")
        return None

def get_git_diff(repo_path, target_branch, current_branch):
    """获取 git diff 内容"""
    remote_name = target_branch.split('/')[0] if '/' in target_branch else 'origin'
    
    print(f"正在尝试从远程 '{remote_name}' 获取最新信息...")
    fetch_command = f"git fetch {remote_name}"
    # 执行 git fetch 并检查其是否成功
    # run_command 会在命令失败时打印 stderr 并返回 None
    if run_command(fetch_command, cwd=repo_path) is None and remote_name == "origin": # 特别处理 origin，因为它是最常见的
        # 尝试获取所有远程的更新，以防默认的 'origin' 不明确或配置了多个tracking
        print(f"'{fetch_command}' 可能未完全成功或未找到特定远程。尝试 'git fetch --all'...")
        if run_command("git fetch --all", cwd=repo_path) is None:
             print(f"执行 'git fetch --all' 也失败。请检查您的网络连接和 Git 远程仓库配置。")
             return None

    # 检查目标分支在 fetch 后是否有效
    check_branch_cmd = f"git rev-parse --verify {target_branch}"
    if run_command(check_branch_cmd, cwd=repo_path) is None:
        print(f"错误：目标分支 '{target_branch}' 在本地的远程跟踪分支中未找到。")
        print(f"这通常意味着：")
        print(f"  1. 远程仓库 '{remote_name}' 中不存在名为 '{target_branch.split('/', 1)[1] if '/' in target_branch else target_branch}' 的分支。")
        print(f"  2. 'git fetch'未能成功更新本地对远程分支的认知。")
        print(f"请在仓库目录 '{repo_path}' 中手动运行 'git branch -r' 查看所有可用的远程分支，并确认 '{target_branch}' 是否存在。")
        print(f"如果分支名称不同 (例如 'origin/master' 而不是 'origin/main')，请更新脚本中的 TARGET_BRANCH 配置。")
        return None
    
    # 获取 merge-base 以进行正确的比较
    merge_base_cmd = f"git merge-base {target_branch} {current_branch}"
    merge_base = run_command(merge_base_cmd, cwd=repo_path)
    if not merge_base: # run_command 返回 None 如果 git merge-base 失败
        print(f"无法获取 '{target_branch}' 和 '{current_branch}' 的 merge-base。")
        print(f"这可能意味着：")
        print(f"  1. 这两个分支没有共同的提交历史。")
        print(f"  2. 当前分支 '{current_branch}' 可能不是一个有效的分支名或引用。")
        print(f"  3. 目标分支 '{target_branch}' 虽然存在，但与当前分支无关。")
        return None
    merge_base = merge_base.strip()

    diff_command = f"git diff {merge_base} {current_branch}"
    print(f"执行 diff 命令: {diff_command}")
    diff_output = run_command(diff_command, cwd=repo_path)
    return diff_output

def call_deepseek_api(messages):
    """调用 DeepSeek API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}" # 使用导入的 DEEPSEEK_API_KEY
    }
    payload = {
        "model": "deepseek-coder", # 或者其他适合的模型
        "messages": messages,
        "max_tokens": 3000, # 根据需要调整
        "temperature": 0.5, # 根据需要调整
    }
    try:
 # 增加超时时间
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120) # 使用导入的 DEEPSEEK_API_URL
        response.raise_for_status()  # 如果请求失败则抛出 HTTPError
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"DeepSeek API 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"API 响应内容: {e.response.text}")
        return None
    except (KeyError, IndexError) as e:
        print(f"解析 DeepSeek API 响应失败: {e}")
        # 检查response变量是否存在并且是否有text属性
        response_text = getattr(requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=120), 'text', 'N/A') if 'response' in locals() else 'N/A'
        print(f"API 原始响应: {response_text}")
        return None


def extract_full_method_from_deepseek(file_path, diff_hunk, file_content_str):
    """使用 DeepSeek 从 diff hunk 和文件内容中提取完整方法体"""
    prompt = f"""
    文件路径: {file_path}
    以下是该文件中的一段代码变更 (git diff hunk):
    ```diff
    {diff_hunk}
    ```
    以下是该文件的当前完整内容:
    ```
    {file_content_str[:8000]} 
    ```
    (注意: 为简洁起见，文件内容可能被截断)

    请基于上述 diff hunk 和文件内容，识别并提取出包含这些变更的完整方法或函数体。
    如果变更位于类定义之外的全局范围，请指出。
    如果变更跨越多个方法或无法清晰界定单个方法，请说明情况。
    请仅返回提取到的完整方法/函数代码，如果无法提取或不适用，请明确说明原因。
    """
    messages = [{"role": "user", "content": prompt}]
    return call_deepseek_api(messages)

def get_code_review_from_deepseek(file_path, method_code):
    """使用 DeepSeek 对方法代码进行审查"""
    if not method_code or "无法提取" in method_code or "不适用" in method_code:
        return "无法获取方法代码进行审查，或变更不适用于方法级审查。"

    prompt = f"""
    请对以下位于文件 '{file_path}' 中的代码进行审查:
    ```
    {method_code}
    ```
    请关注以下方面：
    1.  潜在的 Bug 和逻辑错误。
    2.  安全漏洞。
    3.  代码可读性和可维护性。
    4.  性能问题。
    5.  是否遵循常见的编程最佳实践和代码风格。
    6.  提出具体的改进建议。

    请以清晰、简洁的方式给出您的审查意见。
    """
    messages = [{"role": "user", "content": prompt}]
    return call_deepseek_api(messages)


def parse_diff_hunks(diff_output):
    """
    解析 git diff 输出，提取文件路径和 diff hunks。
    返回一个列表，每个元素是一个字典: {'file_path': str, 'hunks': [str]}
    """
    if not diff_output:
        return []

    changed_files_hunks = []
    current_file_path = None
    current_hunks = []

    # 正则表达式匹配 diff --git a/... b/... 行，并捕获 b 文件路径
    # 它会处理文件名中包含空格的情况
    file_path_pattern = re.compile(r'^diff --git a/(.+) b/(.+)$')
    # 正则表达式匹配 @@ ... @@ 行
    hunk_header_pattern = re.compile(r'^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@')

    lines = diff_output.splitlines()
    
    for i, line in enumerate(lines):
        match_file_path = file_path_pattern.match(line)
        if match_file_path:
            if current_file_path and current_hunks:
                changed_files_hunks.append({'file_path': current_file_path, 'hunks': current_hunks})
            
            # 优先使用 b 文件路径，因为它代表更改后的文件
            # 移除路径中可能存在的 "..." (如果文件名包含空格且被引号包围)
            current_file_path = match_file_path.group(2).strip('"')
            current_hunks = []
            # print(f"解析到文件: {current_file_path}") # 调试信息
            continue

        if current_file_path: # 确保我们已经识别了一个文件
            # 检查是否是 hunk 内容的一部分 (以 + 或 - 或空格开头，但不是 --- 或 +++)
            # 并且前面有 hunk header
            is_hunk_line = line.startswith(('+', '-', ' ')) and \
                           not line.startswith('---') and \
                           not line.startswith('+++')
            
            if is_hunk_line:
                # 查找最近的 hunk_header
                found_hunk_header = False
                for j in range(i - 1, max(-1, i - 20), -1): # 向上查找几行
                    if j < 0 or j >= len(lines): break
                    if hunk_header_pattern.match(lines[j]):
                        found_hunk_header = True
                        break
                if found_hunk_header:
                     current_hunks.append(line)


    if current_file_path and current_hunks: # 添加最后一个文件
        changed_files_hunks.append({'file_path': current_file_path, 'hunks': ["\n".join(current_hunks)]}) # 将hunks列表合并成一个字符串

    # 进一步处理，将每个文件的hunks列表聚合成单个hunk字符串
    # (上面的逻辑已经尝试这么做了，但这里可以确保格式)
    processed_list = []
    for item in changed_files_hunks:
        if item['hunks']: # 确保hunks不为空
             # 将hunks列表中的所有字符串连接成一个大的diff hunk字符串
            full_hunk_for_file = "\n".join(item['hunks'])
            if full_hunk_for_file.strip(): # 确保不是空hunk
                processed_list.append({'file_path': item['file_path'], 'hunk_content': full_hunk_for_file})
    
    return processed_list


def send_email(subject, body, receiver_email):
    """发送邮件"""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_SENDER]):
        print("SMTP 配置不完整，跳过发送邮件。请检查 config.py 中的 SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_SENDER。")
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain', 'utf-8')) # 或者 'html' 如果body是HTML

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()  # 使用TLS加密
        server.login(SMTP_USER, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, receiver_email, text)
        server.quit()
        print(f"邮件已成功发送至 {receiver_email}")
    except Exception as e:
        print(f"发送邮件失败: {e}")

def send_wechat_notification(webhook_url, message):
    """发送企业微信通知"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "msgtype": "markdown",  # 或者 "text"
        "markdown": {
            "content": message
        }
    }
    # 对于 "text" 类型:
    # payload = {
    #     "msgtype": "text",
    #     "text": {
    #         "content": message 
    #     }
    # }
    try:
        response = requests.post(webhook_url, headers=headers, json=payload)
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


# --- 主逻辑 ---
def main():
    print("开始执行代码审查流程...")

    diff_output = get_git_diff(REPO_PATH, TARGET_BRANCH, CURRENT_BRANCH)

    if diff_output is None:
        print("获取 git diff 失败，流程终止。")
        send_wechat_notification(WECHAT_WEBHOOK_URL, "自动化代码审查：获取 git diff 失败。")
        return

    if not diff_output.strip():
        print("未检测到代码变更。")
        send_email("自动化代码审查报告", "未检测到代码变更。", EMAIL_RECEIVER)
        send_wechat_notification(WECHAT_WEBHOOK_URL, "自动化代码审查：未检测到代码变更。")
        return

    # print("Git Diff 输出:\n", diff_output[:1000]) # 打印部分 diff 用于调试
    
    parsed_hunks_data_raw = parse_diff_hunks(diff_output)
    if not parsed_hunks_data_raw:
        print("未能从 diff 中解析出有效的变更片段。")
        send_wechat_notification(WECHAT_WEBHOOK_URL, "自动化代码审查：未能从 diff 中解析出有效的变更片段。")
        return

    # 应用文件过滤器
    parsed_hunks_data = []
    ignored_diff_files_count = 0
    for item in parsed_hunks_data_raw:
        if file_filter.is_allowed(item['file_path']):
            parsed_hunks_data.append(item)
        else:
            print(f"根据过滤规则，已忽略文件 '{item['file_path']}' 中的变更。")
            ignored_diff_files_count += 1
    
    if ignored_diff_files_count > 0:
        print(f"共忽略了 {ignored_diff_files_count} 个在 diff 中但被规则过滤的文件。")

    if not parsed_hunks_data:
        print("所有解析出的变更文件均被过滤规则忽略，无内容可审查。")
        send_wechat_notification(WECHAT_WEBHOOK_URL, "自动化代码审查：所有变更文件均被过滤规则忽略。")
        return

    print(f"将对 {len(parsed_hunks_data)} 个文件的变更进行审查 (已应用过滤规则)。")

    review_report_parts = []
    total_changes = len(parsed_hunks_data)
    processed_changes = 0

    for item in parsed_hunks_data:
        file_path = item['file_path']
        hunk_content = item['hunk_content']
        
        processed_changes += 1
        print(f"\n处理变更 [{processed_changes}/{total_changes}]: {file_path}")

        full_file_path_in_repo = os.path.join(REPO_PATH, file_path)
        file_content_str = ""
        try:
            if os.path.exists(full_file_path_in_repo):
                with open(full_file_path_in_repo, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content_str = f.read()
            else:
                print(f"警告: 文件 {full_file_path_in_repo} 在本地仓库中未找到，可能已被删除或路径不正确。将尝试仅使用hunk进行分析。")

        except Exception as e:
            print(f"读取文件 {full_file_path_in_repo} 失败: {e}")
            # 即使文件读取失败，也尝试继续，DeepSeek 可能仅从 hunk 中提取信息

        review_report_parts.append(f"--- 文件: {file_path} ---")

        print(f"  正在使用 DeepSeek 提取完整方法体...")
        full_method = extract_full_method_from_deepseek(file_path, hunk_content, file_content_str)

        if full_method:
            review_report_parts.append("提取到的方法/函数体:\n```\n" + full_method + "\n```\n")
            print(f"  方法体提取成功 (部分内容): {full_method[:100].strip()}...")
            
            print(f"  正在使用 DeepSeek 进行代码审查...")
            review_comments = get_code_review_from_deepseek(file_path, full_method)
            if review_comments:
                review_report_parts.append("AI 代码审查意见:\n" + review_comments + "\n")
                print(f"  代码审查完成 (部分内容): {review_comments[:100].strip()}...")
            else:
                review_report_parts.append("AI 代码审查失败或无意见。\n")
                print(f"  代码审查失败或无意见。")
        else:
            review_report_parts.append("未能提取相关方法/函数体。\n")
            print(f"  未能提取相关方法/函数体。")
        
        review_report_parts.append("\n")


    final_report = "\n".join(review_report_parts)
    report_summary = f"自动化代码审查完成。共处理 {len(parsed_hunks_data)} 个文件的变更。"
    
    print("\n--- 最终审查报告 ---")
    # print(final_report) # 完整报告可能很长，选择性打印
    print(report_summary)

    # 将报告保存到文件
    report_file_name = "code_review_issues.txt"
    # 脚本的当前工作目录就是本工程目录 /Users/yl/code-sentinel/
    # 所以直接使用文件名即可
    try:
        with open(report_file_name, 'w', encoding='utf-8') as f:
            f.write(f"自动化代码审查报告 - {CURRENT_BRANCH} vs {TARGET_BRANCH}\n")
            f.write(report_summary + "\n\n")
            f.write("详细报告:\n")
            f.write(final_report)
        print(f"审查报告已保存至: {os.path.abspath(report_file_name)}")
    except Exception as e:
        print(f"保存审查报告到文件失败: {e}")

    # 发送邮件
    email_subject = f"自动化代码审查报告 - {CURRENT_BRANCH} vs {TARGET_BRANCH}"
    send_email(email_subject, report_summary + "\n\n详细报告:\n" + final_report, EMAIL_RECEIVER)

    # 发送企业微信通知
    wechat_message = f"#### 自动化代码审查报告\n**分支**: `{CURRENT_BRANCH}` vs `{TARGET_BRANCH}`\n**状态**: {report_summary}\n请查收邮件获取详细报告。"
    send_wechat_notification(WECHAT_WEBHOOK_URL, wechat_message)

    print("\n代码审查流程结束。")

if __name__ == "__main__":
    # 确保脚本在正确的环境中运行，或者 REPO_PATH 是绝对路径
    # 如果 REPO_PATH 是相对路径，需要注意脚本的执行位置
    # 例如: os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
