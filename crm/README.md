# Cordys CRM Docker部署

## 目录结构
```
crm/
├── docker-compose.yml    # Docker Compose配置文件
├── .env                  # 环境变量配置
├── cordys/               # Cordys数据目录（自动创建）
└── README.md             # 说明文档
```

## 部署方法

1. 进入crm目录：
```bash
cd crm
```

2. 启动服务：
```bash
docker-compose up -d
```

3. 查看服务状态：
```bash
docker-compose ps
```

4. 查看日志：
```bash
docker-compose logs -f cordys-crm
```

## 端口说明
- **8081**: 主要服务端口
- **8082**: 辅助服务端口

## 配置修改
编辑 `.env` 文件可以修改端口映射等配置。

## 停止服务
```bash
docker-compose down
```

## 数据持久化
所有数据都保存在 `./cordys` 目录下，映射到容器的 `/opt/cordys` 路径。

## 重启服务
```bash
docker-compose restart
```