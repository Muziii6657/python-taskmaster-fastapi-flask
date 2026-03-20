# 本实验原定用config.py来存储配置，但为了简化结构，我们直接在database.py中定义了数据库连接字符串和相关配置。
# 如果你想把配置单独放在config.py中，可以按照以下方式修改：
# config.py 
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 你可以在 .env 文件中设置 DATABASE_URL 环境变量，例如：
# DATABASE_URL="mysql://root:password@localhost:3306/task_db?charset=utf8mb4"