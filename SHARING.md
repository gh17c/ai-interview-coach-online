# 分享给好友（Windows）

## 生成分享包

在项目目录中右键打开 PowerShell，执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_share_package.ps1
```

生成的 `dist\AIInterviewCoach-Windows.zip` 可以发给好友。压缩包不包含你的 `.env`、虚拟环境和运行日志。

## 好友安装

1. 解压 zip 文件。
2. 确认已安装 Python 3.9–3.13，并勾选 `Add Python to PATH`。
3. 双击 `install_windows.bat` 开始安装；它会自动调用安装脚本。
   如果系统拦截，也可以在 PowerShell 执行：
   `powershell -ExecutionPolicy Bypass -File .\install_windows.ps1`
4. 按提示输入好友自己的硅基流动 API Key。
5. 安装完成后，桌面会出现 `AI Interview Coach` 和 `文献阅读翻译模拟` 两个快捷方式。

安装后，在「预推免综合面试」的模式选择页还可以使用「英文文献翻译面试」：
朗读材料、完成一分钟准备，再用中文语音口译并查看材料学术语评价。

API Key 不应放进 zip 或发给好友。每位使用者都应使用自己的 Key，并自行承担模型调用费用。

## 发布为网页

如果希望好友直接通过浏览器访问，而不是安装本地程序，可以将仓库部署到 Render：

1. 将项目推送到自己的 GitHub 仓库（不要提交 `.env`）。
2. 在 Render 新建 Web Service，连接仓库并选择 Docker；项目里的 `render.yaml` 已提供默认配置。
3. 在服务的 Environment 中添加自己的 `DEEPSEEK_API_KEY`，保存并等待部署完成。
4. 把 Render 生成的 `https://…onrender.com` 地址发给好友即可。

也可以在本机使用 Docker：

```powershell
docker build -t ai-interview-coach .
docker run --rm -p 8501:8501 --env-file .env ai-interview-coach
```
