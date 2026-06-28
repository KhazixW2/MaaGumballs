# collect_game_item_data

收集游戏物品数据的自动化流程，使用 maa-mcp 工具操作。

## 触发条件

用户要求收集游戏中的物品数据（如装备、武器、道具等）时使用此skill。

## 工作流程

### 1. 设备连接

```
mcp__maa-mcp__find_adb_device_list() → 选择设备 → mcp__maa-mcp__connect_adb_device(device_name)
```

### 2. 进入物品列表

1. `mcp__maa-mcp__ocr(controller_id)` - 识别当前屏幕，找到入口按钮坐标
2. `mcp__maa-mcp__click(controller_id, x, y)` - 点击进入物品类别（如"武器"）
3. `mcp__maa-mcp__wait(seconds=1.5)` - 等待界面加载
4. `mcp__maa-mcp__ocr(controller_id)` - 确认已进入物品列表页

### 3. 遍历收集物品详情

对列表中的每个物品：

1. `mcp__maa-mcp__click(controller_id, x, y)` - 点击物品进入详情页
2. `mcp__maa-mcp__wait(seconds=1.5)` - 等待详情加载
3. `mcp__maa-mcp__ocr(controller_id)` - 识别详情页数据
4. 提取关键字段：名称、类型、属性、描述、获取途径等
5. `mcp__maa-mcp__click(controller_id, x, y)` - 点击X按钮关闭 或 `mcp__maa-mcp__click_key(controller_id, key=4)` - 使用返回键
6. `mcp__maa-mcp__wait(seconds=1.5)` - 等待返回列表
7. `mcp__maa-mcp__ocr(controller_id)` - 确认已返回列表，继续下一个

### 4. 数据写入JSON

```json
{
  "item_category": "物品类别",
  "collection_date": "YYYY-MM-DD",
  "items": [
    {
      "name": "物品名称",
      "type": "类型",
      "属性1": 值,
      "属性2": 值,
      "source": "获取途径",
      "description": "描述"
    }
  ]
}
```

使用 `Write` 工具写入文件。

## OCR结果字段说明

`mcp__maa-mcp__ocr()` 返回格式：
```json
[{
  "box": [x, y, width, height],
  "score": 0.99,
  "text": "识别文字"
}]
```

- `box[0]`: 左上角X坐标
- `box[1]`: 左上角Y坐标
- `box[2]`: 宽度
- `box[3]`: 高度
- 中心点坐标: `x + width/2, y + height/2`

## 常用操作

| 操作 | 工具 |
|------|------|
| 截图OCR | `mcp__maa-mcp__ocr(controller_id)` |
| 单击 | `mcp__maa-mcp__click(controller_id, x, y)` |
| 双击 | `mcp__maa-mcp__double_click(controller_id, x, y)` |
| 滑动 | `mcp__maa-mcp__swipe(controller_id, start_x, start_y, end_x, end_y, duration)` |
| 返回键 | `mcp__maa-mcp__click_key(controller_id, key=4)` |
| 等待 | `mcp__maa-mcp__wait(seconds)` |

## 物品列表坐标推算

列表布局通常是网格或纵向排列，可根据OCR结果的 `box` 坐标推算下一个物品位置。

## 注意事项

- 点击前先确认坐标在物品名称范围内
- 关闭详情页优先使用X按钮，其次使用返回键(key=4)
- 等待时间可根据游戏加载速度调整（通常1.5-2秒）
- 复杂游戏可能需要滚动(swipe)列表才能看到所有物品

## 示例命令

```
/collect_game_item_data
```

用户描述：
```
收集装备栏下面武器栏的所有武器数据，包括名称、类型、攻击、命中率、需求力量、重量、获取途径。
```
