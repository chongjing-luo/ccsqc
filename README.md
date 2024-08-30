# CCSQC: A Comprehensive Quality Control Tool for MRI Data
* author: Chongjing Luo (chongjing.luo@mail.bnu.edu.cn)
* date: 2024-08-30
* version: 1.0


## 项目简介

CCSQC 是一个用于脑影像数据质量控制的工具，支持多种质量控制类型，包括头动、颅骨去除、重建和配准。该工具通过GUI界面提供了直观的评分和结果查看功能。

## 功能特点

- 路径结构基于BIDS和CCS。
- 支持头动（Head motion）、颅骨去除（Skull stripping）、重建（Reconstruction）、配准（Registration）四种质量控制类型。
- 直观的评分界面，支持多种质量评分和注释。
- 通过多种图像查看器（如MRIcron、Freeview、FSL等）进行图像展示。
- 支持结果的保存、加载和导出。

## 环境配置

### 1. 克隆项目

首先，克隆此GitHub仓库到本地：

```bash
cd /path/to/store/ccsqc
git clone https://github.com/chongjing-luo/ccsqc.git
```

### 2. 安装依赖

进入项目根目录，运行以下命令创建虚拟环境并安装依赖：
```bash
bash setup.sh
```
您也可以运行以下命令创建conda环境并安装依赖：
```bash
bash setup_conda.sh
```

该命令会自动安装项目所需的Python环境和依赖包。同时生成一个名为`start.sh`的脚本，用于启动项目。

### 3. 运行项目

安装完成后，运行以下命令启动项目：

```bash
# 可以通过执行以下命令启动项目，该命令会自动选择合适的Python环境
start.sh
```

```bash
# 您可查看start.sh文件中的pthon解释器路径，使用该路径运行`ccsqc.py`文件：
VENV_ccsqc/bin/python ccsqc.py
```


