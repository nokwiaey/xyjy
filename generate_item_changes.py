#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 html/data/item.json 前后两次导出的差异，生成页面可读的变更记录。

用法::

    python generate_item_changes.py              # 对比并追加一条变更记录
    python generate_item_changes.py --init       # 只重建基线（不产生变更记录）
    python generate_item_changes.py --dry-run    # 只打印差异，不写文件
    python generate_item_changes.py --max-records 50

产出::

    html/data/item-changes.json    页面读取的变更记录（最新记录在最前）
    html/data/item-snapshot.json   上一次导出内容的基线快照（仅本脚本使用）

关于时间：``item.json`` 由内网手工导出（未来计划改为定时导出），因此记录里的
``recordedAt``（脚本运行时间）和 ``exportTime``（导出文件生成时间）**都不是**
项目实际发生变更的时间。两者只能界定变更发生在 ``prevExportTime`` 与
``exportTime`` 之间，页面上必须如实说明这一点。
"""

import argparse
import json
import sys
from datetime import datetime
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
    ("lis", "LIS 分析项目"),
    ("form", "申请单"),
]

CHANGES_NOTE = (
    "本文件由 generate_item_changes.py 自动生成，请勿手工编辑。"
    "recordedAt 为脚本检测/记录时间，exportTime 为 item.json 的导出时间；"
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
    return "%s（项目列表中已无此编码）" % code


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


def diff_lis_test_items(prev, cur):
    changes = []
    old, new = prev["lisTestItems"], cur["lisTestItems"]

    for test_item_id in sorted(set(new) - set(old)):
        entry = new[test_item_id]
        changes.append(make_change(
            "lis_test_added", "lis", "add", test_item_label(cur, test_item_id),
            [field_value("分析项目ID", test_item_id),
             field_value("代号", entry["code"]),
             field_value("名称", entry["name"]),
             field_value("互认标识", entry["des"])]))

    for test_item_id in sorted(set(old) - set(new)):
        entry = old[test_item_id]
        changes.append(make_change(
            "lis_test_removed", "lis", "remove", test_item_label(prev, test_item_id),
            [field_value("分析项目ID", test_item_id),
             field_value("代号", entry["code"]),
             field_value("名称", entry["name"]),
             field_value("互认标识", entry["des"])]))

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
            changes.append(make_change(
                "lis_test_modified", "lis", "update",
                test_item_label(cur, test_item_id), fields))

    return changes


def diff_lis_charge_items(prev, cur):
    changes = []
    old, new = prev["lisChargeItems"], cur["lisChargeItems"]

    def label(state, charge_item_id):
        entry = state["lisChargeItems"].get(charge_item_id)
        name = entry["name"] if entry else ""
        return "%s %s" % (charge_item_id, name) if name else charge_item_id

    for charge_item_id in sorted(set(new) - set(old)):
        entry = new[charge_item_id]
        changes.append(make_change(
            "lis_charge_added", "lis", "add", label(cur, charge_item_id),
            [field_value("收费项目ID", charge_item_id),
             field_value("收费项目名称", entry["name"]),
             field_value("对应 HIS 项目", item_label(cur, entry["his"]) if entry["his"] else "")]))

    for charge_item_id in sorted(set(old) - set(new)):
        entry = old[charge_item_id]
        changes.append(make_change(
            "lis_charge_removed", "lis", "remove", label(prev, charge_item_id),
            [field_value("收费项目ID", charge_item_id),
             field_value("收费项目名称", entry["name"]),
             field_value("对应 HIS 项目", item_label(prev, entry["his"]) if entry["his"] else "")]))

    for charge_item_id in sorted(set(old) & set(new)):
        before, after = old[charge_item_id], new[charge_item_id]
        fields = []
        if before["name"] != after["name"]:
            fields.append(field_change("收费项目名称", before["name"], after["name"]))
        if before["his"] != after["his"]:
            fields.append(field_change(
                "对应 HIS 项目",
                item_label(prev, before["his"]) if before["his"] else "",
                item_label(cur, after["his"]) if after["his"] else ""))
        if fields:
            changes.append(make_change(
                "lis_charge_modified", "lis", "update",
                label(cur, charge_item_id), fields))

    return changes


def diff_lis_links(prev, cur):
    """比对 LIS 关联关系（收费项目 ↔ 分析项目 ↔ 检验分组），按收费项目汇总。"""
    changes = []
    old, new = prev["lisLinks"], cur["lisLinks"]

    def group_names(state, group_ids):
        names = []
        for group_id in group_ids:
            entry = state["lisGroups"].get(group_id)
            names.append("%s %s" % (group_id, entry["name"]) if entry and entry["name"]
                         else group_id)
        return "、".join(names) if names else "（未分组）"

    def link_label(state, entry):
        return "%s（分组：%s）" % (test_item_label(state, entry["testItemId"]),
                                   group_names(state, entry["groups"]))

    def owner_title(state, charge_item_id):
        entry = state["lisChargeItems"].get(charge_item_id)
        if entry and entry["his"]:
            return item_label(state, entry["his"])
        if entry:
            return "收费项目 %s %s（未关联 HIS 项目）" % (charge_item_id, entry["name"])
        return "收费项目 %s（未匹配到收费项目表）" % charge_item_id

    added_keys = sorted(set(new) - set(old))
    removed_keys = sorted(set(old) - set(new))
    common_keys = sorted(set(old) & set(new))

    buckets = {}  # charge_item_id -> {"add": [...], "remove": [...], "update": [...]}

    for key in added_keys:
        entry = new[key]
        buckets.setdefault(entry["chargeItemId"], {"add": [], "remove": [], "update": []})
        buckets[entry["chargeItemId"]]["add"].append(link_label(cur, entry))

    for key in removed_keys:
        entry = old[key]
        buckets.setdefault(entry["chargeItemId"], {"add": [], "remove": [], "update": []})
        buckets[entry["chargeItemId"]]["remove"].append(link_label(prev, entry))

    for key in common_keys:
        before, after = old[key], new[key]
        if before["groups"] != after["groups"]:
            buckets.setdefault(after["chargeItemId"], {"add": [], "remove": [], "update": []})
            buckets[after["chargeItemId"]]["update"].append(
                "%s：%s → %s" % (test_item_label(cur, after["testItemId"]),
                                 group_names(prev, before["groups"]),
                                 group_names(cur, after["groups"])))

    for charge_item_id in sorted(buckets):
        bucket = buckets[charge_item_id]
        title = owner_title(cur if charge_item_id in cur["lisChargeItems"] else prev,
                            charge_item_id)
        if bucket["add"]:
            changes.append(make_change(
                "lis_link_added", "lis", "add", title,
                [field_value("新增关联分析项目", value) for value in bucket["add"]]))
        if bucket["remove"]:
            changes.append(make_change(
                "lis_link_removed", "lis", "remove", title,
                [field_value("取消关联分析项目", value) for value in bucket["remove"]]))
        if bucket["update"]:
            changes.append(make_change(
                "lis_link_modified", "lis", "update", title,
                [field_value("关联分组调整", value) for value in bucket["update"]]))

    return changes


def diff_states(prev, cur):
    changes = []
    item_changes, wholesale_codes = diff_items(prev, cur)
    changes += item_changes
    changes += diff_prices(prev, cur, skip_codes=wholesale_codes)
    changes += diff_lis_groups(prev, cur)
    changes += diff_lis_test_items(prev, cur)
    changes += diff_lis_charge_items(prev, cur)
    changes += diff_lis_links(prev, cur)
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
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    now = datetime.now()

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

    payload = {}
    if args.changes.exists():
        try:
            payload = read_json(args.changes)
        except (ValueError, OSError):
            payload = {}
    records = payload.get("records") if isinstance(payload.get("records"), list) else []

    # 只有真正检测到变化（或首次建立基线）时才追加记录；
    # 新导出但内容没变时只刷新“最近检测时间”，不产生空记录。
    if changes or record.get("baseline"):
        records.insert(0, record)

    if args.max_records > 0:
        records = records[:args.max_records]

    last_change_at = None
    for item in records:
        if item.get("stats", {}).get("total"):
            last_change_at = item.get("recordedAt")
            break

    payload = {
        "schema": SCHEMA_VERSION,
        "note": CHANGES_NOTE,
        "generatedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "lastCheckedAt": record["recordedAt"],
        "lastExportTime": cur_state["exportTime"],
        "lastChangeAt": last_change_at,
        "recordCount": len(records),
        "categories": [{"key": key, "label": label} for key, label in CATEGORIES],
        "records": records,
    }
    write_json(args.changes, payload)
    log("已写入变更记录：%s（共 %d 条记录）" % (args.changes, len(records)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
