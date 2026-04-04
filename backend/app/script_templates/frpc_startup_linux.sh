#!/bin/bash

# frpc 启动脚本

FRPC_PATH="@@FRPC_PATH@@"
CONFIG_PATH="@@CONFIG_PATH@@"
PID_FILE="./frpc.pid"
LOG_FILE="./frpc.log"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "frpc 已经在运行中 (PID: $PID)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi

    echo "启动 frpc..."
    nohup "$FRPC_PATH" -c "$CONFIG_PATH" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "frpc 已启动 (PID: $(cat $PID_FILE))"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "frpc 未运行"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "停止 frpc (PID: $PID)..."
        kill "$PID"
        rm -f "$PID_FILE"
        echo "frpc 已停止"
    else
        echo "frpc 进程不存在"
        rm -f "$PID_FILE"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "frpc 正在运行 (PID: $PID)"
            return 0
        else
            echo "frpc 未运行（但 PID 文件存在）"
            return 1
        fi
    else
        echo "frpc 未运行"
        return 1
    fi
}

restart() {
    stop
    sleep 2
    start
}

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
    status)
        status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0
