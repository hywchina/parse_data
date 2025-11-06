#!/bin/bash

# 获取当前时间戳
LOG_FILE="logs/parse_data_serve_$(date +"%Y%m%d_%H%M").log"

# 创建日志目录
mkdir -p logs

# 启动应用
start() {
    echo "启动应用..."
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo "安装虚拟环境和依赖..."
        virtualenv -p python3.10 venv
        . venv/bin/activate  # 使用点号替代source
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        . venv/bin/activate  # 使用点号替代source
    fi
    
    # 停止现有进程
    stop
    
    # 启动新进程
    nohup streamlit run app.py --server.headless true > "$LOG_FILE" 2>&1 &
    echo "应用已启动，日志: $LOG_FILE"
    echo "进程PID: $!"
}

# 停止应用
stop() {
    echo "停止应用..."
    pids=$(ps -ef | grep "streamlit run app.py" | grep -v grep | awk '{print $2}')
    if [ -n "$pids" ]; then
        echo "找到进程: $pids"
        echo $pids | xargs kill
        sleep 2
    else
        echo "未找到运行中的进程"
    fi
}

# 重启应用
restart() {
    stop
    sleep 2
    start
}

# 根据参数执行对应操作
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart}"
        echo "示例:"
        echo "  $0 start   # 启动应用"
        echo "  $0 stop    # 停止应用"
        echo "  $0 restart # 重启应用"
        exit 1
        ;;
esac