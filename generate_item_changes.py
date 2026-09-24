#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 html/data/item.json 前后两次导出的差异，生成页面可读的变更记录。

用法::

    python generate_item_changes.py              # 对比并追加一条变更记录
    python generate_item_changes.py --init       # 只重建基线（不产生变更记录）
    python generate_item_changes.py --dry-run    # 只打印差异，不写文件
    python generate_item_changes.py --max-records 50
    python generate_item_changes.py --backfill-git 2026-09-24   # 用 git 历史补齐历史记录

产出::

    html/data/item-changes.json    页面读取的变更记录（最新记录在最前）
    html/data/item-snapshot.json   上一次导出内容的基线快照（仅本脚本使用）

关于时间：``item.json`` 由内网手工导出（未来计划改为定时导出），因此记录里的
``recordedAt``（脚本运行时间）和 ``exportTime``（导出文件生成时间）**都不是**
项目实际发生变更的时间。两者只能界定变更发生在 ``prevExportTime`` 与
``exportTime`` 之间，页面上必须如实说明这一点。

时间统一按 ``--tz-offset``（默认 +8，北京时间）记录，避免 CI 在 UTC 上跑出来的
时间比本地少 8 小时。``--backfill-git`` 补齐的记录，``recordedAt`` 取 git 提交时间。
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = BASE_DIR / "html" / "data" / "item.json"
DEFAULT_CHANGES = BASE_DIR / "html" / "data" / "item-changes.json"
DEFAULT_SNAPSHOT = BASE_DIR / "html" / "data" / "item-snapshot.json"

SCHEMA_VERSION = 1
DEFAULT_MAX_RECORDS = 200

# 变更分类（页面按此顺序分组展示）
CATEGORIES = [
    ("item", "HIS 项目"),
    ("price", "收费价格"),
    ("lis", "LIS项目"),
    ("form", "申请单"),
]

CHANGES_NOTE = (
    "本文件由 generate_item_changes.py 自动生成，请勿手工编辑。"
    "recordedAt 为脚本检测时间（用 --backfill-git 补齐的记录为 git 提交时间），"
    "exportTime 为 item.json 的导出时间；"
    "两者都不等于项目实际发生变更的时间，变更只可能发生在 prevExportTime 与 exportTime 之间。"
)


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def log(message):
    try:
        print(message)
    except UnicodeEncodeError:  # pragma: no cover - 老版本 Windows 控制台
        sys.stdout.buffer.write((message + "\n").encode("utf-8", "replace"))


def read_json(path):
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def write_json(path, payload, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fp:
        if compact:
            json.dump(payload, fp, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, fp, ensure_ascii=False, indent=1)
        fp.write("\n")


def text(value):
    """把任意值安全地转成字符串（None -> ''）。"""
    return "" if value is None else str(value).strip()


def trimmed_text(value):
    return text(value)


def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return text(value).lower() in ("1", "true", "yes", "y", "是")


def to_number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    raw = text(value)
    if not raw:
        return None
    try:
        return round(float(raw), 4)
    except ValueError:
        return None


def fmt_num(value):
    """数字展示：去掉无意义的小数零。"""
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value))
        return ("%.4f" % float(value)).rstrip("0").rstrip(".")
    return text(value)


