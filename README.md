## 基本信息
病案号是 6 位

## 数据流

## 启动脚本
ps -ef|grep app.py | awk '{print $2}' |xargs kill 
nohup streamlit run app.py > logs/parse_data_serve_1105.log 2>&1 &


# 构建镜像
docker build -t parse-data-service:latest .

docker run -d -p 8501:8501 --name parse-data-service parse-data-service:latest