# database.py
from sqlalchemy.orm import declarative_base  # 从 sqlalchemy.orm 导入 declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, text

# ----------------------------------------------------------------------------
# 数据库连接配置 

# 格式: "mysql://<username>:<password>@<host>:<port>/<database_name>?charset=utf8mb4"
# 示例: "mysql://root:mypassword@localhost:3306/task_db?charset=utf8mb4"
# 这里为了演示，我们先直接写入，请务必修改成你自己的配置
# 如果你本地MySQL没有密码，或者数据库名是默认的，请相应修改
SQLALCHEMY_DATABASE_URL = "mysql://root:henu@localhost:3306/task_db?charset=utf8mb4"

# ----------------------------------------------------------------------------
# SQLAlchemy Engine 和 SessionLocal 创建

# create_engine: 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False} # 如果你之后想用SQLite，可以加上
)

# SessionLocal: 创建一个数据库会话工厂
# autocommit=False: 事务不会自动提交，需要手动调用 db.commit()
# autoflush=False: 对象不会在执行查询前自动刷新到数据库，可以更精细控制
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# declarative_base: 创建一个基础类，ORM模型将继承自它
# 这个 Base 应该在 models.py 中被导入并使用，这样 SQLAlchemy 知道哪些类是模型
Base = declarative_base()


# ----------------------------------------------------------------------------
# 数据库会话依赖函数 (用于FastAPI)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() # 确保每次请求结束后关闭数据库会话

# ----------------------------------------------------------------------------
# 数据库初始化函数 (在main.py中调用)

def init_db():
    # 导入你的 ORM 模型类，这样 Base.metadata 才能发现它们
    # !!! 这是一个关键步骤：确保你的 models.py 已经定义了继承自 Base 的模型 !!!
    import models # 假设你的模型定义在同级目录的 models.py 文件中

    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized.")


def ensure_task_order_column():
    """Add and backfill tasks.order for older schemas that predate ordering support."""
    inspector = inspect(engine)
    if not inspector.has_table("tasks"):
        return

    columns = {col["name"] for col in inspector.get_columns("tasks")}
    with engine.begin() as connection:
        if "order" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN `order` INTEGER NOT NULL DEFAULT 0"))

        rows = connection.execute(text("SELECT id, `order` FROM tasks")).fetchall()
        sorted_rows = sorted(
            rows,
            key=lambda item: (
                item[1] if item[1] is not None and item[1] > 0 else 10**9,
                item[0],
            ),
        )

        for index, row in enumerate(sorted_rows, start=1):
            if row[1] != index:
                connection.execute(
                    text("UPDATE tasks SET `order` = :new_order WHERE id = :task_id"),
                    {"new_order": index, "task_id": row[0]},
                )