# --------------------------------------------------------------------------
# 归一化：把 item.json 变成便于逐字段比较的稳定结构
# --------------------------------------------------------------------------
def build_state(data):
    state = {
        "version": text(data.get("version")),
        "exportTime": text(data.get("exportTime")),
    }

    apply_forms = {}
    for form in data.get("applyForms") or []:
        code = text(form.get("applyFormCode"))
        if not code:
            continue
        apply_forms[code] = {"name": text(form.get("applyFormName"))}
    state["applyForms"] = apply_forms

    items = {}
    for item in data.get("items") or []:
        code = text(item.get("itemCode"))
        if not code:
            continue
        items[code] = {
            "name": text(item.get("itemName")),
            "form": text(item.get("applyFormCode")),
            "sample": text(item.get("sample")),
            "emergency": to_bool(item.get("isEmergency")),
            "remark": text(item.get("remark")),
        }
    state["items"] = items

    prices = {}
    for code, entry in (data.get("priceMap") or {}).items():
        code = text(code)
        details = {}
        for detail in (entry or {}).get("details") or []:
            detail_code = text(detail.get("detailCode"))
            detail_name = text(detail.get("detailName"))
            key = detail_code or detail_name or "detail"
            suffix = 2
            base_key = key
            while key in details:  # 同一明细编码重复出现时用序号区分
                key = "%s#%d" % (base_key, suffix)
                suffix += 1
            details[key] = {
                "code": detail_code,
                "name": detail_name,
                "price": to_number(detail.get("price")),
                "count": to_number(detail.get("count")),
                "total": to_number(detail.get("total")),
            }
        prices[code] = {
            "sum": to_number((entry or {}).get("sum")),
            "details": details,
        }
    state["prices"] = prices

    lis = data.get("lis") or {}

    groups = {}
    for group in lis.get("inspectionGroups") or []:
        group_id = text(group.get("groupId"))
        if not group_id:
            continue
        groups[group_id] = {
            "name": text(group.get("groupName")),
            "sort": text(group.get("groupSort")),
        }
    state["lisGroups"] = groups

    test_items = {}
    for test_item in lis.get("testItems") or []:
        test_item_id = text(test_item.get("testItemId"))
        if not test_item_id:
            continue
        test_items[test_item_id] = {
            "code": text(test_item.get("testItemCode")),
            "name": text(test_item.get("chineseName")),
            "des": text(test_item.get("itemDes")),
        }
    state["lisTestItems"] = test_items

    # 注意：chargeItems.charge 与 priceMap.sum 完全等价（已核对 511 条全部一致），
    # 为避免价格变化被重复记录两次，这里不比较 charge 字段。
    charge_items = {}
    for charge_item in lis.get("chargeItems") or []:
        charge_item_id = text(charge_item.get("chargeItemId"))
        if not charge_item_id:
            continue
        charge_items[charge_item_id] = {
            "name": text(charge_item.get("chineseName")),
            "his": text(charge_item.get("hisId")),
        }
    state["lisChargeItems"] = charge_items

    links = {}
    for link in lis.get("chargeItemLists") or []:
        charge_item_id = text(link.get("chargeItemId"))
        test_item_id = text(link.get("testItemId"))
        if not charge_item_id or not test_item_id:
            continue
        key = charge_item_id + "|" + test_item_id
        group_id = text(link.get("groupId"))
        entry = links.setdefault(key, {"chargeItemId": charge_item_id,
                                       "testItemId": test_item_id,
                                       "groups": set()})
        if group_id:
            entry["groups"].add(group_id)
    for entry in links.values():
        entry["groups"] = sorted(entry["groups"])
    state["lisLinks"] = links

    return state


# --------------------------------------------------------------------------
# 变更条目的构造
# --------------------------------------------------------------------------
def make_change(kind, category, level, title, fields=None):
    return {
        "kind": kind,
        "category": category,
        "level": level,          # add / remove / update
        "title": title,
        "fields": fields or [],
    }


def field_value(label, value):
    return {"label": label, "value": text(value)}


def field_change(label, old, new):
    return {"label": label, "from": text(old), "to": text(new)}


def item_label(state, item_code):
    """项目编码 + 名称，缺失时回退到价格明细里的名称。"""
    code = text(item_code)
    item = state["items"].get(code)
    if item and item["name"]:
        return "%s %s" % (code, item["name"])
    price = state["prices"].get(code)
    if price:
        for detail in price["details"].values():
            if detail["name"]:
                return "%s %s" % (code, detail["name"])
    if item:
        return code
    return "%s（HIS中暂无对应在用项目）" % code


def form_label(state, form_code):
    code = text(form_code)
    form = state["applyForms"].get(code)
    if form and form["name"]:
        return "%s %s" % (code, form["name"])
    return code or "（无申请单）"


def yes_no(value):
    return "是" if value else "否"


def format_detail(detail):
    parts = []
    if detail["code"]:
        parts.append(detail["code"])
    if detail["name"]:
        parts.append(detail["name"])
    body = " ".join(parts)
    extras = []
    if detail["price"] is not None:
        extras.append("单价 %s" % fmt_num(detail["price"]))
    if detail["count"] is not None:
        extras.append("数量 %s" % fmt_num(detail["count"]))
    if detail["total"] is not None:
        extras.append("金额 %s" % fmt_num(detail["total"]))
    if extras:
        body = "%s｜%s" % (body, "｜".join(extras)) if body else "｜".join(extras)
    return body


