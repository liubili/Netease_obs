# 网易云音乐 OBS 插件脚本

> 作者: liubiliGrass  
> 功能：实时读取网易云音乐当前播放歌曲信息并在 OBS 中显示歌词、进度、封面等信息


## 功能简介

- 🎵 实时获取网易云音乐播放歌曲名与歌手
- 📃 同步显示歌词（支持翻译歌词）
- ⏱️ 显示播放进度（支持 mm:ss 与 百分比格式）
- 🖼️ 下载当前歌曲封面图 (未完成)
- 🪄 OBS 中通过文本源与图片源展示上述内容


## 待办

- [ ] 完成封面图下载功能
- [ ] 拆分翻译歌词
- [ ] 添加切换输出到文件/输出到歌词选项

## 效果预览

<img width="1784" height="823" alt="1752908527-351335-image" src="https://github.com/user-attachments/assets/c2a8eb1c-d8a6-4f5b-972a-b12ac350c201" />



## 版本偏移链适配

> 3.1.14 64位 版本未知`[0x01C6D230, 0xB8]`
> 
> 3.1.15 64位 Build:204255 Patch:b142624 `[0x01C713B0, 0xB8]`
>
> 3.1.15 64位 Build:204255 Patch:6842b9d `[0x01C713B0, 0xB8]`
>
> 3.1.16 64位 Build:204365 Patch:1a85061 `[0x01C6EBD0,0xB8]`
>
> 3.1.17 64位 Build:204416 Patch:0b7c7b7 `[0x01C9F1B0,0xB8]`
>
> 3.1.18 64位 Build:204470 Patch:92b0833 `[0x01CA1190,0xB8]`
> 3.1.19 64位 Build:204510 Patch:e4c4c2a `[0x01CCBB50,0xB8]`
> 3.1.20 64位 Build:204558 Patch:f84632d `[0x01CCBB70,0xB8]`
## ⚙️ 配置项说明

| 参数名称             | 类型     | 说明                                       |
|----------------------|----------|--------------------------------------------|
| `refresh_interval`   | 整数     | 刷新间隔时间（毫秒），默认：`1000`        |
| `enable_lyrics`      | 布尔     | 是否启用歌词功能                           |
| `enable_translation` | 布尔     | 是否启用翻译歌词                           |
| `enable_progress`    | 布尔     | 是否启用播放进度显示                       |
| `enable_cover`       | 布尔     | 是否启用歌曲封面下载                       |
| `progress_format`    | 字符串   | 播放进度格式：`mm:ss` 或 `percent`         |
| `subtitle_offset_ms` | 整数     | 歌词显示偏移（单位：毫秒，正值为延后）    |

> 所有参数均可在 OBS 脚本配置界面中设置。


### 推荐设置

- `刷新间隔`: 200
- `字幕偏移`: 1200

## 🧰 所需依赖

需确保以下 Python 包已正确安装：

```bash
pip install pymem psutil requests pywin32
```

## 内部实现要点

使用 pymem 结合偏移链方式读取网易云音乐内存中当前播放进度

使用网易云公开接口获取歌词与封面

使用 win32gui 获取网易云窗口标题从而解析出当前歌曲名与歌手名

自动比对匹配 API 搜索结果中的歌曲 ID

### 第三方包及其许可证
- psutil (BSD License)
- requests (Apache 2.0)
- pymem (MIT License)
- pywin32 (MIT License)
## 许可

无许可证。未经许可，不得商用。本项目所有权利归 @liu_bili (liubiliGrass/liu_bili_Grass) 所有,保留所有权利。

## 关于许可

Py脚本可以随便修改，保留所有权利是为了防止被抹名/修改然后付费二次分发，比如咸鱼/pdd卖脚本这种行为，不会对个人用户/非商用进行任何追责