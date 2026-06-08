import os
import sys
import subprocess
import shutil


def main():
    print("=" * 50)
    print("   智能打包助手 (专修 uiautomator2 缺失文件)")
    print("=" * 50)
    print("")

    # 1. 清理旧文件
    print("第一步：清理旧文件...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"  已删除 {folder} 文件夹")
    if os.path.exists('main.spec'):
        os.remove('main.spec')
        print("  已删除 main.spec 文件")
    print("  清理完成！")
    print("")

    # 2. 查找 uiautomator2 的必要文件路径
    print("第二步：查找 uiautomator2 必要零件...")
    try:
        import uiautomator2
        u2_path = os.path.dirname(uiautomator2.__file__)
        assets_path = os.path.join(u2_path, 'assets')
        print(f"  找到零件路径：{assets_path}")
    except Exception as e:
        print(f"  ❌ 失败：找不到 uiautomator2，请先安装它 (pip install uiautomator2)")
        input("按回车键退出...")
        return

    # 3. 开始打包
    print("")
    print("第三步：开始打包 (可能需要几分钟，请耐心等待)...")
    print("")

    # 构造命令
    # Windows 下分隔符是分号 ;
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "-F",
        "--add-data", f"{assets_path};uiautomator2\\assets",
        "main.py"
    ]

    try:
        # 运行打包命令
        subprocess.run(cmd, check=True)

        print("")
        print("=" * 50)
        print("   🎉 打包成功！")
        print("=" * 50)
        print(f"   生成的程序在：{os.path.join(os.getcwd(), 'dist', 'main.exe')}")
        print("   您可以把 dist 文件夹里的 main.exe 复制出来使用了。")
        print("=" * 50)

    except subprocess.CalledProcessError:
        print("")
        print("❌ 打包过程中出错了，请检查上面的红色报错信息。")
        print("   常见原因：缺少依赖库，请运行 pip install -r requirements.txt")

    print("")
    input("按回车键关闭此窗口...")


if __name__ == "__main__":
    main()
