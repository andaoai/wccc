# PostgreSQL 数据库使用文档

## 概述

本项目使用 PostgreSQL 16 数据库，通过 Docker Compose 进行部署。数据库数据存储在本地目录中，便于备份和管理。

## 配置信息

- **数据库名称**: `wccc`
- **用户名**: `postgres`
- **密码**: 在 `.env` 文件中配置
- **端口**: `5433` (避免与系统默认 PostgreSQL 冲突)
- **数据存储路径**: `./data/postgres/`

## 快速开始

### 1. 启动数据库

```bash
# 启动 PostgreSQL 服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs postgres
```

### 2. 连接数据库

#### 方式一：使用 Docker 容器内客户端
```bash
# 连接到数据库
docker-compose exec postgres psql -U postgres -d wccc
```

#### 方式二：使用本地客户端
```bash
# 需要先安装 postgresql-client
psql -h localhost -p 5433 -U postgres -d wccc
```

#### 方式三：使用 GUI 工具
- **主机**: `localhost`
- **端口**: `5433`
- **用户名**: `postgres`
- **密码**: 在 `.env` 文件中配置
- **数据库**: `wccc`

## 环境变量配置

数据库配置存储在 `.env` 文件中：

```env
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=wccc
POSTGRES_PORT=5433
```

**重要**: 请将 `your_secure_password_here` 修改为安全的密码。

## 数据持久化

- 数据库文件存储在 `./data/postgres/` 目录
- 该目录已添加到 `.gitignore` 中，不会被 Git 跟踪
- 备份数据只需复制此目录即可

## 数据库初始化

- 初始化脚本位于 `./init.sql`
- 在容器首次启动时自动执行
- 可用于创建初始用户、表结构等

## 常用命令

### 容器管理
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart postgres

# 进入容器
docker-compose exec postgres bash
```

### 数据库操作
```bash
# 连接数据库
docker-compose exec postgres psql -U postgres -d wccc

# 创建新数据库
docker-compose exec postgres createdb -U postgres new_database

# 备份数据库
docker-compose exec postgres pg_dump -U postgres wccc > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U postgres wccc < backup.sql
```

## 连接字符串格式

### Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    user="postgres",
    password="your_password",
    database="wccc"
)
```

### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine

engine = create_engine("postgresql://postgres:your_password@localhost:5433/wccc")
```

### Node.js
```javascript
const { Client } = require('pg');

const client = new Client({
  host: 'localhost',
  port: 5433,
  user: 'postgres',
  password: 'your_password',
  database: 'wccc'
});
```

### JDBC (Java)
```
jdbc:postgresql://localhost:5433/wccc?user=postgres&password=your_password
```

## 健康检查

数据库服务配置了健康检查，可以通过以下命令查看状态：

```bash
# 检查服务健康状态
docker-compose ps

# 查看健康检查日志
docker-compose logs postgres | grep health
```

## 故障排除

### 端口冲突
如果遇到端口冲突，可以修改 `.env` 文件中的 `POSTGRES_PORT`：

```bash
# 修改端口
echo "POSTGRES_PORT=5434" >> .env

# 重启服务
docker-compose down && docker-compose up -d
```

### 权限问题
如果遇到数据目录权限问题：

```bash
# 修复数据目录权限
sudo chown -R 999:999 ./data/postgres/
sudo chmod -R 755 ./data/postgres/

# 重启服务
docker-compose restart postgres
```

### 完全重置
如需完全重置数据库：

```bash
# 停止服务
docker-compose down

# 删除数据目录
rm -rf ./data/postgres/

# 重新启动
docker-compose up -d
```

## 监控和日志

### 查看实时日志
```bash
docker-compose logs -f postgres
```

### 查看数据库活动
```sql
-- 连接到数据库后执行
SELECT * FROM pg_stat_activity;
```

### 查看数据库大小
```sql
SELECT
    datname as database_name,
    pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database
WHERE datname = 'wccc';
```

## 安全建议

1. **密码安全**: 使用强密码，不要提交到版本控制系统
2. **网络访问**: 考虑只在本地网络暴露数据库端口
3. **用户权限**: 为应用创建专用数据库用户，避免使用 postgres 用户
4. **定期备份**: 设置定期备份策略
5. **更新维护**: 及时更新 PostgreSQL 镜像版本

## 扩展配置

如需添加 PostgreSQL 扩展，可以修改 `init.sql` 文件：

```sql
-- 在 init.sql 中添加扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
```