# 使用完整的 Python 3.10 镜像
FROM python:3.10

# 设置工作目录
WORKDIR /app

# 安装 Tkinter 和必要的依赖库，包括 xauth 和 xvfb
RUN apt-get update && apt-get install -y \
    python3-tk \
    tk-dev \
    tcl-dev \
    tcl8.6 \
    tk8.6 \
    tk8.6-blt2.5 \
    libx11-6 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libgl1-mesa-glx \
    libxft2 \
    xvfb \
    xauth \
    && apt-get clean

# 将 requirements.txt 复制到容器中
COPY requirements.txt .

# 安装 Python 依赖包
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目文件到容器中
COPY . .

# 调试信息：显示 DISPLAY 环境变量
RUN echo "DISPLAY: $DISPLAY"

# 使用 Xvfb 启动虚拟显示环境并运行应用程序
CMD ["xvfb-run", "-a", "-s", "-screen 0 1024x768x24", "python", "ccsqc.py"]

