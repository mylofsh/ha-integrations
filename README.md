# A.O.史密斯 & 352 智能家居 Home Assistant 集成

包含两个独立集成，分别在对应子目录中：

| 集成 | 目录 | HACS 名称 |
|---|---|---|
| AI-LiNK 燃气热水器 | [`ailink_water_heater/`](ailink_water_heater/) | AI-LiNK Water Heater |
| 352 空气净化器 | [`air_purifier_352/`](air_purifier_352/) | 352 Air Purifier |

## HACS 安装

两个集成都通过同一个仓库添加：

1. HACS → 右上角三个点 → 自定义仓库
2. 仓库地址：`https://github.com/mylofsh/ha-ailink-water-heater`
3. 类别选 **集成**
4. 分别搜索安装

## 手动安装

复制对应子目录的 `custom_components/` 到 HA 的 `custom_components/`：

```bash
# 只装热水器
cp -r ailink_water_heater/custom_components/ailink_water_heater /path/to/ha/config/custom_components/

# 只装净化器
cp -r air_purifier_352/custom_components/air_purifier_352 /path/to/ha/config/custom_components/
```

## 各集成文档

- [AI-LiNK 热水器](ailink_water_heater/README.md)
- [352 空气净化器](air_purifier_352/README.md)
