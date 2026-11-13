# 渲染数据格式（schema_version = 1）

`render_reader.py`仅用Python标准库。所有字符串按纯文本转义；不需要编写HTML。输入是一个JSON对象：

- `paper`: `title`英文题名、`title_zh`中文题名、`authors`、`citation`、可选`doi`及`course`。
- `items`: **唯一的顺序清单**，按原文排列，包含下面五种单元。渲染器按数组顺序输出，不按类型或章节重新分组。
- `images.pages`: PDF页码字符串映射到图像文件路径或`data:image/...`。相对路径相对于JSON所在目录。
- `images.figures`: 任意图片键映射到图版图像路径或data URI。与页图分开，可在一页裁出多幅图。
- `argument`: 文末论证总览，见下文。
- 可选`coverage`: 字符串数组，仅记录实际影响理解的材料缺失、源文不一致或必要来源说明。非空时在文末“材料说明”中折叠显示；不填写制作流程、功能介绍或遵循规范的声明。
- 旧字段`reading_note`、`ribbon`仍可出现在输入中，但不再渲染。必要的材料问题应写入相关单元或`coverage`，不要新建顶部导读。

## items单元

所有单元有唯一`id`，格式为字母开头，后接字母、数字、下划线或连字符。保留ID：`top`、`main`、`argument`、`source`、`source-dialog`、`course`。不要将段落/图版ID用于章节。`order_page`使用合并PDF的**1起始页序**，不是印刷页号；有此字段的单元必须单调不下降。

### section：章节/小节起点

`type: "section"`，字段`id`、`title`（中文）、可选`subtitle`（英文原节名）、`kicker`、`description`。`nav_label`存在时加入吸顶章节导航。渲染器在下一节、章或参考文献前关闭本节。`kicker`仅用于源文已有的章节编号/名称，`description`仅用于具体内容说明，不添加装饰口号或模板介绍。

### chapter：大章幕封

`type: "chapter"`，字段`id`、`title`、`kicker`、`description`，可选`nav_label`。用于论文真正的大章，不生成无依据的章或重新组织原文。

### paragraph：英中对照与中文批注

```json
{
  "type": "paragraph",
  "id": "P01",
  "order_page": 1,
  "pages": [1, 2],
  "en": "The intervention improved survival in the animal model.",
  "zh": "该干预改善了动物模型的存活结局。",
  "function": "本段的具体功能。",
  "role": "本段与前后文如何共同推进中心论证。",
  "note": "具体的论证技巧、推断边界或潜在漏洞。",
  "category": "evidence",
  "highlights": {"evidence": ["improved survival in the animal model"]},
  "highlight_pairs": [
    {"category": "evidence", "en": "improved survival in the animal model", "zh": ["改善了动物模型的存活结局"]}
  ],
  "terms": [],
  "subheading": "可选的原有子标题"
}
```

- `pages`列出该段实际跨越的全部源页；`order_page`是该单元起始位置，用于顺序检查。
- `en`、`zh`、`function`、`role`、`note`均必填。后三项默认必须包含中文，不仅翻译标签。
- `category`为`thesis`、`concept`、`evidence`、`concession`、`method`或`neutral`，控制批注卡。它不强制英文高亮类别。
- `highlights`使用前五种类别，值为原文中的确切短语数组，大小写不敏感。不存在的短语报错；重叠只绘制最先选定的范围。先放最重要的长范围，避免关键词切碎核心句。
- `terms`可选，最多自动补充两个概念词，仍只标记原文中存在且不重叠的位置。
- `highlight_pairs`逐项对应所有实际显示的英文高亮，包括`terms`。每项有同一`category`、确切英文`en`和中文片段数组`zh`。没有英文高亮可省略或填空数组。渲染器检查双边覆盖、类别、原文/译文匹配及中文选区不重叠；不会自动生成翻译对齐。重复术语应选更长的唯一中文短语定位，避免标错出现位置。
- 意译造成语序重组时，一个英文选区可对应多个中文片段；用同一数组列出。英文与中文颜色含义一致，图例切换同步作用于两边。

### figure：源图与完整图注

与paragraph共享`en`（完整英文图注）、`zh`（完整图注意译）及三项中文批注。额外字段：

```json
{
  "type": "figure",
  "id": "F1",
  "title": "图1｜原图的具体主题",
  "short_title": "图1",
  "order_page": 3,
  "pages": [4],
  "image_page": 3,
  "image_key": "figure-1"
}
```

此处只展示额外字段，实际记录还必须包含共享的正文与批注字段。`image_key`对应`images.figures`。`order_page`按图版首次出现位置；`pages`可指向不同的图注页。将记录插在正文相应位置，**不能生成一个文末主图数组代替原有顺序**。

### references：文献表

包含且仅包含一个`type: "references"`记录，字段`id`、`entries`（原始著录字符串数组），可选`order_page`、`description`、`nav_label`及三项中文批注。没有文献表时`entries: []`并说明。三项批注只有全部提供时才显示，不自动补充通用批注。文献逐条保留英文著录；不编造未提供的题名或DOI。

## argument：文末总览

```json
{
  "thesis": "作者核心主张的一句话版本。",
  "chain": [
    {"label": "问题", "text": "具体问题。", "target": "intro"},
    {"label": "论点", "text": "作者提出的解释。", "target": "P01"},
    {"label": "证据", "text": "关键证据及层级。", "target": "P02"},
    {"label": "反驳与让步", "text": "竞争性解释及边界。", "target": "discussion"},
    {"label": "结论", "text": "证据允许的结论。", "target": "conclusion"}
  ],
  "matrix": [
    {"claim": "主张环节", "supports": "证据实际支持什么", "limits": "尚未解决什么"}
  ],
  "strongest": {"title": "最强论证的名称", "text": "具体理由。"},
  "weakest": {"title": "最弱论证的名称", "text": "具体缺环。"}
}
```

链接目标必须真实存在。没有明确反驳段时，说明作者是否处理替代解释，不捏造原文没有的反驳。`matrix`可省略，其余核心总览字段保留。

## 执行

```text
python scripts/render_reader.py work/paper.json outputs/paper.html --report work/render-report.json
```

报告包括单元数、图数、页数和顺序清单；这不是内容准确性的证明。渲染器不联网下载图片，不删除输入，不处理翻译或判断的生成。分析仍由阅读论文的智能体完成。
