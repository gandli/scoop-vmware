# scoop-vmware

[VMware Workstation Pro](https://www.vmware.com/products/desktop-hypervisor/workstation-pro) 的 [Scoop](https://scoop.sh/) bucket —— Windows 一键安装，无需 Broadcom Support Portal 登录。

[![hash 来源](https://img.shields.io/badge/hash-archive.org%2Fvmwareworkstationarchive-0071c5?style=flat-square)](https://archive.org/details/vmwareworkstationarchive)

## 用法

```powershell
scoop bucket add vmware https://github.com/gandli/scoop-vmware
scoop install vmware-workstation-pro
```

| App | 版本 | 用途 |
|:----|:-----|:-----|
| `vmware-workstation-pro` | 26H1u1 (build 25688693) | 最新版 |
| `vmware-workstation-pro-<版本>` | 7.0.0 … 26H1（**96 个**） | 历史版本 |

```powershell
scoop search vmware-workstation-pro                    # 列全部 96 个版本
scoop install vmware-workstation-pro-17.6.4            # 装指定历史版本
scoop uninstall vmware-workstation-pro                 # 卸载
scoop update                                          # 无操作：新版本由 CI 自动写进 manifest
```

历史版本的 manifest 由 `gen.py` 自动生成，一个版本一个文件，命名就是 `-<版本号>`（含小数点，实测 bucket 里 `cuda10.2.json` 这类命名没问题）。

## 数据来源

唯一数据源是 **archive.org** collection [`vmwareworkstationarchive`](https://archive.org/details/vmwareworkstationarchive)：

```bash
curl -s https://archive.org/metadata/vmwareworkstationarchive | python -m json.tool | head
```

`gen.py` 从这份 metadata 里挑版本号最大的 `.exe`（26H1u1 → 26H1 → 25H2u1 …，旧式 17.6.4 单独一条），生成 `bucket/*.json`。**不下载安装包**，一次跑完约 2 秒。

- 安装包 URL：`https://archive.org/download/vmwareworkstationarchive/<路径>`
- manifest 里的 `hash` 优先用 **Broadcom 官方 SHA256**，取自 [gandli/vmware-downloads](https://github.com/gandli/vmware-downloads) 公开的 `data/checksums.txt`（该值来自 Broadcom API，并已与 archive.org 侧的 MD5 交叉比对过）。**scoop 安装时会自动用它校验下载的安装包**，不符则中止安装。
- 官方校验表只覆盖还在 Broadcom Portal 上的版本（当前 10 个：新式 `25H2*`/`26H1*` + `17.5.2`~`17.6.4`）。其余 **86 个历史版本退回用 archive.org 自带的 SHA1** —— 没有跟官方交叉比对过，弱一些，但仍是镜像自身的校验值；每个 manifest 的 `notes` 里都标注了实际用的是哪种。
- 想自己复核：`scoop hash <下载下来的 exe>`，输出直接跟 manifest 的 `hash` 比。

## 自动更新

`.github/workflows/update.yml` 每月 10 日 UTC 04:17 自动跑 `gen.py`，有 diff 就自动提交（也支持手动 `workflow_dispatch` 触发）。新版本发布后通常 1~2 天内跟进。

CI 跑的是 `--strict`：**最新版拿不到 Broadcom 官方 SHA256 就直接失败**，不会把 archive.org 的 SHA1（弱，且未与官方交叉比对过）当成已验证结果发出去。archive.org 上先于官方校验表出现的包会以 workflow 失败的形式暴露出来，等上游校验表补齐后自动重试即可。历史版本不受 `--strict` 约束（官方本就只覆盖在架版本），否则 CI 永远红。

没写 `checkver`：archive.org 的 metadata 是单行大 JSON，正则抓版本号会命中列表里的第一项而不是最新项，与其给一个会误报的提示，不如让 CI 直接更新。

## 注意事项

- **需要管理员权限**：安装脚本用 `Start-Process -Verb RunAs` 触发 UAC 提权。
- **静默参数**：`/s /v"/qn EULAS_AGREED=1 REBOOT=R"`（InstallShield 包 MSI）。
- **无需序列号**：17.5.2 起 VMware Workstation Pro 对个人与商业用途免费；更早的版本需要序列号。
- **老版本不一定能装**：7.x~16.x 是 2010~2020 年的包，在现代 Windows 上大概率装不上（或只能装不能跑），列出来只为应急与取证。
- **hash 必须是 Broadcom 官方 SHA256**：`gen.py --strict` 保证。手工改 manifest 时别填 SHA1/MD5 糊弄过去，scoop 虽然也认，但那是没跟官方交叉比对过的弱校验。
- **下载源是 archive.org**：`url` 会 302 跳到 `*.ca.archive.org` 节点；网络不通时先给 scoop 配代理。

## License

manifest 与脚本：MIT。VMware 安装包本体版权归 Broadcom 所有，受 [Broadcom EULA](https://www.broadcom.com/company/legal/licensing) 约束，本仓库只提供索引。