# --------------------------------------------------------------------------
# 各分类的差异比较
# --------------------------------------------------------------------------
def diff_apply_forms(prev, cur):
    changes = []
    old, new = prev["applyForms"], cur["applyForms"]

    for code in sorted(set(new) - set(old)):
        changes.append(make_change(
            "form_added", "form", "add", "申请单 %s" % form_label(cur, code),
            [field_value("申请单编码", code),
             field_value("申请单名称", new[code]["name"])],
        ))

    for code in sorted(set(old) - set(new)):
        changes.append(make_change(
            "form_removed", "form", "remove", "申请单 %s" % form_label(prev, code),
            [field_value("申请单编码", code),
             field_value("申请单名称", old[code]["name"])],
        ))

    for code in sorted(set(old) & set(new)):
        if old[code]["name"] != new[code]["name"]:
            changes.append(make_change(
                "form_modified", "form", "update", "申请单 %s" % code,
                [field_change("申请单名称", old[code]["name"], new[code]["name"])],
            ))

    return changes


def price_fields(state, code):
    """新增/删除项目时一并展示其收费信息，避免价格分类再重复记一条。"""
    fields = []
    price = state["prices"].get(code)
    if not price:
        return fields
    if price["sum"] is not None:
        fields.append(field_value("收费合计", fmt_num(price["sum"])))
    for detail in price["details"].values():
        fields.append(field_value("收费明细", format_detail(detail)))
    return fields


def diff_items(prev, cur):
    """返回 (变更列表, 已整体新增/删除的项目编码集合)。

    整体新增/删除的项目，其价格条目不再单独记一条价格变更（信息已包含在
    项目条目里），避免同一件事在页面上出现两次。
    """
    changes = []
    old, new = prev["items"], cur["items"]
    wholesale = set()

    for code in sorted(set(new) - set(old)):
        item = new[code]
        wholesale.add(code)
        fields = [
            field_value("项目编码", code),
            field_value("项目名称", item["name"]),
            field_value("申请单", form_label(cur, item["form"])),
            field_value("标本类型", item["sample"]),
            field_value("急诊项目", yes_no(item["emergency"])),
        ]
        if item["remark"]:
            fields.append(field_value("备注", item["remark"]))
        fields.extend(price_fields(cur, code))
        changes.append(make_change(
            "item_added", "item", "add", item_label(cur, code), fields))

    for code in sorted(set(old) - set(new)):
        item = old[code]
        wholesale.add(code)
        fields = [
            field_value("项目编码", code),
            field_value("项目名称", item["name"]),
            field_value("申请单", form_label(prev, item["form"])),
            field_value("标本类型", item["sample"]),
            field_value("急诊项目", yes_no(item["emergency"])),
        ]
        if item["remark"]:
            fields.append(field_value("备注", item["remark"]))
        fields.extend(price_fields(prev, code))
        changes.append(make_change(
            "item_removed", "item", "remove", item_label(prev, code), fields))

    for code in sorted(set(old) & set(new)):
        before, after = old[code], new[code]
        fields = []
        if before["name"] != after["name"]:
            fields.append(field_change("项目名称", before["name"], after["name"]))
        if before["form"] != after["form"]:
            fields.append(field_change("申请单",
                                       form_label(prev, before["form"]),
                                       form_label(cur, after["form"])))
        if before["sample"] != after["sample"]:
            fields.append(field_change("标本类型", before["sample"], after["sample"]))
        if before["emergency"] != after["emergency"]:
            fields.append(field_change("急诊项目",
                                       yes_no(before["emergency"]),
                                       yes_no(after["emergency"])))
        if before["remark"] != after["remark"]:
            fields.append(field_change("备注", before["remark"], after["remark"]))
        if fields:
            title = item_label(cur, code) if after["name"] == before["name"] else \
                "%s（%s）" % (item_label(cur, code), before["name"])
            changes.append(make_change(
                "item_modified", "item", "update", title, fields))

    return changes, wholesale


