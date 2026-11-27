import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    
    # MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'sharehosting')
    MYSQL_CURSORCLASS = 'DictCursor'
    
    # Hosting
    HOSTING_ROOT = os.environ.get('HOSTING_ROOT', '/www/wwwroot')
    
    # Allowed commands di terminal (whitelist)
    ALLOWED_COMMANDS = [
        'git', 'php', 'composer', 'npm', 'node', 'python', 'python3',
        'pip', 'pip3', 'spark', 'artisan', 'ls', 'cd', 'pwd', 'mkdir',
        'rm', 'cp', 'mv', 'cat', 'touch', 'chmod', 'chown', 'grep',
        'find', 'echo', 'env', 'export', 'unzip', 'zip', 'tar', 'curl',
        'wget', 'nano', 'vi', 'vim', 'clear', 'whoami', 'which',
        'bash', 'sh'
    ]
