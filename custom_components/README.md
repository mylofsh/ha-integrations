# A.O.史密斯 & 352 智能家居 Home Assistant 集成

两个独立 Home Assistant 集成，位于 `custom_components/` 下：

| 集成 | 目录 | 说明 |
|---|---|---|
| AI-LiNK Water Heater | [`custom_components/ailink_water_heater/`](custom_components/ailink_water_heater/) | A.O.史密斯燃气热水器 |
| 352 Air Purifier | [`custom_components/air_purifier_352/`](custom_components/air_purifier_352/) | 352 空气净化器 |

## HACS 安装

1. HACS → 右上角三个点 → 自定义仓库
2. 仓库地址：`https://github.com/mylofsh/ha-ailink-water-heater`
3. 类别选 **集成**
4. 分别搜索安装

## 手动安装

复制对应目录到 HA 的 `custom_components/`：

```bash
# 只装热水器
cp -r custom_components/ailink_water_heater /path/to/ha/config/custom_components/

# 只装净化器
cp -r custom_components/air_purifier_352 /path/to/ha/config/custom_components/
```

## 各集成文档

- [AI-LiNK 热水器](custom_components/ailink_water_heater/README.md)
- [352 空气净化器](custom_components/air_purifier_352/README.md)
