# scoop-vmware

[VMware Workstation Pro](https://www.vmware.com/products/desktop-hypervisor/workstation-pro) 的 [Scoop](https://scoop.sh/) bucket —— Windows 一键安装，无需 Broadcom Support Portal 登录。

[![hash 来源](https://img.shields.io/badge/SHA256-gandli%2Fvmware--downloads-0071c5?style=flat-square)](https://github.com/gandli/vmware-downloads)

## 用法

```powershell
scoop bucket add vmware https://github.com/gandli/scoop-vmware
scoop install vmware-workstation-pro
```

| App | 版本 | 用途 |
|:----|:-----|:-----|
| `vmware-workstation-pro` | 26H1u1 (build 25688693) | 最新版 |
| `vmware-workstation-pro-legacy` | 17.6.4 (build 24832109) | 老系统 / 兼容性备用 |

```powershell
scoop uninstall vmware-workstation-pro   # 卸载
scoop update                            # 检查新版本（checkver 已接上游 checksums.txt）
```

## 数据来源

安装包与 SHA256 全部来自上游仓库 **[gandli/vmware-downloads](https://github.com/gandli/vmware-downloads)**（Broadcom 官方 SHA256 + archive.org 免登录镜像），本 bucket 只是它的 Scoop 视图，不重复造数据源。

上游每月自动同步一次；本仓库的 manifest 由 `gen.py` 从上游 `data/vmware_downloads.json` 生成：

```bash
curl -sL https://raw.githubusercontent.com/gandli/vmware-downloads/main/data/vmware_downloads.json -o vmware_downloads.json
python gen.py vmware_downloads.json
```

## 注意事项

- **需要管理员权限**：安装脚本用 `Start-Process -Verb RunAs` 触发 UAC 提权。
- **静默参数**：`/s /v"/qn EULAS_AGREED=1 REBOOT=R"`（InstallShield 包 MSI）。
- **无需序列号**：17.5.2 起 VMware Workstation Pro 对个人与商业用途免费。
- **下载源是 archive.org**：`url` 指向 `archive.org/download/...`，会 302 跳到 `*.ca.archive.org` 节点；网络不通时先给 scoop 配代理。
- **没写 `autoupdate`**：上游镜像路径按年代变化（`26H1/` / `17.x/`），无法用版本号可靠模板化，硬写模板会在跨代更新时拉到错的文件。所以只保留 `checkver`（提示有新版），升级由维护者重跑 `gen.py` 发布。

## License

manifest 与脚本：MIT。VMware 安装包本体版权归 Broadcom 所有，受 [Broadcom EULA](https://www.broadcom.com/company/legal/licensing) 约束，本仓库只提供索引。
