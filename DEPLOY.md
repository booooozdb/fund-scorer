# 基金投资评分系统 - 部署指南

## 方案一：部署到 Render.com（推荐，免费 24/7 运行）

Render.com 免费提供 Python 应用托管，部署后获得一个固定网址，随时随地可用。

### 步骤：
1. 注册 https://render.com（用 GitHub 账号即可）
2. 将本项目上传到 GitHub：
   ```bash
   git init
   git add .
   git commit -m "fund scorer v2"
   git remote add origin https://github.com/你的用户名/fund-scorer.git
   git push -u origin main
   ```
3. 在 Render 控制台 → New → Web Service → 连接你的 GitHub 仓库
4. 自动识别 render.yaml 配置，点击 Deploy
5. 等待 3-5 分钟，获得网址如：`https://fund-scorer.onrender.com`

> **注意**：免费版 15 分钟无访问会自动休眠，下次首次访问需等待 ~30 秒冷启动。

---

## 方案二：Docker 部署到任意 VPS

```bash
# 构建镜像
docker build -t fund-scorer .

# 运行（后台，自启动）
docker run -d --restart=always -p 8000:8000 --name fund-scorer fund-scorer

# 查看日志
docker logs fund-scorer
```

---

## 方案三：局域网手机访问（同一 WiFi）

1. 查看电脑 IP 地址：打开终端运行 `ipconfig`，找到 IPv4 地址（如 192.168.1.100）
2. 手机连接同一 WiFi，浏览器访问：`http://192.168.1.100:8000`

---

## 方案四：开机自启动（本地）

将 `start_server.bat` 的快捷方式放入启动文件夹：
1. `Win+R` → 输入 `shell:startup` → 确定
2. 右键 → 新建 → 快捷方式 → 指向 `start_server.bat`
3. 以后每次开机自动启动服务器

---

## 数据源说明
- 基金实时数据：新浪财经 (hq.sinajs.cn)
- 基金历史净值：东方财富 (api.fund.eastmoney.com)
- 技术指标计算：MA/MACD/RSI/波动率在服务端实时计算
