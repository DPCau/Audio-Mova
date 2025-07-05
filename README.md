# 活字乱刷术 (Audio Mova)

**活字乱刷术 (Audio Mova)** 是一款桌面应用程序，它借鉴了中国古代的“活字印刷术”思想，将音频或视频中的语音进行智能拆分，生成独立的字、词音频片段。用户可以像排版一样，在多轨道时间轴上自由拖拽、组合这些“声音活字”，进行二次创作，最终合成全新的音频。

本项目使用 Python、PyQt5 构建图形界面，并采用 `faster-whisper` 作为核心的语音识别引擎，实现高效、精准的语音切分。

## ✨ 功能特性

- **智能语音切分**：自动将输入的音频/视频文件（支持多种格式）按字词切分成独立的 `.wav` 音频片段。
- **素材库管理**：按项目和拼音首字母自动分类和管理所有切分出的音频素材，方便查找。
- **多轨道时间轴**：提供可视化的多轨道时间轴，支持拖拽、复制、粘贴和删除音频块。
- **实时防重叠**：在拖动音频块时，自动检测并阻止重叠，并通过颜色变化提供直观反馈。
- **自由缩放与播放**：支持时间轴的自由缩- 放，方便精细编辑；可随时播放、暂停和停止时间轴上的合成效果。
- **灵活导出**：可将时间轴上的创作成果导出为 `.mp3` 或 `.wav` 文件。
- **跨平台运行**：支持 Windows、macOS 和 Linux。
- **本地化模型**：支持离线使用，通过手动下载模型文件，无需在运行时连接网络。

## 🚀 安装与运行

本项目依赖 Python 3.10 环境(不建议跨版本)。建议使用虚拟环境进行安装。

### 1. 克隆项目

```bash
git clone 
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

### 4. 手动下载模型文件

为了实现离线运行并避免程序自动下载，我们推荐您**手动下载** `faster-whisper` 模型。

`faster-whisper` 支持多种大小的模型，体积越小速度越快，但精度可能略低；体积越大精度越高，但更消耗资源。常用模型如下：

- `tiny`
- `base` (推荐入门)
- `small`
- `medium`
- `large-v3` (最高精度)

请根据您的需求，点击超链接访问以下 Hugging Face 仓库地址

- [tiny](https://huggingface.co/Systran/faster-whisper-tiny/tree/main)
- [base](https://huggingface.co/Systran/faster-whisper-base/tree/main)
- [small](https://huggingface.co/Systran/faster-whisper-small/tree/main)
- [medium](https://huggingface.co/Systran/faster-whisper-medium/tree/main)
- [large-v3](https://huggingface.co/Systran/faster-whisper-large-v3/tree/main)

**下载步骤**:
- huggface-cli下载
> 请自行使用huggface-cli下载放入models/
- 手动下载(不推荐)
    1.  进入对应的模型仓库页面。
    2.  点击 "Files and versions" 选项卡。
    3.  下载该模型所需的所有文件，通常包括：
        - `config.json`
        - `model.bin`
        - `tokenizer.json`
        - `vocabulary.txt`
        - 其他可能的文件...
    4.  将所有下载的文件**直接**放入项目根目录下的 `models` 文件夹中。

**示例**：如果您下载了 `base` 和 `large-v3` 模型，您的目录结构应如下所示：

```
AudioMova/
├── models/
│   ├── models--Systran--faster-whisper-base/
│   │   ├── config.json
│   │   ├── model.bin
│   │   ├── tokenizer.json
│   │   └── vocabulary.txt
│   │
│   └── models--Systran--faster-whisper-large-v3/
│       ├── config.json
│       ├── model.bin
│       ├── tokenizer.json
│       └── vocabulary.txt
│
├── main_final_v13_drag_fixed_definitively.py
├── requirements.txt
└── README.md
```

### 5. 运行程序

一切准备就绪后，运行主程序文件：

```bash
python main_window.py
```

## 📖 使用指南

1.  **选择输入文件**：点击界面上方的第一个“浏览...”按钮，选择一个包含中文语音的音频或视频文件（如 `.mp3`, `.wav`, `.mp4` 等）。
2.  **选择模型**：在“模型大小”下拉菜单中，选择您已手动下载并放置在 `models` 文件夹中的模型。**请确保选择的模型与您下载的文件一致**，否则会弹窗提示错误。
3.  **开始处理**：点击“开始处理”按钮。程序将开始进行语音识别和切分。处理进度会显示在进度条上。
    - 如果是首次处理该文件，耗时会较长。
    - 如果之前处理过，程序会自动加载缓存，速度很快。
4.  **浏览素材**：处理完成后，左侧的“素材库”会自动刷新。您可以按项目名称和拼音首字母展开，找到切分好的字词。
5.  **拖拽创作**：从素材库中将想要的音频片段拖拽到右侧的时间轴上。
    - 您可以将其放置在任意轨道。
    - 拖动时，如果与其他音频块重叠，它会变红并无法放置。
6.  **编辑时间轴**：
    - **移动**: 直接拖动时间轴上的音频块。
    - **复制**: 右键点击音频块，选择“复制”。
    - **粘贴**: 将播放头（红色竖线）移动到目标位置，按 `Ctrl+V` (Windows/Linux) 或 `Cmd+V` (macOS) 粘贴。
    - **删除**: 右键点击音频块，选择“删除”。
    - **试听**: 双击时间轴上的音频块可单独播放它。
7.  **播放与缩放**：
    - 使用播放控件（▶, ■）来播放或停止整个时间轴的合成效果。
    - 使用下方的缩放滑块或 `+` / `-` 按钮来放大或缩小时间轴，方便进行精细调整。
8.  **导出作品**：点击菜单栏的“文件” -> “导出音频...”，选择保存路径和格式，即可将您的创作导出。

## ⚠️ 注意事项

- **首次运行**: 在 macOS 上首次运行可能会有安全提示，请在“系统偏好设置” -> “安全性与隐私”中允许应用运行。
- **性能**: 处理长音频或使用大模型会消耗较多的 CPU 和内存资源，请耐心等待。在配置较低的电脑上建议使用 `base` 或 `small` 模型。
- **模型匹配**: 请确保在程序中选择的模型大小与您在 `models` 文件夹中存放的文件完全对应。