#!/usr/bin/env python3
"""从 archive.org 生成 scoop manifest（数据源唯一，纯 metadata，不下载安装包）。

数据源：
    https://archive.org/metadata/vmwareworkstationarchive

用法：
    python gen.py                  # 生成 bucket/*.json（archive sha1，弱）
    python gen.py --strict         # 拿不到 Broadcom 官方 SHA256 就报错退出（CI 用）
    python gen.py --no-official    # 忽略官方 SHA256，纯用 archive.org 的 hash

hash 从哪来（信任链）：
    archive.org 只提供 md5/sha1，不提供 sha256（sha256 在 Broadcom 那边需登录）。
    官方 sha256 从 gandli/vmware-downloads 公开的 data/checksums.txt 取，
    那边的值来自 Broadcom API，且已与 archive.org 的 md5 做过交叉比对。
    所以 CI 用 --strict：archive.org 上出现上游还没验证过的新包时直接失败，
    而不是把一个未经验证的 sha1 当成已验证结果发布。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

COLLECTION = "vmwareworkstationarchive"
META_URL = f"https://archive.org/metadata/{COLLECTION}"
DOWNLOAD_BASE = f"https://archive.org/download/{COLLECTION}"
UPSTREAM_CHECKSUMS = (
    "https://raw.githubusercontent.com/gandli/vmware-downloads/main/data/checksums.txt"
)
HOMEPAGE = "https://www.vmware.com/products/desktop-hypervisor/workstation-pro"
LICENSE = {
    "identifier": "Freeware",
    "url": "https://www.broadcom.com/company/legal/licensing",
}
NOTES = (
    "\n- 个人 / 商业用途免费，无需序列号。\n"
    "- 安装需要管理员权限，安装脚本会弹 UAC。\n"
    "- 安装后从开始菜单启动 VMware Workstation。\n"
    "- hash 为 Broadcom 官方 SHA256（经 gandli/vmware-downloads 公开），"
    "scoop 安装时自动校验。\n"
)

# app 名, 文件名 regex, 描述
APPS = [
    (
        "vmware-workstation-pro",
        re.compile(r"^VMware-Workstation-Full-(\d{2}H\d(?:u\d)?)-(\d+)\.exe$", re.I),
        "VMware Workstation Pro（最新版）",
    ),
    (
        "vmware-workstation-pro-legacy",
        re.compile(r"^VMware-[Ww]orkstation-[Ff]ull-(17\.\d+\.\d+)-(\d+)\.exe$"),
        "VMware Workstation Pro 17.6.4（老系统备用）",
    ),
]

UA = "scoop-vmware-gen/1.0"
HASH_FIELDS = (("sha1", 40), ("md5", 32))  # 优先更强的


def fetch_metadata(timeout: int = 60) -> dict:
    req = urllib.request.Request(META_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310
        return json.load(r)


def official_shas() -> dict[str, str]:
    """文件名(小写) -> Broadcom 官方 sha256。一次请求，全量复用。"""
    req = urllib.request.Request(UPSTREAM_CHECKSUMS, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:  # nosec B310
        text = r.read().decode()
    out = {}
    for line in text.splitlines():
        h, _, name = line.partition("  ")
        if len(h.strip()) == 64:
            out[name.strip().lower()] = h.strip().lower()
    return out


def version_key(version: str) -> tuple:
    """26H1u1 -> (26,1,1,1)；17.6.4 -> (17,6,4)。新式版本号数字更大。"""
    m = re.fullmatch(r"(\d{2})H(\d)(?:u(\d))?", version)
    if m:
        return (int(m[1]), int(m[2]), int(m[3] or 0), 1)
    return tuple(int(p) for p in version.split("."))


def pick(files: list[dict], pattern: re.Pattern) -> dict | None:
    """collection 里版本最大的匹配安装包（path 形如 26H1/VMware-...exe）"""
    best = None
    for f in files:
        name = f.get("name", "")
        if not name.endswith(".exe"):  # 排除 torrent / 校验和 / 压缩附件
            continue
        base = name.rsplit("/", 1)[-1]
        m = pattern.match(base)
        if not m:
            continue
        key = version_key(m[1])
        if best is None or key > best[0]:
            digest = next(
                (f.get(k, "").lower() for k, n in HASH_FIELDS
                 if len(f.get(k, "").strip()) == n),
                "",
            )
            best = (key, name, base, m[1], digest)
    if best is None:
        return None
    return {
        "path": best[1], "filename": best[2], "version": best[3], "hash": best[4]
    }


def manifest(p: dict, desc: str) -> dict:
    # InstallShield 包 MSI：/s 静默 + /v 转交 MSI 参数；反引号是 PowerShell 的转义引号
    return {
        "version": p["version"],
        "description": desc,
        "homepage": HOMEPAGE,
        "license": LICENSE,
        "url": f"{DOWNLOAD_BASE}/{p['path']}",
        "hash": p["hash"],
        "installer": {
            "script": [
                "$p = Start-Process -FilePath (Join-Path $dir '"
                + p["filename"]
                + "') -ArgumentList '/s','/v`\"/qn EULAS_AGREED=1 REBOOT=R`\"'"
                " -Verb RunAs -Wait -PassThru; exit $p.ExitCode"
            ]
        },
        "notes": NOTES,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="从 archive.org 生成 scoop manifest")
    ap.add_argument("--out", default="bucket", help="manifest 输出目录（默认 bucket/）")
    ap.add_argument("--strict", action="store_true",
                    help="拿不到官方 SHA256 就报错退出（CI 用）")
    ap.add_argument("--no-official", action="store_true",
                    help="忽略官方 SHA256，只用 archive.org 的 sha1/md5")
    args = ap.parse_args()

    print(f"拉取 {META_URL} …")
    files = fetch_metadata().get("files", [])
    official = {} if args.no_official else official_shas()
    if official:
        print(f"官方 SHA256 校验表: {len(official)} 条")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rc = 0

    for app, pattern, desc in APPS:
        p = pick(files, pattern)
        if p is None:
            print(f"❌ {app}: archive.org 里没找到匹配的安装包")
            rc = 1
            continue
        sha = official.get(p["filename"].lower())
        if sha:
            p["hash"], algo = sha, "sha256(官方)"
        elif args.strict:
            print(f"❌ {app} {p['filename']}: 官方 SHA256 校验表里没有它，拒绝发布未验证的 hash")
            rc = 1
            continue
        else:
            algo = "sha1" if len(p["hash"]) == 40 else "md5"
            print(f"⚠️ {app} {p['version']}: 无官方 SHA256，退回 archive.org {algo}")
        path = out / f"{app}.json"
        path.write_text(
            json.dumps(manifest(p, desc), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"✓ {path}  {p['version']}  {algo} {p['hash'][:16]}…")

    return rc


if __name__ == "__main__":
    sys.exit(main())