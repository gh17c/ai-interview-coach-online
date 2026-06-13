# 🎓 AI 学术面试教练

面向考研复试、保研夏令营、博士申请的 **AI 模拟面试系统**。

## 功能

- **画像驱动出题**：填写专业/院校/科研经历 → AI 自动生成个性化题库
- **全模拟面试**：真实面试流程，AI 逐题追问，终场诊断报告
- **单题练习**：自由选题，即时评估反馈，不限次数
- **三个场景**：考研复试 / 保研夏令营 / 博士申请

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
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
│   ├── interviewer.py     # 面试官对话引擎
│   ├── evaluator.py       # 评估引擎
│   └── history.py         # 面试记录持久化
└── data/sessions/         # 面试记录存储
```

## 技术栈

- **界面**: Streamlit
- **AI**: DeepSeek Chat API
- **语言**: Python 3.9+
