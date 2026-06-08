import os

# 配置参数
FILE_SIZE_MB = 500  # 文件大小：500MB
OUTPUT_FILE = "500mb_test_file.dat"  # 输出文件名，格式不限，.dat/.txt/.bin都可以


def create_fixed_size_file(file_path, size_mb):
    """创建指定大小的文件（快速生成，无需随机数据）"""
    # 转换为字节：1MB = 1024*1024 字节
    size_bytes = size_mb * 1024 * 1024

    # 如果文件已存在且大小匹配，直接返回
    if os.path.exists(file_path):
        current_size = os.path.getsize(file_path)
        if current_size == size_bytes:
            print(f"文件已存在且大小符合要求：{file_path} ({size_mb}MB)")
            return
        else:
            print(f"文件已存在但大小不符，重新生成...")

    # 快速生成文件（用空字节填充，速度远快于随机字节）
    print(f"正在生成 {size_mb}MB 的文件，请稍候...")
    with open(file_path, 'wb') as f:
        # 分块写入，避免一次性申请超大内存
        block_size = 1024 * 1024  # 每次写1MB
        blocks = size_bytes // block_size
        remaining = size_bytes % block_size

        for _ in range(blocks):
            f.write(b'\0' * block_size)  # 用空字节填充，生成速度最快
        if remaining > 0:
            f.write(b'\0' * remaining)

    # 验证文件大小
    final_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"文件生成完成！")
    print(f"文件名：{file_path}")
    print(f"实际大小：{final_size:.2f}MB")


if __name__ == "__main__":
    create_fixed_size_file(OUTPUT_FILE, FILE_SIZE_MB)