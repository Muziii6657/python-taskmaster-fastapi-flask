# **TaskMaster: 基于 FastAPI、Flask 和 Pydantic 的个人任务管理系统**

- TaskMaster 是一个功能强大的个人任务管理系统，采用现代化的技术栈构建，提供高效的任务创建、管理和可视化功能。
  
---
！！！请点击并阅读 AI赋能优化说明.md ，了解更新内容！！！
---

## 技术栈

- **后端 API:**

- [FastAPI](https://fastapi.tiangolo.com/): 高性能的 Web 框架，用于构建 RESTful API 服务。
- [Pydantic v2](https://docs.pydantic.dev/latest/): 提供强大的数据验证和序列化能力，确保 API 的健壮性。

*   [SQLAlchemy](https://www.sqlalchemy.org/): 强大的 ORM 工具，用于与数据库交互。
*   **管理前端:**
    *   [Flask](https://flask.palletsprojects.com/): 轻量级的 Web 框架，用于构建简单的管理界面，与 FastAPI API 集成。
*   **数据库:**
    *   [MySQL](https://www.mysql.com/): 关系型数据库，用于持久化存储任务数据。
*   **前端技术 (用于 Flask 页面):**
    *   [HTML](https://developer.mozilla.org/en-US/docs/Web/HTML)
    *   [CSS](https://developer.mozilla.org/en-US/docs/Web/CSS)
    *   [JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript) (用于交互和AJAX请求)
    *   [Jinja2](https://jinja.palletsprojects.com/): Flask 的模板引擎。

## 功能亮点

*   **RESTful API:** 提供完整的 CRUD (Create, Read, Update, Delete) 接口，用于任务管理。
*   **严格的数据验证:** 通过 Pydantic v2 对任务数据进行强制验证，包括：
    *   标题不能为空。
    *   日期格式合法。
    *   状态只能是 `todo`、`doing` 或 `done`。
*   **任务筛选:** 支持按状态和截止日期范围筛选任务。
*   **标准化 JSON 响应:** 所有 API 响应都遵循一致的 JSON 格式。
*   **可选管理后台:** 提供一个简单的 Flask Web 界面，用于直观地展示、创建、编辑和删除任务，并支持任务排序。

## 项目结构

task_manager_api/
├── venv/ # 虚拟环境
├── app_flask.py # Flask 应用 (管理后台)
├── config.py # 项目配置 (如数据库 URL)
├── database.py # 数据库连接、Session工厂、ORM模型基类
├── main.py # FastAPI 应用主接口服务
├── models.py # Pydantic 数据模型 和 SQLAlchemy ORM模型
├── requirements.txt # 项目依赖列表
├── task_data.json # 用于测试的 JSON 数据文件
├── templates/ # Flask 页面模板
│ ├── index.html # 任务列表页
│ ├── create_task.html # 创建任务页
│ └── edit_task.html # 编辑任务页
└── README.md # 本文件

---



## 如何运行

### 1. 环境准备

*   **安装 Python:** 确保已安装 Python 3.7+。
*   **安装 MySQL:** 确保 MySQL 服务器正在运行，**并创建一个用于存储任务的数据库（例如 `task_db`）**。
*   **配置数据库连接：**
    *   修改 `database.py` 中的 `SQLALCHEMY_DATABASE_URL` 为你的 MySQL 连接字符串。
    *   确保 MySQL 用户名、密码、主机、端口和数据库名都已正确配置。
    *   **安全性提示：** 生产环境中应使用环境变量管理敏感信息。

### 2. **使用步骤** 

1、打开终端，进入目标文件夹  eq：cd D:\summary\task_manager_api
2、输入  .\venv\Scripts\Activate.ps1  运行已安装好的venu虚拟环境
3、输入   uvicorn main:app --reload  启动main方法（后端运行）
4、浏览器进入  http://127.0.0.1:8000/docs  进入后端页面`

![image-20260320134426522](readme.assets/image-20260320134426522.png)

### 3.后端测试步骤

#### 方式 1：使用 curl.exe

- **新建终端**，**进入项目根目录**
- **激活虚拟环境**

- POST /tasks/ (创建任务，含中文 JSON，Windows PowerShell 5 稳定写法)
```powershell
$json = @'
{
  "title": "学习 FastAPI",
  "description": "今天完成接口测试",
  "status": "todo",
  "due_date": "2026-03-20T04:29:00.170Z"
}
'@

Set-Content -Path .\payload.json -Value $json -Encoding utf8    

#（payload只是示例名称）

#- Z 表示 UTC时间，中国时间是UTC+8

curl.exe -X POST "http://127.0.0.1:8000/tasks/" `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-binary "@payload.json"
```

注意：虽然上述示例可以直接复制到终端运行，在 Windows PowerShell 5 中，直接把多行中文字符串作为 `curl.exe` 参数传递，常见现象是 JSON 被拆坏或中文乱码。先写入 UTF-8 文件再通过 `@payload.json` 发送最稳定。

- GET /tasks/ (获取所有任务)
```powershell
curl.exe "http://127.0.0.1:8000/tasks/"
```

- GET /tasks/ (按状态过滤)

```powershell
curl.exe "http://127.0.0.1:8000/tasks/?status=todo"
```

- GET /tasks/{task_id} (假设 ID 是 1)
```powershell
curl.exe "http://127.0.0.1:8000/tasks/1"
```
---

- PUT /tasks/{task_id} (更新任务，假设 ID 是 1)  ！！！！实际操作时记得修改ID（主键）
```powershell
$json = @'
{
  "status": "doing",
  "description": "进展顺利，继续推进"
}
'@

Set-Content -Path .\payload.json -Value $json -Encoding utf8

curl.exe -X PUT "http://127.0.0.1:8000/tasks/1" `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-binary "@payload.json"
```
---

- DELETE /tasks/{task_id} (删除任务，假设 ID 是 1)
```powershell
curl.exe -X DELETE "http://127.0.0.1:8000/tasks/1"
```

#### 方式 2：使用 Invoke-RestMethod
```powershell
$body = @{
  title = "学习 FastAPI"
  description = "用 PowerShell 调接口"
  status = "todo"
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/tasks/" -ContentType "application/json; charset=utf-8" -Body $body
```

#### **方式 3：http://127.0.0.1:8000/docs中实现**

- **点击POST端点**

![image-20260320134647944](readme.assets/image-20260320134647944.png)

- 按下  Try it out  组件

![image-20260320134738134](readme.assets/image-20260320134738134.png)

- 根据示例模板要填充的任务内容

![image-20260320134821685](readme.assets/image-20260320134821685.png)

- 点击Execute结束，出现curl和Request URL

![image-20260320134913244](readme.assets/image-20260320134913244.png)

- 在终端中添加后（方法一）点击 GET/tasks 端点获取（第一个查询所有，第二个查询对应任务号的单个任务）

![image-20260320135130198](readme.assets/image-20260320135130198.png)

- 同样按下try it out，选择任务状态status后，点击execute确认进行获取

![image-20260320135323890](readme.assets/image-20260320135323890.png)

![image-20260320135406681](readme.assets/image-20260320135406681.png)

#### **剩余端点同理使用，不做过多赘述**



---

### 4.前端启动步骤

- **新建终端**（后端运行中）

- **运行flask_api.py文件**
- ![image-20260320133903650](readme.assets/image-20260320133903650.png)

- 根据提示Running on http://127.0.0.1:5000

![image-20260320133929837](readme.assets/image-20260320133929837.png)

- 进入后即可开始任务管理

### 功能点

- **新建任务**

![image-20260320134043917](readme.assets/image-20260320134043917.png)

![image-20260320134058861](readme.assets/image-20260320134058861.png)

- 上下位移order序列

![image-20260320134157628](readme.assets/image-20260320134157628.png)

- edit编辑任务内容
- delete删除任务

**所有功能前后端同步**

---



## 你可能遇到：中文显示为   ’? ‘  ，解决方法如下

这个问题通常有两层：
1. 终端编码不一致（输入/显示乱码）
2. 数据库编码不是 utf8mb4（入库后变成 ?，查出来也还是 ?）

### A. 先修终端编码（PowerShell）
在当前终端执行：
```powershell
chcp 65001
[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = "1"
```

建议使用 Windows Terminal + PowerShell 7，并将字体设置为支持中文（如 Cascadia Mono + 中文字体回退、等宽更纱黑体等）。

### B. 修数据库链路编码（关键）
项目里数据库连接已建议使用：
```python
SQLALCHEMY_DATABASE_URL = "mysql://root:password@localhost:3306/task_db?charset=utf8mb4"
```

并在 MySQL 中检查与修复字符集：
```sql
SHOW VARIABLES LIKE 'character_set%';
SHOW CREATE DATABASE task_db;
SHOW TABLE STATUS WHERE Name = 'tasks';
```

若不是 utf8mb4，执行：
```sql
ALTER DATABASE task_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE tasks CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 还可能遇到的问题：

​	1.无法输入中文，

- 当前是 Windows PowerShell 5.1，这一版对原生程序传中文参数经常出问题。（已修复
- 数据库配置问题，无法识别中文。根据指令修复
2. ID做为数据库的主键，无法直接

3. 为什么 PowerShell 下 curl 会报错？

   在 Windows PowerShell 中，`curl` 默认是 `Invoke-WebRequest` 的别名，不是 Linux/macOS 的 `curl`。
   另外，示例里使用的 `\` 续行符也是 Bash 语法，PowerShell 不能直接用

   在 PowerShell 中的正确写法

   - 方式 1：显式使用 `curl.exe`（推荐，和你在 Linux 的习惯接近）
   - 方式 2：使用 PowerShell 原生命令 `Invoke-RestMethod
