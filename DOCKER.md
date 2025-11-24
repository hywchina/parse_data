# Docker 部署说明

## 构建镜像

在 `parse_data` 目录下执行：

```bash
docker build -t parse-data-service:latest .
```

## 运行容器

### 方式一：使用 docker run

```bash
docker run -d \
  --name parse-data-service \
  -p 8501:8501 \
  -v $(pwd)/data_00_ori:/app/data_00_ori \
  -v $(pwd)/data_01_csv:/app/data_01_csv \
  -v $(pwd)/data_02_pdf:/app/data_02_pdf \
  -v $(pwd)/data_03_json:/app/data_03_json \
  -v $(pwd)/data_04_summary_txt:/app/data_04_summary_txt \
  -v $(pwd)/data_05_final_pdf:/app/data_05_final_pdf \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/temp:/app/temp \
  -v $(pwd)/conf:/app/conf \
  -e TZ=Asia/Shanghai \
  parse-data-service:latest
```

### 方式二：使用 docker-compose（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

## 访问服务

服务启动后，在浏览器访问：

```
http://localhost:8501
```

## 容器管理

```bash
# 查看运行状态
docker ps | grep parse-data

# 查看日志
docker logs -f parse-data-service

# 进入容器
docker exec -it parse-data-service /bin/bash

# 停止容器
docker stop parse-data-service

# 删除容器
docker rm parse-data-service

# 删除镜像
docker rmi parse-data-service:latest
```

## 数据持久化

以下目录通过 volume 映射到宿主机，数据会持久化保存：
- `data_00_ori/` - 原始数据
- `data_01_csv/` - CSV 数据
- `data_02_pdf/` - PDF 文件
- `data_03_json/` - JSON 数据
- `data_04_summary_txt/` - 文本报告
- `data_05_final_pdf/` - 最终 PDF
- `logs/` - 日志文件
- `temp/` - 临时文件
- `conf/` - 配置文件

## 注意事项

1. 确保宿主机端口 8501 未被占用
2. 首次运行会自动创建所需的数据目录
3. 配置文件修改后需要重启容器生效
4. 建议定期清理 temp 目录和旧日志文件

## 镜像推送（可选）

如需推送到镜像仓库：

```bash
# 标记镜像
docker tag parse-data-service:latest your-registry.com/parse-data-service:latest

# 推送镜像
docker push your-registry.com/parse-data-service:latest
```
