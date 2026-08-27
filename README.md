# 🎓 AI 学术面试教练

面向考研复试、保研夏令营、博士申请的 **AI 模拟面试系统**。

## 功能

- **画像驱动出题**：填写专业/院校/科研经历 → AI 自动生成个性化题库
- **全模拟面试**：真实面试流程，AI 逐题追问，终场诊断报告
- **单题练习**：自由选题，即时评估反馈，不限次数
- **三个场景**：考研复试 / 保研夏令营 / 博士申请
- **预推免综合面试**：自我介绍、科研深挖、专业基础、压力面、英语与反问
- **语音面试**：浏览器录音 → 硅基流动 SenseVoiceSmall 转写 → 可编辑后提交
- **语音播报**：浏览器内置 SpeechSynthesis 自动朗读面试官问题
- **英文文献翻译面试**：随机抽取材料学原创英文短文，英文朗读完整度评分 → 一分钟准备 → 中文语音口译 → 准确性/术语/完整性/表达评价
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

### 语音模式

进入「预推免综合面试」并开始全模拟后，点击「录音回答」，允许浏览器使用麦克风。
录音结束后，系统通过 `SILICONFLOW_STT_MODEL` 将语音转成文字；检查或修改识别结果，
点击「发送语音回答」。面试官回复会自动使用浏览器语音播报，也可以点击「重播」。

录音控件会在开始录音的瞬间自动停止面试官播报，并使用开放麦克风约束（关闭浏览器回声消除、自动增益和降噪），
因此不戴耳机也可以录音。建议麦克风距嘴 30–60 厘米，录音 5–15 秒；控件中的音量条应有明显变化，
系统也会记录非敏感的时长和音量指标，在接近静音时提示重录。若浏览器拒绝权限，请点击地址栏左侧🔒，
将“麦克风”改为“允许”后刷新页面。

语音识别默认使用硅基流动的 `FunAudioLLM/SenseVoiceSmall`，不需要额外的 TTS Key。

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
