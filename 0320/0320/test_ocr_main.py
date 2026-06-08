# -*- coding: utf-8 -*-
"""
OCR测试脚本 - 使用 main.py 的识别逻辑测试 region_percent.png
"""
import os
import re
import pytesseract
from PIL import Image, ImageEnhance

# 配置Tesseract OCR路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_ocr_logic():
    """
    使用 main.py 的 OCR 识别逻辑测试 region_percent.png
    """
    # 图片路径
    image_path = r'd:\Hcode\0320\0320\region_percent.png'
    
    if not os.path.exists(image_path):
        print(f"错误：图片文件不存在 - {image_path}")
        return
    
    print(f"开始测试 OCR 识别: {image_path}")
    
    try:
        # 打开图片
        image = Image.open(image_path)
        
        # 增强图像对比度提高识别率
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(2.0)
        
        # OCR识别（使用与 main.py 相同的配置）
        text = pytesseract.image_to_string(
            enhanced,
            lang='eng'
        ).strip()
        
        print(f"\n原始识别结果:")
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
        
    except Exception as e:
        print(f"OCR识别异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_ocr_logic()