def diff_prices(prev, cur, skip_codes=None):
    changes = []
    old, new = prev["prices"], cur["prices"]
    skip_codes = skip_codes or set()

    for code in sorted(set(new) - set(old)):
        if code in skip_codes:
            continue
        entry = new[code]
        fields = []
        if entry["sum"] is not None:
            fields.append(field_value("收费合计", fmt_num(entry["sum"])))
        for detail in entry["details"].values():
            fields.append(field_value("收费明细", format_detail(detail)))
        changes.append(make_change(
            "price_added", "price", "add", item_label(cur, code), fields))

    for code in sorted(set(old) - set(new)):
        if code in skip_codes:
            continue
        entry = old[code]
        fields = []
        if entry["sum"] is not None:
            fields.append(field_value("收费合计", fmt_num(entry["sum"])))
        for detail in entry["details"].values():
            fields.append(field_value("收费明细", format_detail(detail)))
        changes.append(make_change(
            "price_removed", "price", "remove", item_label(prev, code), fields))

    for code in sorted(set(old) & set(new)):
        before, after = old[code], new[code]
        fields = []
        if before["sum"] != after["sum"]:
            fields.append(field_change("收费合计",
                                       fmt_num(before["sum"]),
                                       fmt_num(after["sum"])))

        old_details, new_details = before["details"], after["details"]
        for key in sorted(set(new_details) - set(old_details)):
            fields.append(field_value("新增收费明细", format_detail(new_details[key])))
        for key in sorted(set(old_details) - set(new_details)):
            fields.append(field_value("删除收费明细", format_detail(old_details[key])))
        for key in sorted(set(old_details) & set(new_details)):
            old_detail, new_detail = old_details[key], new_details[key]
            label = new_detail["name"] or old_detail["name"] or new_detail["code"] or key
            if old_detail["name"] != new_detail["name"]:
                fields.append(field_change("明细名称 %s" % label,
                                           old_detail["name"], new_detail["name"]))
            if old_detail["price"] != new_detail["price"]:
                fields.append(field_change("单价 %s" % label,
                                           fmt_num(old_detail["price"]),
                                           fmt_num(new_detail["price"])))
            if old_detail["count"] != new_detail["count"]:
                fields.append(field_change("数量 %s" % label,
                                           fmt_num(old_detail["count"]),
                                           fmt_num(new_detail["count"])))
            if old_detail["total"] != new_detail["total"]:
                fields.append(field_change("金额 %s" % label,
                                           fmt_num(old_detail["total"]),
                                           fmt_num(new_detail["total"])))

        if fields:
            changes.append(make_change(
                "price_changed", "price", "update", item_label(cur, code), fields))

    return changes


def diff_lis_groups(prev, cur):
    changes = []
    old, new = prev["lisGroups"], cur["lisGroups"]

    for group_id in sorted(set(new) - set(old)):
        changes.append(make_change(
            "lis_group_added", "lis", "add",
            "检验分组 %s %s" % (group_id, new[group_id]["name"]),
            [field_value("分组编码", group_id),
             field_value("分组名称", new[group_id]["name"]),
             field_value("排序号", new[group_id]["sort"])]))

    for group_id in sorted(set(old) - set(new)):
        changes.append(make_change(
            "lis_group_removed", "lis", "remove",
            "检验分组 %s %s" % (group_id, old[group_id]["name"]),
            [field_value("分组编码", group_id),
             field_value("分组名称", old[group_id]["name"])]))

    for group_id in sorted(set(old) & set(new)):
        if old[group_id]["name"] != new[group_id]["name"]:
            changes.append(make_change(
                "lis_group_modified", "lis", "update", "检验分组 %s" % group_id,
                [field_change("分组名称",
                              old[group_id]["name"], new[group_id]["name"])]))

    return changes


def test_item_label(state, test_item_id):
    entry = state["lisTestItems"].get(test_item_id)
    if not entry:
        return "分析项目 %s（已无此项目）" % test_item_id
    parts = [part for part in (entry["code"], entry["name"]) if part]
    body = " ".join(parts) or test_item_id
    return "%s（%s）" % (body, test_item_id)


def group_names(state, group_ids):
    names = []
    for group_id in group_ids:
        entry = state["lisGroups"].get(group_id)
        names.append("%s %s" % (group_id, entry["name"]) if entry and entry["name"]
                     else group_id)
    return "、".join(names) if names else "（未分组）"


def links_by_charge(state):
    """chargeItemId -> {testItemId: [groupId, ...]}，即每个诊疗项目关联的分析项目。"""
    result = {}
    for entry in state["lisLinks"].values():
        result.setdefault(entry["chargeItemId"], {})[entry["testItemId"]] = entry["groups"]
    return result


def links_by_test_item(state):
    """testItemId -> [chargeItemId, ...]，即每个分析项目被哪些诊疗项目引用。"""
    result = {}
    for entry in state["lisLinks"].values():
        result.setdefault(entry["testItemId"], set()).add(entry["chargeItemId"])
    return result


def charge_item_label(state, charge_item_id):
    entry = state["lisChargeItems"].get(charge_item_id)
    if entry and entry["name"]:
        return "%s %s" % (charge_item_id, entry["name"])
    if entry:
        return charge_item_id
    return "%s（不在诊疗项目表中）" % charge_item_id


