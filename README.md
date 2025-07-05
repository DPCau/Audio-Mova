# 活字乱刷术 (Audio Mova)

**活字乱刷术 (Audio Mova)** 是一款桌面应用程序，它借鉴了中国古代的“活字印刷术”思想，将音频或视频中的语音进行智能拆分，生成独立的字、词音频片段。用户可以像排版一样，在多轨道时间轴上自由拖拽、组合这些“声音活字”，进行二次创作，最终合成全新的音频。

本项目使用 Python、PyQt5 构建图形界面，并采用 `faster-whisper` 作为核心的语音识别引擎，实现高效、精准的语音切分。

## ✨ 功能特性

- **单一python文件**：安装依赖后，直接运行 `main_window.py` 文件即可，不存在导入报错。
- **智能语音切分**：自动将输入的音频/视频文件（支持多种格式）按字词切分成独立的 `.wav` 音频片段。
- **素材库管理**：按项目和拼音首字母自动分类和管理所有切分出的音频素材，方便查找。
- **多轨道时间轴**：提供可视化的多轨道时间轴，支持拖拽、复制、粘贴和删除音频块。
- **实时防重叠**：在拖动音频块时，自动检测并阻止重叠，并通过颜色变化提供直观反馈。
- ~~**自由缩放与播放**：支持时间轴的自由缩放，方便精细编辑；可随时播放、暂停和停止时间轴上的合成效果。~~**调试中**
- **灵活导出**：可将时间轴上的创作成果导出为 `.mp3` 或 `.wav` 文件。
- **跨平台运行**：支持 Windows、macOS 和 Linux。
- **本地化模型**：支持离线使用，通过第一次使用下载模型文件，后续无需在运行时连接网络。

## 📃使用可执行文件

点击[此处](https://github.com/DPCau/Audio-Mova/releases)下载并运行最新或者旧版本的可执行文件。
但仍请仔细阅读使用指南。

## 🚀 安装与运行(直接使用可执行文件可以跳过)

本项目依赖 Python 3.10 环境(不建议跨版本)。建议使用虚拟环境进行安装。

### 1. 克隆项目

```bash
git clone https://github.com/DPCau/Audio-Mova.git
cd AudioMova
```

### 2. 创建并激活虚拟环境

- **Windows/ macOS / Linux**:
  
  ```bash
  conda create -n AudioMova python=3.10
  conda activate AudioMova
  ```

### 3. 安装依赖

项目所需的依赖项已在 `requirements.txt` 文件中列出。

```bash
pip install -r requirements.txt
```

### 4. 运行程序

一切准备就绪后，运行主程序文件：

```bash
python main_window.py
```

## 📖 使用指南(!必看!)

0. **(启动前)配置环境变量与外部依赖**：
1. **ffmpeg**：如果您的电脑没有安装ffmpeg，需要手动安装[ffmpeg](https://ffmpeg.org/download.html)，这里不再赘述。
2. **huggingface**：如果您所在地区为中国大陆，需要配置huggingface环境变量至系统配置，详情请自行搜索。
    - Windows
    > 控制面板配置huggingface国内镜像源
    - macOS / Linux
    > .zshrc或者.bashrc配置huggingface国内镜像源
1.  **选择输入文件**：点击界面上方的第一个“浏览...”按钮，选择一个包含中文语音的音频或视频文件（如 `.mp3`, `.wav`, `.mp4` 等）。
2.  **选择模型**：在“模型大小”下拉菜单中，第一次运行时选择的模型会下载并放置在 `models` 文件夹中。
3.  **开始处理**：点击“开始处理”按钮。程序将开始进行语音识别和切分。处理进度会显示在进度条上。
    - 如果是首次处理文件，会拉取模型(进度见终端)，耗时会较长。
    - 如果之前已经使用过该模型，程序会自动加载`/model`下缓存。
4.  **浏览素材**：处理完成后，素材保留在`/temp`文件夹下，左侧的“素材库”会自动刷新。您可以按项目名称和拼音首字母展开，找到切分好的字词。**您也可以将手动分割的音频按文件夹规则放在`/temp`下，程序会自动识别并加载。**
5.  **拖拽创作**：从素材库中将想要的音频片段拖拽到右侧的时间轴上。
    - 您可以将其放置在任意轨道。
    - 拖动时，如果与其他音频块重叠，它会变红并无法放置。
6.  **编辑时间轴**：
    - **移动**: 直接拖动时间轴上的音频块。
    - **复制**: 右键点击音频块，选择“复制”。
    - **粘贴**: 将播放头（红色竖线）移动到目标位置，按 `Ctrl+V` (Windows/Linux) 或 `Cmd+V` (macOS) 粘贴。
    - **删除**: 右键点击音频块，选择“删除”。
7.  ~~**播放与缩放**：~~**调试中暂不可用，不影响导出**
    - ~~使用播放控件（▶, ■）来播放或停止整个时间轴的合成效果。~~
    - ~~使用下方的缩放滑块或 `+` / `-` 按钮来放大或缩小时间轴，方便进行精细调整。~~
8.  **导出**：点击菜单栏的“文件” -> “导出音频...”，选择保存路径和格式，即可导出。

## ⚠️ 注意事项

- **首次运行**: 在 macOS 上首次运行可能会有安全提示，请在“系统偏好设置” -> “安全性与隐私”中允许应用运行。
- **性能**: 处理长音频或使用大模型会消耗较多的 CPU 和内存资源，请耐心等待。在配置较低的电脑上建议使用 `base` 或 `small` 模型。
- **模型匹配**: 请确保在程序中选择的模型大小与您在 `models` 文件夹中存放的文件完全对应。

## 📦 打包(选做)
- **安装pyinstaller**
```bash
pip install pyinstaller
```
- 打包
> Windows
> ```bash
> pyinstaller --windowed --name "活字乱刷术 Audio Mova" --icon="icons/icon.png" --add-data="icons:icons" --add-data="temp:temp" --add-data="models:models" main_window.py
> ```
> macOS
> ```bash
> pyinstaller --windowed --name "活字乱刷术 Audio Mova" --icon="icons/icon.icns" --add-data="icons:icons" --add-data="temp:temp" --add-data="models:models" main_window.py
> xattr -cr dist/活字乱刷术\ Audio\ Mova.app 
> ```
- **执行**
命令执行完毕后，`PyInstaller` 会创建两个新文件夹：`build` 和 `dist`。
您最终的应用程序就在 dist 文件夹里，它是一个名为 `活字乱刷术 Audio Mova.exe`(Windows) 或者 `活字乱刷术 Audio Mova.app`(macOS) 的文件。您可以双击来运行它。