# -*- coding: utf-8 -*-
"""
OCR测试脚本 - 识别 region_percent.png 图片
功能：识别图片中的文字，存为数组，去除空格并打印
"""
import os
import re
import pytesseract
from PIL import Image, ImageEnhance

# 配置Tesseract OCR路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr_test():
    """
    OCR测试函数
    """
    # 图片路径
    image_path = r'd:\Hcode\0320\0320\region_percent.png'
    
    if not os.path.exists(image_path):
        print(f"错误：图片文件不存在 - {image_path}")
        return
    
    print(f"开始识别图片: {image_path}")
    
    try:
        # 打开图片
        image = Image.open(image_path)
        
        # 增强图像对比度提高识别率
        enhancer = ImageEnhance.Contrast(image)
        enhanced_image = enhancer.enhance(2.0)
        
        # OCR识别
        text = pytesseract.image_to_string(enhanced_image, lang='eng')
        
        print(f"\n原始识别结果:")
        print(repr(text))
        
        # 处理结果：去除空格，分割成数组
        # 去除所有空格
        text_no_spaces = re.sub(r'\s+', '', text)
        
        # 分割成数组（按数字或其他有意义的分割）
        # 这里简单按非数字字符分割
        values = re.findall(r'[\d.]+', text_no_spaces)
        
        for i, val in enumerate(values):
                values[i] = val[:-1]  # 去掉最后一位
                break
        
        # 或者按行分割
        lines = text.strip().split('\n')
        lines_no_spaces = [line.replace(' ', '') for line in lines if line.strip()]
        
        print(f"\n处理后的数组（按数值分割）:")
        print(values)
        
        print(f"\n处理后的数组（按行分割）:")
        print(lines_no_spaces)
        
        # 打印变量获取到的值
        print(f"\n变量获取到的值:")
        print(f"values = {values}")
        print(f"lines_no_spaces = {lines_no_spaces}")
        
    except Exception as e:
        print(f"OCR识别异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    ocr_test()
