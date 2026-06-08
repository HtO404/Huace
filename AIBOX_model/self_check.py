# -*- coding: utf-8 -*-
"""
自检脚本 - 无需设备，验证代码逻辑
"""
import os
import sys
import ast


def check_syntax(file_path):
    """检查Python语法"""
    print(f"检查语法: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f"  [OK] 语法正确")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] 语法错误: {e}")
        return False


def check_imports(file_path):
    """检查导入语句（不实际导入）"""
    print(f"检查导入: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)
        
        print(f"  [OK] 发现导入: {', '.join(set(imports))}")
        return True
    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        return False


def check_config():
    """检查配置文件"""
    print("检查配置文件: config.ini")
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if not os.path.exists(config_path):
        print("  ✗ 配置文件不存在")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键配置项
    required_sections = ['AppConfig', 'DeviceConfig', 'TestParams', 'UIElements', 'OutputConfig']
    issues = []
    
    for section in required_sections:
        if f'[{section}]' not in content:
            issues.append(f"缺少 [{section}] 配置节")
    
    # 检查 cycle_times 是否被注释
    if '#cycle_times' in content or ';cycle_times' in content:
        issues.append("cycle_times 被注释，可能导致运行时错误")
    
    if issues:
        for issue in issues:
            print(f"  [FAIL] {issue}")
        return False
    else:
        print("  [OK] 配置检查通过")
        return True


def check_dead_logic():
    """检查已知的死逻辑问题"""
    print("检查死逻辑问题...")
    
    main_path = os.path.join(os.path.dirname(__file__), 'main.py')
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # 检查1: continue 位置问题（修复后应该没有这个问题了）
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'continue  # 失败后跳到下一次大循环' in line:
            # 检查下一行是否是 if self.test_params
            if i + 1 < len(lines) and 'if self.test_params' in lines[i + 1]:
                issues.append(f"第{i+1}行: continue 在 if 判断之前，可能导致逻辑错误")
    
    # 检查2: 未使用的 wait_loading_dialog_init
    if 'def wait_loading_dialog_init(self):' in content:
        # 检查是否有调用
        if content.count('wait_loading_dialog_init') == 1:  # 只有定义，没有调用
            issues.append("wait_loading_dialog_init 方法定义但未调用")
    
    # 检查3: 冗余 print
    if 'print("=" * 60)' in content and 'print(f"总测试次数' in content:
        issues.append("_generate_summary 中有冗余 print 输出")
    
    if issues:
        for issue in issues:
            print(f"  [FAIL] {issue}")
        return False
    else:
        print("  [OK] 未发现已知死逻辑问题")
        return True


def main():
    print("=" * 60)
    print("AIBOX_model 代码自检")
    print("=" * 60)
    print()
    
    all_pass = True
    
    # 检查 main.py
    main_path = os.path.join(os.path.dirname(__file__), 'main.py')
    all_pass &= check_syntax(main_path)
    all_pass &= check_imports(main_path)
    print()
    
    # 检查 utils.py
    utils_path = os.path.join(os.path.dirname(__file__), 'utils.py')
    all_pass &= check_syntax(utils_path)
    all_pass &= check_imports(utils_path)
    print()
    
    # 检查配置
    all_pass &= check_config()
    print()
    
    # 检查死逻辑
    all_pass &= check_dead_logic()
    print()
    
    print("=" * 60)
    if all_pass:
        print("[OK] 所有检查通过")
    else:
        print("[FAIL] 发现一些问题，请修复后再测试")
    print("=" * 60)
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
