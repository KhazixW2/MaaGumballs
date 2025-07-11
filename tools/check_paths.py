#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path


def check_resource_paths():
    """检查interface.json中的资源路径是否正确"""

    # 读取interface.json
    interface_path = Path("f:/workspace/MaaGumballs/assets/interface.json")

    if not interface_path.exists():
        print(f"错误: interface.json文件不存在于 {interface_path}")
        return False

    with open(interface_path, "r", encoding="utf-8") as f:
        interface_data = json.load(f)

    # 获取PROJECT_DIR (interface.json所在目录)
    project_dir = interface_path.parent
    print(f"PROJECT_DIR: {project_dir}")

    # 检查资源配置
    if "resource" not in interface_data:
        print("错误: interface.json中没有resource配置")
        return False

    all_paths_valid = True

    for resource_config in interface_data["resource"]:
        resource_name = resource_config.get("name", "未知")
        print(f"\n检查资源配置: {resource_name}")

        if "path" not in resource_config:
            print(f"  错误: 资源配置 {resource_name} 没有path字段")
            all_paths_valid = False
            continue

        for path_template in resource_config["path"]:
            # 替换{PROJECT_DIR}为实际路径
            actual_path = path_template.replace("{PROJECT_DIR}", str(project_dir))
            path_obj = Path(actual_path)

            print(f"  检查路径: {path_template}")
            print(f"  实际路径: {actual_path}")

            if path_obj.exists():
                print(f"  ✓ 路径存在")

                # 检查是否包含pipeline目录
                pipeline_dir = path_obj / "pipeline"
                if pipeline_dir.exists():
                    print(f"  ✓ pipeline目录存在")

                    # 检查pipeline目录中的文件
                    json_files = list(pipeline_dir.glob("*.json"))
                    if json_files:
                        print(f"  ✓ 发现 {len(json_files)} 个JSON文件")
                    else:
                        print(f"  ⚠ pipeline目录中没有JSON文件")
                else:
                    print(f"  ⚠ pipeline目录不存在")
            else:
                print(f"  ✗ 路径不存在")
                all_paths_valid = False

    return all_paths_valid


if __name__ == "__main__":
    print("检查MaaGumballs资源路径配置...")
    if check_resource_paths():
        print("\n✓ 所有资源路径配置正确")
    else:
        print("\n✗ 存在资源路径配置问题")