def charge_refs_text(state, test_item_id, refs, limit=5):
    """列出引用了某分析项目的诊疗项目，供“分析项目自身变化”的条目做上下文。"""
    charge_ids = sorted(refs.get(test_item_id, set()))
    if not charge_ids:
        return ""
    names = [charge_item_label(state, charge_id) for charge_id in charge_ids[:limit]]
    if len(charge_ids) > limit:
        names.append("等 %d 个" % len(charge_ids))
    return "、".join(names)


def diff_lis_test_items(prev, cur):
    """分析项目（testItems）自身的变化。

    已挂到诊疗项目下的分析项目，其新增/取消由所属诊疗项目条目记录（见
    diff_lis_charge_items），这里只补两类：名称/代号/互认标识的变化，以及
    没有挂任何诊疗项目的孤立分析项目的增删。
    """
    changes = []
    old, new = prev["lisTestItems"], cur["lisTestItems"]
    old_refs = links_by_test_item(prev)
    new_refs = links_by_test_item(cur)

    def base_fields(entry, test_item_id, state, refs):
        return [
            field_value("分析项目ID", test_item_id),
            field_value("代号", entry["code"]),
            field_value("名称", entry["name"]),
            field_value("互认标识", entry["des"]),
            field_value("关联诊疗项目", charge_refs_text(state, test_item_id, refs) or "（无）"),
        ]

    for test_item_id in sorted(set(new) - set(old)):
        if new_refs.get(test_item_id):
            continue  # 已随所属诊疗项目一并记录
        changes.append(make_change(
            "lis_test_added", "lis", "add", test_item_label(cur, test_item_id),
            base_fields(new[test_item_id], test_item_id, cur, new_refs)))

    for test_item_id in sorted(set(old) - set(new)):
        if old_refs.get(test_item_id):
            continue  # 已随所属诊疗项目一并记录
        changes.append(make_change(
            "lis_test_removed", "lis", "remove", test_item_label(prev, test_item_id),
            base_fields(old[test_item_id], test_item_id, prev, old_refs)))

    for test_item_id in sorted(set(old) & set(new)):
        before, after = old[test_item_id], new[test_item_id]
        fields = []
        if before["code"] != after["code"]:
            fields.append(field_change("代号", before["code"], after["code"]))
        if before["name"] != after["name"]:
            fields.append(field_change("名称", before["name"], after["name"]))
        if before["des"] != after["des"]:
            fields.append(field_change("互认标识", before["des"], after["des"]))
        if fields:
            refs = charge_refs_text(cur, test_item_id, new_refs)
            if refs:
                fields.append(field_value("关联诊疗项目", refs))
            changes.append(make_change(
                "lis_test_modified", "lis", "update",
                test_item_label(cur, test_item_id), fields))

    return changes


