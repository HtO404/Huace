import uiautomator2 as u2
import time

d = u2.connect()
#通过包名打开应用
d.press('back')
a = d(text="强").count
print(a)

# # 获取页面XML结构
# xml_content = d.dump_hierarchy()
# print(xml_content)



