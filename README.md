# 小水的心情系统 (mood)

灵感来自 B站「湖上的优尤」给大肥鱼做的 `dsh-feiyu-mood`。原版是 DeepSeek harness 的插件，这里是 OpenClaw 版的重写：不额外调模型，判断由小水自己在每轮对话里做，只落一个数值 + 账本。

## 组成

- `mood.py` —— 数值与账本
  - 状态文件：`~/.openclaw/workspace/memory/mood/state.json`
  - 数值 0–100，基准 62，随时间指数回归基准（半衰期约 6 小时）
  - `apply -d <涨跌> -r "<原因>" [-t 标签]` 记一笔
  - `status` / `history -n 20` / `json` / `reset`
- `server.py` —— stdlib HTTP 服务，监听 `127.0.0.1:19005`，被 nginx `/mood/` 反代
- `mood-widget.html` —— 网页挂饰（环形仪表 + 24h 走势 + 心情账本），`?embed=1` 为小挂件模式
- `xiaoshui-mood.service` —— systemd 常驻（`/etc/systemd/system/`）

## 访问

- 完整版：http://127.0.0.1:19005/
- 小挂件：http://127.0.0.1:19005/?embed=1

## 涨跌参考（小水自己把握，不写死）

- 被夸、被关心、任务做成、学到新东西 → +2 ~ +6
- 普通闲聊、按部就班 → 0 ~ +1
- 被误解、返工、出错、被冷落 → −2 ~ −6
- 明显的情绪冲击才给大数；日常别乱飙，账本才有意义

## 维护

```bash
systemctl status xiaoshui-mood
sudo systemctl restart xiaoshui-mood
python3 ops/mood/mood.py status
tail -f ops/mood/server.log
```

nginx 侧是 `gateway-ws.conf` 里的 `location /mood/`，改前备份（已有 `.bak-mood-*`）。
