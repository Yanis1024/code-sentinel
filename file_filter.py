import os

class FileFilter:
    def __init__(self, ignored_folders=None, allowed_extensions=None, ignored_files=None):
        """
        初始化文件过滤器。
        :param ignored_folders: 要忽略的文件夹列表 (相对于仓库根目录)。例如: ["Pods/", "node_modules/"]
        :param allowed_extensions: 允许的文件扩展名列表。例如: [".py", ".js"]。如果为 None 或空列表，则不按扩展名过滤。
        :param ignored_files: 要忽略的特定文件列表 (相对于仓库根目录)。例如: [".DS_Store"]
        """
        self.ignored_folders = [os.path.normpath(folder).rstrip(os.sep) + os.sep for folder in ignored_folders] if ignored_folders else []
        self.allowed_extensions = [ext.lower() for ext in allowed_extensions] if allowed_extensions else []
        self.ignored_files = [os.path.normpath(f) for f in ignored_files] if ignored_files else []

    def is_allowed(self, file_path):
        """
        检查文件路径是否允许被处理。
        :param file_path: 相对于仓库根目录的文件路径。
        :return: 如果文件允许处理则返回 True，否则返回 False。
        """
        normalized_file_path = os.path.normpath(file_path)

        # 1. 检查是否是明确忽略的文件
        if normalized_file_path in self.ignored_files:
            return False

        # 2. 检查是否在忽略的文件夹内
        for ignored_folder_prefix in self.ignored_folders:
            if normalized_file_path.startswith(ignored_folder_prefix):
                return False
        
        # 3. 如果指定了允许的扩展名，则检查文件扩展名
        if self.allowed_extensions:
            _, ext = os.path.splitext(normalized_file_path)
            if ext.lower() not in self.allowed_extensions:
                return False
        
        # 如果通过所有检查，则文件是允许的
        return True