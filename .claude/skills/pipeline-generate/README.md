# pipeline-generate

本目录包含 MaaFramework pipeline OCR 节点生成工具。

## 包含内容

- `generate_node.py`: 生成单个 OCR 节点并合并到目标 pipeline 文件
- `generate_sweep.py`: 批量生成不同 expand 值的 sweep pipeline，辅助选择最佳 ROI
- `SKILL.md`: skill 说明文档
- `maahub_meta.json`: 网站元信息

## 使用方法

### 生成单个节点

```bash
python .claude/skills/pipeline-generate/generate_node.py "目标文字" NodeName path/to/pipeline.json --expand 20 --overwrite
```

### 扫描 expand 值

```bash
python .claude/skills/pipeline-generate/generate_sweep.py "目标文字" "x,y,w,h" 0,5,10,15,20,25,30
```

## 说明

- `generate_node.py` 将根据 OCR 识别结果生成节点并将其写入 pipeline。
- `generate_sweep.py` 生成一个 sweep pipeline，用于通过 run_pipeline 验证不同 expand 值的效果。
- 目标 pipeline 支持相对路径和绝对路径。
