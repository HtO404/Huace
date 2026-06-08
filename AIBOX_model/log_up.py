#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log_up.py — 通用日志与导出模块

整合了你在 Hcode 各项目中重复编写的 setup_logging()、get_export_path()、
load_config()、CSV 写入等样板代码。新脚本只需：

    from log_up import setup_logging, get_export_path, load_config, \
        write_csv_row, write_csv_summary

即可一行搞定日志和导出路径配置，不再造轮子。

作者: auto-generated from 我的编码习惯总结.md
日期: 2026-05-13
"""

import os
import csv
import logging
from datetime import datetime
from configparser import ConfigParser


# ═══════════════════════════════════════════════════════════════
# 日志配置
# ═══════════════════════════════════════════════════════════════

LOG_FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logging(log_path: str, level: int = logging.INFO) -> None:
    """
    配置日志系统 —— FileHandler + StreamHandler 双输出。

    用法:
        setup_logging(log_path)
        logging.info(\"测试开始\")

    参数:
        log_path: 日志文件完整路径
        level:    日志级别，默认 logging.INFO
    """
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


# ═══════════════════════════════════════════════════════════════
# 导出路径生成
# ═══════════════════════════════════════════════════════════════

def get_export_path(root_path: str, project_name: str,
                    export_num: int, date_str: str = None) -> tuple:
    """
    生成 CSV 和日志文件的完整路径，自动创建目录。

    路径格式:
        CSV:  {root_path}/{project_name}_csv/{date_str}_{export_num:02d}.csv
        日志: {root_path}/{project_name}_log/{date_str}_{export_num:02d}_{project_name}_log.txt

    用法:
        csv_path, log_path = get_export_path('.', 'my_project', 1)
        # → ./my_project_csv/20260513_01.csv
        # → ./my_project_log/20260513_01_my_project_log.txt

    参数:
        root_path:    输出根目录（通常从 config.ini 读取）
        project_name: 项目名称（用于目录/文件名）
        export_num:   导出编号（1 起）
        date_str:     日期字符串 YYYYMMDD，默认当天

    返回:
        (csv_path, log_path)
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')

    csv_dir = os.path.join(root_path, f'{project_name}_csv')
    log_dir = os.path.join(root_path, f'{project_name}_log')

    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    csv_path = os.path.join(csv_dir, f'{date_str}_{export_num:02d}.csv')
    log_path = os.path.join(log_dir,
                            f'{date_str}_{export_num:02d}_{project_name}_log.txt')

    return csv_path, log_path


# ═══════════════════════════════════════════════════════════════
# 配置文件加载
# ═══════════════════════════════════════════════════════════════

def load_config(config_path: str = 'config.ini') -> ConfigParser:
    """
    加载 config.ini 配置文件。

    用法:
        config = load_config()
        project_name = config.get('AppConfig', 'project_name')
        cycle_times = config.getint('TestParams', 'cycle_times')

    参数:
        config_path: ini 文件路径，默认 'config.ini'

    返回:
        ConfigParser 对象
    """
    config = ConfigParser()
    config.read(config_path, encoding='utf-8')
    return config


# ═══════════════════════════════════════════════════════════════
# CSV 写入
# ═══════════════════════════════════════════════════════════════

CSV_HEADERS = ['时间', '序号', '测试项', '状态', '详细信息']


def init_csv(csv_path: str, headers: list = None) -> None:
    """
    创建 CSV 文件并写入表头。

    用法:
        init_csv(csv_path)
        # 或用自定义表头:
        init_csv(csv_path, ['时间', '操作', '结果'])

    参数:
        csv_path: CSV 文件路径
        headers:  表头列表，默认使用标准 ['时间','序号','测试项','状态','详细信息']
    """
    if headers is None:
        headers = CSV_HEADERS
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)


def write_csv_row(csv_path: str, row: list) -> None:
    """
    向 CSV 文件追加一行数据（自动加时间戳）。

    用法:
        write_csv_row(csv_path, [1, '开机关机', '成功', '正常启动'])

    参数:
        csv_path: CSV 文件路径
        row:      数据列表，不含时间（函数会自动在最前面插入当前时间）
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp] + row)


def write_csv_summary(csv_path: str, total: int, success: int,
                      fail: int, extra_rows: list = None) -> None:
    """
    在 CSV 末尾写入汇总统计信息。

    用法:
        write_csv_summary(csv_path, total, success, fail)

    参数:
        csv_path:   CSV 文件路径
        total:      总测试次数
        success:    成功次数
        fail:       失败次数
        extra_rows: 额外追加的自定义行列表，每项为 [key, value]
    """
    rate = (success / total * 100) if total > 0 else 0.0

    rows = [
        [],
        ['===== 汇总统计 ====='],
        ['总测试次数', total],
        ['成功次数', success],
        ['失败次数', fail],
        ['成功率', f'{rate:.2f}%'],
    ]

    if extra_rows:
        rows.extend(extra_rows)

    with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(r)


# ═══════════════════════════════════════════════════════════════
# 日志辅助 —— 测试循环中常用的分段标记
# ═══════════════════════════════════════════════════════════════

def log_test_start(project_name: str, cycle_times: int = None):
    """输出测试开始的装饰线 + 基本信息"""
    logging.info("=" * 60)
    logging.info(f"{project_name} 测试开始")
    if cycle_times is not None:
        logging.info(f"循环次数: {cycle_times}")
    logging.info("=" * 60)


def log_test_cycle(cycle_num: int):
    """输出第 N 次测试循环的起始标记"""
    logging.info(f"===== 第{cycle_num}次测试开始 =====")


def log_test_cycle_ok(cycle_num: int):
    """输出第 N 次测试成功的标记"""
    logging.info(f"===== 第{cycle_num}次测试成功 =====")


def log_test_cycle_fail(cycle_num: int, error: str):
    """输出第 N 次测试失败的标记"""
    logging.error(f"第{cycle_num}次测试失败: {error}")


def log_step(step_num: int, description: str):
    """输出步骤标记线

    用法:
        log_step(1, "下电")
        # → # -------------------------- 步骤1：下电 --------------------------

    参数:
        step_num:     步骤编号
        description:  步骤描述
    """
    sep = "-" * 26
    logging.info(f"{sep} 步骤{step_num}：{description} {sep}")


def log_summary(total: int, success: int, fail: int):
    """输出汇总统计到日志"""
    rate = (success / total * 100) if total > 0 else 0.0
    logging.info("===== 汇总统计 =====")
    logging.info(f"总测试次数: {total}")
    logging.info(f"成功次数: {success}")
    logging.info(f"失败次数: {fail}")
    logging.info(f"成功率: {rate:.2f}%")
