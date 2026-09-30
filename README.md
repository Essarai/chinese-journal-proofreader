# Chinese Journal Proofreader

面向中文学术期刊 Word 稿件的审校 Skill。逐句检查语言，并核对论证、图表、引文、注释、参考文献及稿件中实际存在的英文内容。支持单篇审校和多稿件隔离处理。

## 交付什么

默认生成独立、可继续编辑的 DOCX 副本。确定的错误直接改在正文，保留 Word 原生批注解释原文、改法和原因；原意或依据不明的地方保留原文，批注要求作者处理。

| 字体颜色 | 处理状态 | 用法 |
| --- | --- | --- |
| 蓝色 | 已修改 | 标出直接落实的文字修改；纯删除在邻近位置作最小定位标记 |
| 红色 | 需作者修改 | 标出作者需决定措辞、施事、逻辑或论证强度的原文 |
| 橙色 | 待核实 | 标出卷次、数量、史实、引文、版本、页码等尚需查证的原文 |

批注另写明问题类型和具体处理建议。颜色表示处理状态，不表示错误类别。源文件不会被覆盖。若明确要求仅批注或 Word 修订记录，按该要求输出。

## 审校范围

- 逐句检查成分残缺、句式杂糅、施事切换、搭配、并列层级、比较对象、指代、关联词和否定范围；对长句逐分句核对，不把合理省略或个人润色偏好判为错误。
- 对照摘要、正文、表格、图注和脚注中的数字、术语、引文与结论。证据不足时提出可回答的作者问题；古籍异文不机械统一。
- 有英文题名、摘要或关键词时检查与中文的对象、年代、数字和结论是否一致；没有则跳过。
- 在内部台账记录原文范围、修改、处理状态、颜色、批注锚点和理由，最后核对 DOCX 结构及渲染页面。

## 安装与使用

```bash
git clone https://github.com/Essarai/chinese-journal-proofreader.git \
  ~/.codex/skills/chinese-journal-proofreader
```

示例请求：

> 使用 chinese-journal-proofreader 审校这份 Word 期刊稿件。请直接修改确定的语法和文字问题，按已修改、需作者修改、待核实三种状态分色，并保留原生批注说明。

运行时需要可读写和渲染 DOCX 的文档工具。随仓库附带的精确批注及仅批注模式校验脚本依赖 Python 3.10+ 和 `lxml`：

```bash
python -m pip install -r requirements.txt
```

`scripts/add_precise_comments.py` 负责插入原生批注，`scripts/verify_commented_docx.py` **仅适用于正文未改的仅批注模式**。默认直接改稿须使用具备 DOCX 编辑能力的工具，并按 `references/word-edit-output.md` 对照修改台账验证；上述两个脚本不能单独完成正文修改。

## 文件与配套能力

- `SKILL.md`：审校模式、单篇与批量流程。
- `references/word-edit-output.md`：三种状态颜色、批注格式及交付验收。
- `references/review-checklist.md`：逐句语言、结构、图表与书目检查。
- `references/full-review-orchestration.md`、`references/batch-processing.md`：全面审校与多稿件流程。
- `references/docx-comment-workflow.md`、`scripts/`：精确批注与仅批注模式校验。

可按任务搭配 [`chinese-style-guide`](https://github.com/RightCapitalHQ/chinese-style-guide) 处理中文排版，搭配 [`nature-skills`](https://github.com/Yuan1z0825/nature-skills) 核验参考文献或处理学术英语。这些是独立配套 Skill；本仓库不包含其代码。DOCX 页面和 Word 批注界面需分别检查，结构检查不能代替界面确认。

## 许可

[MIT](LICENSE)