def diff_lis_charge_items(prev, cur):
    """以“诊疗项目”为单位汇总 LIS 变化。

    诊疗项目 ↔ 分析项目 是一对多（和 HIS 项目 ↔ 收费明细 一样），所以关联分析
    项目作为诊疗项目条目的明细一起展示，不单独另记一条；诊疗项目下没有关联分析
    项目时，该明细为空（（无））。
    """
    changes = []
    old, new = prev["lisChargeItems"], cur["lisChargeItems"]
    old_links, new_links = links_by_charge(prev), links_by_charge(cur)
    charge_ids = sorted(set(old) | set(new) | set(old_links) | set(new_links))

    def attr_fields(state, charge_item_id, level):
        """诊疗项目自身的属性：新增/删除时按值展示。"""
        entry = state["lisChargeItems"].get(charge_item_id)
        if not entry:
            return [field_value("诊疗项目名称", "（不在诊疗项目表中）")]
        return [
            field_value("诊疗项目名称", entry["name"]),
            field_value("对应 HIS 项目",
                        item_label(state, entry["his"]) if entry["his"]
                        else "（HIS中暂无对应在用项目）"),
        ]

    def link_label(state, test_item_id, group_ids):
        return "%s（分组：%s）" % (test_item_label(state, test_item_id),
                                   group_names(state, group_ids))

    def all_link_fields(state, charge_item_id):
        links = links_by_charge(state).get(charge_item_id, {})
        if not links:
            return [field_value("关联分析项目", "（无）")]
        return [field_value("关联分析项目", link_label(state, test_item_id, links[test_item_id]))
                for test_item_id in sorted(links)]

    def link_diff_fields(charge_item_id):
        before, after = old_links.get(charge_item_id, {}), new_links.get(charge_item_id, {})
        fields = []
        for test_item_id in sorted(set(after) - set(before)):
            fields.append(field_value("新增关联分析项目",
                                      link_label(cur, test_item_id, after[test_item_id])))
        for test_item_id in sorted(set(before) - set(after)):
            fields.append(field_value("取消关联分析项目",
                                      link_label(prev, test_item_id, before[test_item_id])))
        for test_item_id in sorted(set(before) & set(after)):
            if before[test_item_id] != after[test_item_id]:
                fields.append(field_value(
                    "关联分组调整",
                    "%s：%s → %s" % (test_item_label(cur, test_item_id),
                                     group_names(prev, before[test_item_id]),
                                     group_names(cur, after[test_item_id]))))
        return fields

    for charge_item_id in charge_ids:
        had_before = (charge_item_id in old) or bool(old_links.get(charge_item_id))
        has_now = (charge_item_id in new) or bool(new_links.get(charge_item_id))

        if not had_before and has_now:
            changes.append(make_change(
                "lis_charge_added", "lis", "add", charge_item_label(cur, charge_item_id),
                [field_value("诊疗项目ID", charge_item_id)]
                + attr_fields(cur, charge_item_id, "add")
                + all_link_fields(cur, charge_item_id)))
        elif had_before and not has_now:
            changes.append(make_change(
                "lis_charge_removed", "lis", "remove", charge_item_label(prev, charge_item_id),
                [field_value("诊疗项目ID", charge_item_id)]
                + attr_fields(prev, charge_item_id, "remove")
                + all_link_fields(prev, charge_item_id)))
        else:
            fields = []
            before, after = old.get(charge_item_id), new.get(charge_item_id)
            if before and after:
                if before["name"] != after["name"]:
                    fields.append(field_change("诊疗项目名称", before["name"], after["name"]))
                if before["his"] != after["his"]:
                    fields.append(field_change(
                        "对应 HIS 项目",
                        item_label(prev, before["his"]) if before["his"]
                        else "（HIS中暂无对应在用项目）",
                        item_label(cur, after["his"]) if after["his"]
                        else "（HIS中暂无对应在用项目）"))
            fields += link_diff_fields(charge_item_id)
            if fields:
                changes.append(make_change(
                    "lis_charge_modified", "lis", "update",
                    charge_item_label(cur, charge_item_id), fields))

    return changes


def diff_states(prev, cur):
    changes = []
    item_changes, wholesale_codes = diff_items(prev, cur)
    changes += item_changes
    changes += diff_prices(prev, cur, skip_codes=wholesale_codes)
    changes += diff_lis_groups(prev, cur)
    changes += diff_lis_charge_items(prev, cur)
    changes += diff_lis_test_items(prev, cur)
    changes += diff_apply_forms(prev, cur)
    return changes


def summarize(changes):
    stats = {
        "total": len(changes),
        "add": sum(1 for item in changes if item["level"] == "add"),
        "remove": sum(1 for item in changes if item["level"] == "remove"),
        "update": sum(1 for item in changes if item["level"] == "update"),
    }
    for key, _label in CATEGORIES:
        stats[key] = sum(1 for item in changes if item["category"] == key)
    return stats


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def build_record(prev_state, cur_state, changes, now):
    stats = summarize(changes)
    record = {
        "id": now.strftime("%Y%m%d-%H%M%S"),
        "recordedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "exportTime": cur_state["exportTime"],
        "prevExportTime": prev_state["exportTime"] if prev_state else "",
        "version": cur_state["version"],
        "prevVersion": prev_state["version"] if prev_state else "",
        "stats": stats,
        "changes": changes,
    }
    return record


def build_baseline_record(cur_state, now):
    return {
        "id": now.strftime("%Y%m%d-%H%M%S"),
        "recordedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "exportTime": cur_state["exportTime"],
        "prevExportTime": "",
        "version": cur_state["version"],
        "prevVersion": "",
        "baseline": True,
        "stats": summarize([]),
        "changes": [],
    }


def print_changes(record):
    stats = record["stats"]
    log("导出时间：%s（上一次：%s）" % (record["exportTime"] or "未知",
                                        record["prevExportTime"] or "无基线"))
    log("共 %d 项变更：新增 %d，删除 %d，修改 %d"
        % (stats["total"], stats["add"], stats["remove"], stats["update"]))
    for key, label in CATEGORIES:
        if stats.get(key):
            log("  - %s：%d 项" % (label, stats[key]))
    for change in record["changes"]:
        log("  [%s] %s" % (change["level"], change["title"]))
        for field in change["fields"]:
            if "from" in field:
                log("      %s：%s → %s" % (field["label"], field["from"], field["to"]))
            else:
                log("      %s：%s" % (field["label"], field["value"]))


