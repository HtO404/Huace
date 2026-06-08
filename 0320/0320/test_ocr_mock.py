# -*- coding: utf-8 -*-
"""
模拟测试脚本 - 验证 main.py 的 OCR 处理逻辑
"""
import re

def test_ocr_logic():
    """
    模拟测试 main.py 的 OCR 处理逻辑
    """
    # 模拟图片中的文本内容
    # 根据用户提供的图片描述："1.34°          LFP:0.0m"
    text = "1.34° LFP:0.0m"
    
    print(f"模拟识别结果:")
    print(repr(text))
    
    # 处理结果：去除空格，分割成数组
    # 去除所有空格
    text_no_spaces = re.sub(r'\s+', '', text)
    
    # 分割成数组（按数字分割）
    values = re.findall(r'[\d.]+', text_no_spaces)
    
    # 处理 '134' 去掉最后一位
    for i, val in enumerate(values):
        if val == '134':
            values[i] = val[:-1]  # 去掉最后一位
            break
    
    # 优先匹配LFP:后面的数字
    match = re.search(r'LFP[:\s]*([\d.]+)', text, re.IGNORECASE)
    lfp_value = ""
    if match:
        lfp_value = match.group(1)
        print(f"\nLFP值（正则匹配）: {lfp_value}")

    # 备用方案：使用分割后的数组
    if not lfp_value and values:
        lfp_value = values[0] if values else ""
        print(f"\nLFP值（数组提取）: {lfp_value}")
    
    print(f"\n处理后的数组（按数值分割）:")
    print(values)
    
    # 打印最终结果
    print(f"\n最终识别结果:")
    print(f"LFP值: {lfp_value}")
    print(f"所有识别值: {values}")
    
    # 测试 '134' 特殊处理
    print("\n=== 测试 '134' 特殊处理 ===")
    test_text = "134 0.0"
    test_text_no_spaces = re.sub(r'\s+', '', test_text)
    test_values = re.findall(r'[\d.]+', test_text_no_spaces)
    
    print(f"测试文本: {repr(test_text)}")
    print(f"处理前: {test_values}")
    
    for i, val in enumerate(test_values):
        if val == '134':
            test_values[i] = val[:-1]  # 去掉最后一位
            break
    
    print(f"处理后: {test_values}")


if __name__ == "__main__":
    test_ocr_logic()
