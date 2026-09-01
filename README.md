# 🎓 AI 学术面试教练

面向考研复试、保研夏令营、博士申请的 **AI 模拟面试系统**。

## 功能

- **画像驱动出题**：填写专业/院校/科研经历 → AI 自动生成个性化题库
- **全模拟面试**：真实面试流程，AI 逐题追问，终场诊断报告
- **单题练习**：自由选题，即时评估反馈，不限次数
- **三个场景**：考研复试 / 保研夏令营 / 博士申请
- **预推免综合面试**：自我介绍、科研深挖、专业基础、压力面、英语与反问
- **语音面试**：浏览器录音 → 硅基流动 Qwen3-ASR 转写（SenseVoice/XingChen 自动备用）→ 可编辑后提交
- **语音播报**：浏览器内置 SpeechSynthesis 自动朗读面试官问题
- **英文文献翻译面试**：按方向即时生成不重复的材料学原创英文短文，英文朗读完整度评分 → 一分钟准备 → 中文语音口译 → 准确性/术语/完整性/表达评价
- **智能导入**：支持从 PDF、DOCX、TXT 简历中提取文字，再由 AI 自动填充面试画像
- **简历事实约束出题**：科研项目、竞赛论文、高分专业课会进入题库提示词；支持项目贡献核验、反事实刁难、专业课发散与跨场景迁移，禁止凭空补造经历

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的模型服务 API Key
```

### 3. 测试连通性

```bash
python app.py
```

### 4. 启动网页

```bash
streamlit run app_ui.py
```

浏览器自动打开，开始你的第一场 AI 模拟面试！

### 分享给好友

Windows 分享与安装说明见 [SHARING.md](SHARING.md)。运行 `build_share_package.ps1` 可生成不含个人 API Key 的分享压缩包，
好友解压后双击 `install_windows.bat`，按提示填写自己的硅基流动 API Key 即可安装。

安装脚本会同时创建「AI Interview Coach」和「文献阅读翻译模拟」两个桌面快捷方式；后者双击后直接打开英文文献翻译环节。

### 发布成可直接访问的网页

项目现在同时提供了容器化网页入口：`Dockerfile`、`.streamlit/config.toml` 和 `render.yaml`。
部署到 Render 时，直接连接 GitHub 仓库并选择 `render.yaml`，然后在环境变量中填写自己的
`DEEPSEEK_API_KEY`；模型和语音识别默认已指向硅基流动。部署完成后，Render 会提供一个可分享的
`https://…onrender.com` 地址，好友无需安装 Python 或运行代码，直接用浏览器打开即可。

当前仓库也可以通过下面的入口一键创建 Render 服务（首次使用需要授权 GitHub）：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fgh17c%2Fai-interview-coach-online)

创建服务时，将 `DEEPSEEK_API_KEY` 填入 Render 的 Environment Variables；不要把 Key 写进仓库文件。

本机也可以用 Docker 启动：

```powershell
docker build -t ai-interview-coach .
docker run --rm -p 8501:8501 --env-file .env ai-interview-coach
```

然后打开 <http://localhost:8501>。不要把 `.env` 或 API Key 提交到 GitHub；线上平台请使用它的
Secrets / Environment Variables 配置。

### 语音模式

进入「预推免综合面试」并开始全模拟后，点击「录音回答」，允许浏览器使用麦克风。
录音结束后，系统通过 `SILICONFLOW_STT_MODEL` 将语音转成文字；检查或修改识别结果，
点击「发送语音回答」。面试官回复会自动使用浏览器语音播报，也可以点击「重播」。

所有录音环节统一最长 10 分钟；达到安全上限才会自动停止，通常应由用户点击录音控件上的停止按钮结束。

录音控件会在开始录音的瞬间自动停止面试官播报，并提供“电脑外放 / 开放麦克风”和“耳机麦克风”两种环境配置，
还可以选择具体输入设备。建议麦克风距嘴 30–60 厘米；控件中的音量条应有明显变化，
系统也会记录非敏感的时长和音量指标，在接近静音时提示重录。若浏览器拒绝权限，请点击地址栏左侧🔒，
将“麦克风”改为“允许”后刷新页面。
如果控件提示“没有音频信号”，请打开 Windows「设置 → 隐私和安全性 → 麦克风」，
开启“麦克风访问”和“允许桌面应用访问麦克风”，并在录音控件中重新选择实际的麦克风设备。

识别结果会自动过滤“嗯、呃、啊、uh、um”等停顿词，并对晶界、析出强化、氧空位、
电解液等材料专业词汇进行规范化。文献翻译环节还会把当前材料的英文术语作为识别提示，
以减少专业词汇被识别成同音普通词的情况。页面保留“查看原始转写”入口，提交前仍可手动修正。

语音识别默认使用硅基流动的 `Qwen/Qwen3-ASR-1.7B`，并按顺序备用
`FunAudioLLM/SenseVoiceSmall`、`XingChenAGI/XingChenASR-V3.2`，不需要额外的 TTS Key。
遇到临时的 503、502、504 或 429 时，系统会自动进行短间隔重试，随后切换备用模型；
仍失败时会提示检查硅基流动控制台中的模型状态、额度和网络连接。可在 `.env` 中通过
`SILICONFLOW_STT_MODEL`、`SILICONFLOW_STT_FALLBACK_MODELS`、`SILICONFLOW_STT_MAX_RETRIES`、
`SILICONFLOW_STT_TIMEOUT_SECONDS` 和 `SILICONFLOW_STT_TOTAL_TIMEOUT_SECONDS` 调整模型、重试次数、
单次请求和整段录音的等待上限。默认单次最多等待 45 秒、整段录音最多等待 120 秒，
避免硅基流动连接卡住时页面长时间无响应；10 分钟录音本身仍可完整录制。

英文文献翻译环节在选择材料方向并点击开始后，会调用当前配置的聊天模型即时生成约 130–180 词的原创材料。
已生成的标题、正文指纹和近似文本会写入 `data/literature_material_history.jsonl`，当前会话和后续会话都会进行去重；
模型暂时不可用时只使用该方向尚未用过的本地备用材料，不会悄悄重复已用文章。
如果去重历史文件损坏或不可读，系统会停止分配并提示修复，不会把它误判为空记录。

### 简历文件导入

在「构建你的面试画像」页面展开「智能导入」，上传 PDF、DOCX 或 TXT 文件即可自动提取文字并解析。
如果 PDF 是扫描图片而不是可复制文字，需要先 OCR，或切换到「粘贴文本」手动粘贴内容。

## 项目结构

```
ai-interview-coach/
├── app_ui.py              # Streamlit 前端
├── app.py                 # CLI 测试入口
├── modules/
│   ├── api_client.py      # DeepSeek 统一调用层
│   ├── scenarios.py       # 场景配置
│   ├── question_seeds.py  # 真实面经种子题库
│   ├── profiler.py        # 画像分析 + 题库生成
│   ├── document_parser.py # PDF / DOCX / TXT 文本提取
│   ├── interviewer.py     # 面试官对话引擎
│   ├── evaluator.py       # 评估引擎
│   ├── literature_interview.py # 文献材料、朗读评分与口译评价
│   └── history.py         # 面试记录持久化
├── components/audio_recorder/index.html # 可关闭回声消除的浏览器录音控件
├── components/countdown/index.html      # 一分钟准备倒计时控件
└── data/sessions/         # 面试记录存储
```

## 技术栈

- **界面**: Streamlit
- **AI**: DeepSeek Chat API
- **语言**: Python 3.9–3.13
