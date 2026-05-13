# 星元检验工具箱

## 部署站点

- GitHub（主站）: https://nokwiaey.github.io/xyjy/
- Cloudflare（副站）: https://xyjy.dfly.site/
- 帽子云（镜像站）: https://xyjy-rbw5h01el.maozi.io/
- Vercel（镜像站）: https://xyjy-tools.vercel.app/
- Netlify（镜像站）: https://xyjy.netlify.app/

## 站点监控

每30分钟自动检测各站点响应速度，监控数据保存在 [monitor/logs/](monitor/logs/) 目录。

- **监控面板**: 打开 [monitor/dashboard.html](https://nokwiaey.github.io/xyjy/monitor/dashboard.html) 查看可视化面板
- **手动检测**: 运行 `pwsh monitor/check-sites.ps1`
- **定时任务**（本地）: 以管理员身份运行 `pwsh monitor/setup-schedule.ps1` 注册 Windows 定时任务
- **GitHub Actions**: 通过 `.github/workflows/monitor.yml` 自动运行并提交结果
