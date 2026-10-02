#!/usr/bin/env python3
"""从 gandli/vmware-downloads 的 data/vmware_downloads.json 生成 scoop manifest。

用法: python gen.py <vmware_downloads.json> [输出目录=./bucket]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HOMEPAGE = "https://www.vmware.com/products/desktop-hypervisor/workstation-pro"
LICENSE = {"identifier": "Freeware", "url": "https://www.broadcom.com/company/legal/licensing"}
CHECKVER_URL = (
    "https://raw.githubusercontent.com/gandli/vmware-downloads/main/data/checksums.txt"
)
NOTES = (
    "\n- 个人 / 商业用途免费，无需序列号。\n"
    "- 安装需要管理员权限，安装脚本会弹 UAC。\n"
    "- 安装后从开始菜单启动 VMware Workstation。\n"
)

# (app 短名, 版本, 描述, checkver regex)
APPS = [
    ("vmware-workstation-pro", "26H1u1", "VMware Workstation Pro（最新版）",
     r"VMware-Workstation-Full-(\d{2}H\d(?:u\d)?)-\d+\.exe"),
    ("vmware-workstation-pro-legacy", "17.6.4", "VMware Workstation Pro 17.6.4（老系统备用）",
     r"VMware-Workstation-Full-(17\.\d+\.\d+)-\d+\.exe"),
]


def build(data: dict, version: str, regex: str) -> dict:
    entry = next(w for w in data["workstation_pro"] if w["version"] == version)
    win = entry["downloads"]["windows"]
    # VMware 是 InstallShield 包 MSI 的安装器：/s 静默 + /v 转交 MSI 参数。
    # JSON → PowerShell 里引号用反引号转义，所以先在 Python 里写出反引号版本。
    silent = "/s"
    msi = '/v`"/qn EULAS_AGREED=1 REBOOT=R`"'
    return {
        "version": version,
        "description": "见 description 字段",
        "homepage": HOMEPAGE,
        "license": LICENSE,
        "url": win["url"],
        "hash": win["sha256"],
        "checkver": {"url": CHECKVER_URL, "regex": regex},
        "installer": {
            "script": [
                "$p = Start-Process -FilePath (Join-Path $dir '"
                + win["filename"]
                + "') -ArgumentList '"
                + silent
                + "','"
                + msi
                + "' -Verb RunAs -Wait -PassThru; exit $p.ExitCode"
            ]
        },
        "notes": NOTES,
    }


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/vmware_downloads.json")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "bucket")
    data = json.loads(src.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    for app, version, desc, regex in APPS:
        m = build(data, version, regex)
        m["description"] = desc
        (out / f"{app}.json").write_text(
            json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"✓ {app}.json  {version}  {m['hash'][:12]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
