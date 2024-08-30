#!/bin/bash

# 设置虚拟环境名称
VENV_NAME="ccsqc"

# 检查操作系统类型
OS_TYPE=$(uname)

# 检查并安装 python3.10-venv 或者 python3.10
if [ "$OS_TYPE" == "Linux" ]; then
    if ! dpkg -l | grep -q python3.10-venv; then
        echo "Linux: python3.10-venv 未安装，正在安装..."
        sudo apt update
        sudo apt install -y python3.10-venv
    else
        echo "Linux: python3.10-venv 已安装。"
    fi
elif [ "$OS_TYPE" == "Darwin" ]; then
    if ! brew list | grep -q python@3.10; then
        echo "MacOS: python3.10 未安装，正在安装..."
        brew update
        brew install python@3.10
    else
        echo "MacOS: python3.10 已安装。"
    fi

    # 安装 Tkinter 依赖
    if ! brew list | grep -q python-tk@3.10; then
        echo "MacOS: python-tk@3.10 未安装，正在安装..."
        brew install python-tk@3.10
    else
        echo "MacOS: python-tk@3.10 已安装。"
    fi
else
    echo "不支持的操作系统: $OS_TYPE"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "$VENV_NAME" ]; then
    echo "正在创建虚拟环境..."
    python3.10 -m venv $VENV_NAME
else
    echo "虚拟环境已存在。"
fi

# 激活虚拟环境
source $VENV_NAME/bin/activate

# 确保 pip 已更新
pip install --upgrade pip

# 安装依赖
echo "正在安装依赖项..."
pip install -r requirements.txt

# 获取 Python 解释器的路径
PYTHON_PATH=$(which python)

# 创建 start.sh 文件
echo "正在生成 start.sh 脚本..."
echo "#!/bin/bash" > start.sh
echo "source $(pwd)/$VENV_NAME/bin/activate" >> start.sh
echo "$PYTHON_PATH $(pwd)/ccsqc.py" >> start.sh

# 确保 start.sh 是可执行的
chmod +x start.sh

echo "Setup complete. You can now start the project with bash start.sh"
