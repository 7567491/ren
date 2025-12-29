#!/bin/bash
# 重启API服务器脚本

echo "正在重启API服务器..."

# 查找并杀死旧进程
OLD_PID=$(ps aux | grep "/home/wave/py/api_server.py" | grep -v grep | awk '{print $2}')

if [ -n "$OLD_PID" ]; then
    echo "发现旧进程: PID $OLD_PID"
    kill $OLD_PID
    sleep 2

    # 检查是否成功杀死
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "强制杀死进程..."
        kill -9 $OLD_PID
    fi

    echo "✅ 旧进程已停止"
else
    echo "ℹ️  未发现运行中的API服务器"
fi

# 启动新进程
echo "正在启动新的API服务器..."
cd /home/wave
source venv/bin/activate
nohup python3 py/api_server.py > logs/api_server.log 2>&1 &

NEW_PID=$!
echo "✅ API服务器已启动: PID $NEW_PID"
echo "日志文件: logs/api_server.log"
echo ""
echo "检查服务器状态："
sleep 3
curl -s http://localhost:18000/health | python3 -m json.tool || echo "⚠️  服务器可能还在启动中，请稍候..."
