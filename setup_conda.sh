#!/bin/bash
# ######################################################################
# This script sets up a Conda environment and installs the
# required dependencies for the project, including tkinter.
# Author: chongjing.luo@mail.bnu.edu.cn
# Date: 2024.08-30
# ######################################################################

# 获取本代码的路径并进入
cd "$(dirname "$0")"

# 设置 Conda 环境名称
ENV_NAME="ccsqcenv"

# 检查 Conda 是否已安装
if ! command -v conda &> /dev/null; then
    echo "Conda 未安装，正在安装 Miniconda..."

    # 下载并安装 Miniconda
    if [ "$(uname)" == "Darwin" ]; then
        curl -o miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
    elif [ "$(uname)" == "Linux" ]; then
        curl -o miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    else
        echo "不支持的操作系统: $(uname)"
        exit 1
    fi

    bash miniconda.sh -b -p $HOME/miniconda
    rm miniconda.sh

    # 初始化 Conda
    eval "$($HOME/miniconda/bin/conda shell.bash hook)"

    # 检查当前 Shell 并选择正确的配置文件
    SHELL_NAME=$(basename "$SHELL")
    if [ "$SHELL_NAME" == "zsh" ]; then
        source ~/.zshrc
    elif [ "$SHELL_NAME" == "bash" ]; then
        source ~/.bashrc
    else
        echo "未知的 shell: $SHELL_NAME，请手动 source 你的 shell 配置文件。"
    fi
fi

# 创建 Conda 环境
if conda env list | grep -q "$ENV_NAME"; then
    echo "Conda 环境 '$ENV_NAME' 已存在。"
else
    echo "正在创建 Conda 环境 '$ENV_NAME'..."
    conda create -n "$ENV_NAME" python=3.10 -y
fi

# 激活 Conda 环境
echo "激活 Conda 环境 '$ENV_NAME'..."
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

# 安装依赖
echo "正在安装依赖项..."
pip install numpy==2.0.1 pandas==2.2.2 python-dateutil==2.9.0.post0 pytz==2024.1 six==1.16.0 tzdata==2024.1

# 验证 tkinter 是否正常安装
echo "验证 tkinter..."
python -c "import tkinter; tkinter._test()" && echo "tkinter 安装成功。" || echo "tkinter 安装失败。"

# 获取 Conda 环境中的 Python 解释器路径
PYTHON_PATH=$(conda run -n $ENV_NAME which python)

# 创建 start.sh 文件
echo "正在生成 start.sh 脚本..."
echo "#!/bin/bash" > start.sh
echo "eval \"\$(conda shell.bash hook)\"" >> start.sh
echo "conda activate $ENV_NAME" >> start.sh
echo "$PYTHON_PATH $(pwd)/ccsqc.py" >> start.sh

# 确保 start.sh 是可执行的
chmod +x start.sh

echo "Setup complete. You can now start the project with bash start.sh"
