# 个人精简追剧配置

基于 [gaotianliuyun/gao](https://github.com/gaotianliuyun/gao) 的公开接口整理。上游快照：`8213bb046f4dce746b5f2ddcddb13a336d0b0d60`（2024-11-17）。核验日期：2026-10-13。

## 导入

```text
https://fastly.jsdelivr.net/gh/UltramanM78/gao-clean@master/clean.json
```

备用下载入口（同一配置，不是备用视频源）：

```text
https://cdn.jsdelivr.net/gh/UltramanM78/gao-clean@master/clean.json
https://raw.githubusercontent.com/UltramanM78/gao-clean/master/clean.json
```

使用 FongMi 设置中的点播配置导入。仅三个标准 JSON CMS 接口，无 JAR、JS、账号、网盘登录、壁纸或解析服务依赖。未添加自定义 DoH、代理或来源宣传条目。iOS 播放器仍需支持 TVBox type=1 配置；不承诺任意 iOS 播放器均兼容。

## 如何选主用和备用

| 用途 | 主用 | 备用 | 实测依据 |
|---|---|---|---|
| 电视剧 | 量子 | 暴風 | 《兰香如故》抽样均能播放；量子缓冲余量更大，暴風为1080p |
| 电影 | 非凡 | 量子 | 《流浪地球2》抽样：非凡下载余量略高，量子备用 |
| 动漫 | 量子 | 非凡 | 《斗罗大陆》2018动漫版：两者片段下载均有余量 |

三类选择合并为三个入口。表中主备是手动选择建议，并非播放器自动故障切换规则。主用仅指本次样本和当前测试网络的优先候选，不是全仓库性能最优的证明。

## 验证边界

- 已枚举所有7份来源配置的722个条目（594种执行配置），包含嵌套猫源配置；重复项、工具项也纳入清单。
- 10种直连接口做了三类内容、每类两次协议测试。
- 对可取得播放地址的4个提供商做了片段下载和媒体识别；最终3个提供商的9组内容都完成3秒音视频解码。
- **689个 type=3 条目和其他特殊来源没有 Android/JAR/JS 运行环境，尚未完成实际搜索和播放验证。**它们未进入精简配置，但并未被认定为失效。
- 283个可静态识别的站点首页做了两次连通性检查；首页返回200不能证明片库或播放可用，403也不能证明永久失效。
- 性能为电脑网络的短时抽样，包含请求开销；并非家中电视测速、长时间稳定性或整个片库的保证。
- “纯净”仅指精简配置不带推广和不必要依赖，不能保证第三方视频内无广告。

完整结果：[核验报告](AUDIT_REPORT.md)、[逐条清单](source-audit.csv)、[机器可读清单](source-audit.json)、[搜索原始结果](direct-search.json)、[视频测试](media-tests.json)。

## 重新核验

使用 Python 3、Git、FFmpeg/ffprobe。建议创建虚拟环境后安装 `requirements-audit.txt`：

```sh
python3 -m pip install -r requirements-audit.txt
python3 audit_inventory.py --repo . --out audit --ref 8213bb046f4dce746b5f2ddcddb13a336d0b0d60
python3 audit_direct.py --out audit
python3 audit_decode.py --out audit
```

完整库存通过 Git 对象读取，避免 macOS 大小写文件名冲突。域名检查会复用同一输出目录中的已有结果；做全新网络复测时请指定一个新的 `--out` 目录。测试只读取接口及短视频片段，不下载整集，不执行上游插件，不自动更改或发布配置。

## 上游与更新

保留原仓库文件作为对照；电视只导入 `clean.json`。上游说明保存在 [UPSTREAM_README.md](UPSTREAM_README.md)。同步上游不等于更新精简配置；新增接口必须重新验证。没有设置定时任务或自动发布流程。
