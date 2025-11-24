## 基本信息
病案号是 6 位

## 数据流

## 启动脚本
ps -ef|grep app.py | awk '{print $2}' |xargs kill 
nohup streamlit run app.py > logs/parse_data_serve_1105.log 2>&1 &


# 构建镜像
# 容器--》镜像--》离线压缩包--》加载离线压缩包
docker commit <容器ID或容器名> <新镜像名>:<tag>
docker save -o <保存路径/文件名.tar> <镜像名>:<tag>
docker load -i <文件名.tar>


docker build -t parse-data-service:v1.0.0 .

docker run -d -p 8501:8501 \
  -v $(pwd)/conf:/app/conf \
  --name parse-data-service \
  parse-data-service:v1.0.0

