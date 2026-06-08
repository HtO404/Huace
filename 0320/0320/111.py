import uiautomator2 as u2
import time
import logging
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

d = u2.connect()
screenshot = d.screenshot()  # 获取PIL Image对象
screen_width, screen_height = screenshot.size
print(f"屏幕尺寸: {screen_width} x {screen_height}")

# d.click(300, 600)
# d.click(300, 600)
# # d.click(300, 500)
# time.sleep(4)
# d.click(1620, 600)
# d.click(1620, 600)
def ocr_win(crop_area):
    screenshot = d.screenshot()
    region_image = screenshot.crop(crop_area)
    # 5. 保存裁剪区域用于调试
    region_image.save("region_percent.png")
    print("裁剪区域已保存为 region_percent.png")
    # 6. OCR识别
    # text = pytesseract.image_to_string(region_image, lang='eng').strip()
    text = pytesseract.image_to_string(
        region_image,
        config='--psm 7 -c tessedit_char_whitelist=0123456789.'  # 只允许数字和小数点
    ).strip()
    # text = pytesseract.image_to_string(region_image, lang='chi_sim+eng').strip()
    return text.replace(' ', '')


# 3. 使用百分比定义目标区域
# x轴从80%到92%，y轴从40%到50%
x_start_percent = 0.45  # 80%
x_end_percent = 0.67  # 92%
y_start_percent = 0.90  # 40%
y_end_percent = 0.98  # 50%
# 将百分比转换为实际像素坐标
x_start = int(screen_width * x_start_percent)
x_end = int(screen_width * x_end_percent)
y_start = int(screen_height * y_start_percent)
y_end = int(screen_height * y_end_percent)
# 计算宽度和高度
width = x_end - x_start
height = y_end - y_start
print(f"转换后的区域: x={x_start}, y={y_start}, width={width}, height={height}")
# 4. 裁剪指定区域
crop_area = (x_start, y_start, x_end, y_end)

res = ocr_win(crop_area)
print(res)