# --------------------------------------------------------------------------
# 用 git 历史补齐变更记录
# --------------------------------------------------------------------------
def git_stdout(args, cwd):
    result = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(message or "git 命令执行失败：git %s" % " ".join(args))
    return result.stdout


def parse_git_date(value, tz):
    """解析 `git log --format=%cI` 的提交时间并换算到目标时区。"""
    raw = text(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now(tz)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(tz)


def collect_git_commits(repo_dir, rel_path):
    """按时间正序返回该文件的所有提交（sha / 提交时间 / 主题）。"""
    fmt = "%H%x1f%cI%x1f%s%x1e"
    raw = git_stdout(["log", "--reverse", "--format=" + fmt, "--", rel_path], repo_dir)
    commits = []
    for chunk in raw.decode("utf-8", "replace").split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("\x1f")
        if len(parts) < 3:
            continue
        commits.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
    return commits


def build_payload(records, now, last_export_time):
    last_change_at = None
    for item in records:
        if item.get("stats", {}).get("total"):
            last_change_at = item.get("recordedAt")
            break
    return {
        "schema": SCHEMA_VERSION,
        "note": CHANGES_NOTE,
        "generatedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "lastCheckedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "lastExportTime": last_export_time,
        "lastChangeAt": last_change_at,
        "recordCount": len(records),
        "categories": [{"key": key, "label": label} for key, label in CATEGORIES],
        "records": records,
    }


def read_existing_records(path):
    if not path.exists():
        return []
    try:
        payload = read_json(path)
    except (ValueError, OSError):
        return []
    records = payload.get("records")
    return records if isinstance(records, list) else []


def run_backfill(args, now, tz):
    """用 git 历史里 item.json 的历次提交重建变更记录。"""
    if not args.data.exists():
        log("找不到数据文件：%s" % args.data)
        return 1

    try:
        since = datetime.strptime(args.backfill_git, "%Y-%m-%d").replace(tzinfo=tz)
    except ValueError:
        log("日期格式应为 YYYY-MM-DD：%s" % args.backfill_git)
        return 1

    repo_dir = BASE_DIR
    try:
        rel_path = args.data.resolve().relative_to(repo_dir.resolve()).as_posix()
    except ValueError:
        log("数据文件不在脚本所在仓库内，无法使用 git 历史：%s" % args.data)
        return 1

    try:
        commits = collect_git_commits(repo_dir, rel_path)
    except RuntimeError as exc:
        log("读取 git 历史失败：%s" % exc)
        return 1

    start = None
    for index, commit in enumerate(commits):
        if parse_git_date(commit["date"], tz).date() >= since.date():
            start = index
            break
    if start is None:
        log("git 历史中没有 %s（含）之后针对 %s 的提交。" % (args.backfill_git, rel_path))
        return 0

    log("用 git 历史补齐 %s 起的变更记录，共 %d 次提交。" % (args.backfill_git, len(commits) - start))

    states = {}

    def state_of(sha):
        if sha not in states:
            raw = git_stdout(["show", "%s:%s" % (sha, rel_path)], repo_dir)
            states[sha] = build_state(json.loads(raw.decode("utf-8")))
        return states[sha]

    prev_state = state_of(commits[start - 1]["sha"]) if start > 0 else None
    backfilled = []

    for commit in commits[start:]:
        cur_state = state_of(commit["sha"])
        commit_time = parse_git_date(commit["date"], tz)
        changes = diff_states(prev_state, cur_state) if prev_state else []
        record = (build_record(prev_state, cur_state, changes, commit_time)
                  if prev_state else build_baseline_record(cur_state, commit_time))
        record["id"] = commit_time.strftime("%Y%m%d-%H%M%S")
        record["source"] = "git"
        record["gitCommit"] = commit["sha"][:8]
        record["gitSubject"] = commit["subject"]
        backfilled.append(record)
        log("  %s  导出 %s  →  %d 项变更  %s"
            % (commit_time.strftime("%Y-%m-%d %H:%M"),
               text(cur_state["exportTime"])[:19] or "未知",
               record["stats"]["total"], commit["subject"]))
        prev_state = cur_state

    # 工作区里的 item.json 若比 git 里最新的一次提交还新（例如刚导出还没提交），一并记录
    file_state = build_state(read_json(args.data))
    if backfilled and backfilled[-1]["exportTime"] != file_state["exportTime"]:
        changes = diff_states(prev_state, file_state)
        if changes:
            record = build_record(prev_state, file_state, changes, now)
            record["id"] = now.strftime("%Y%m%d-%H%M%S")
            backfilled.append(record)
            log("  当前 item.json（导出时间 %s）另有 %d 项变更，一并记录。"
                % (text(file_state["exportTime"])[:19], len(changes)))
        prev_state = file_state

    records = sorted(
        backfilled + [r for r in read_existing_records(args.changes)
                      if not r.get("baseline")
                      and r.get("exportTime") not in {item["exportTime"] for item in backfilled}],
        key=lambda item: item.get("exportTime") or "",
        reverse=True,
    )
    if args.max_records > 0:
        records = records[:args.max_records]

    if args.dry_run:
        log("（--dry-run：未写入任何文件，以下为补齐后的记录顺序）")
        for item in records:
            log("  %s  导出 %s  %d 项变更"
                % (item.get("recordedAt"), text(item.get("exportTime"))[:19],
                   item.get("stats", {}).get("total", 0)))
        return 0

    write_json(args.snapshot, file_state, compact=True)
    log("已更新基线快照：%s" % args.snapshot)

    payload = build_payload(records, now, file_state["exportTime"])
    write_json(args.changes, payload)
    log("已写入变更记录：%s（共 %d 条记录）" % (args.changes, len(records)))
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="对比 item.json 前后两次导出，生成变更记录")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA,
                        help="当前的 item.json 路径")
    parser.add_argument("--changes", type=Path, default=DEFAULT_CHANGES,
                        help="输出的变更记录路径")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT,
                        help="基线快照路径")
    parser.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS,
                        help="变更记录最多保留条数（默认 %d）" % DEFAULT_MAX_RECORDS)
    parser.add_argument("--init", action="store_true",
                        help="只重建基线，不产生变更记录")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印差异，不写入任何文件")
    parser.add_argument("--tz-offset", type=float, default=8.0,
                        help="记录时间使用的时区偏移（小时，默认 8 即北京时间）")
    parser.add_argument("--backfill-git", metavar="YYYY-MM-DD", default=None,
                        help="用 git 历史补齐该日期（含）之后的变更记录")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    tz = timezone(timedelta(hours=args.tz_offset))
    now = datetime.now(tz)

    if args.backfill_git:
        return run_backfill(args, now, tz)

    if not args.data.exists():
        log("找不到数据文件：%s" % args.data)
        return 1

    log("读取当前导出：%s" % args.data)
    cur_state = build_state(read_json(args.data))

    prev_state = None
    if not args.init and args.snapshot.exists():
        try:
            prev_state = read_json(args.snapshot)
        except (ValueError, OSError) as exc:
            log("基线快照无法读取（%s），将按首次运行处理" % exc)
            prev_state = None

    if prev_state:
        changes = diff_states(prev_state, cur_state)
        record = build_record(prev_state, cur_state, changes, now)
        if changes:
            log("检测到变更：")
        else:
            log("与上一次导出相比没有变化。")
    else:
        changes = []
        record = build_baseline_record(cur_state, now)
        log("未找到基线快照，本次作为首次运行建立基线。")

    print_changes(record)

    if args.dry_run:
        log("（--dry-run：未写入任何文件）")
        return 0

    # 内容完全一致且导出时间也没变（例如重复运行）时，不做任何改动，避免无意义的提交
    same_export = prev_state is not None and prev_state["exportTime"] == cur_state["exportTime"]
    if not changes and not record.get("baseline") and same_export:
        log("内容与导出时间均未变化，未写入任何文件。")
        return 0

    write_json(args.snapshot, cur_state, compact=True)
    log("已更新基线快照：%s" % args.snapshot)

    if args.init:
        log("（--init：仅重建基线，未写入变更记录）")
        return 0

    records = read_existing_records(args.changes)

    # 只有真正检测到变化（或首次建立基线）时才追加记录；
    # 新导出但内容没变时只刷新“最近检测时间”，不产生空记录。
    if changes or record.get("baseline"):
        records.insert(0, record)

    if args.max_records > 0:
        records = records[:args.max_records]

    payload = build_payload(records, now, cur_state["exportTime"])
    write_json(args.changes, payload)
    log("已写入变更记录：%s（共 %d 条记录）" % (args.changes, len(records)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
