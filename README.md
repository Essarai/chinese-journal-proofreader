# Chinese Journal Proofreader

面向中文学术期刊 Word 稿件的 Codex/Agent Skill。默认保留正文，在副本中添加原生 Word 批注，并对批注范围、正文不变性和 DOCX 包结构进行验证。

## 主要能力

- 完整检查题名、摘要、正文、表格、注释、引文、参考文献与英文内容。
- 将“明确错误”“编辑建议”“请作者确认”分开表述。
- 以最小必要文本范围添加 Word 原生批注，不覆盖源文件。
- 支持多稿件隔离审校；每篇仍执行完整审校和交付验证。
- 附带精确批注与结构验证脚本。

## 安装

将本仓库克隆到 Codex 的 skills 目录：

```bash
git clone https://github.com/Essarai/chinese-journal-proofreader.git \
  ~/.codex/skills/chinese-journal-proofreader
```

脚本运行依赖 Python 3.10+ 与 `lxml`：

```bash
python -m pip install -r requirements.txt
```

也可以使用支持 Agent Skills 规范的其他客户端加载本仓库。

## 配套 Skills 与运行能力

本 Skill 会按任务需要调用以下配套能力：

- [`RightCapitalHQ/chinese-style-guide`](https://github.com/RightCapitalHQ/chinese-style-guide)：中文排版与中英文混排规范。
- [`Yuan1z0825/nature-skills`](https://github.com/Yuan1z0825/nature-skills)：其中的 `nature-polishing` 与 `nature-ref-verifier` 用于学术英语和参考文献核验。
- Codex `documents`：DOCX 读取、渲染和交付验证。
- Codex `computer-use`：仅在需要 Microsoft Word 界面终检时使用。

## 目录

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── batch-processing.md
│   ├── docx-comment-workflow.md
│   └── review-checklist.md
└── scripts/
    ├── add_precise_comments.py
    └── verify_commented_docx.py
```

## 脚本示例

使用 JSON issue ledger 添加精确批注：

```bash
python scripts/add_precise_comments.py source.docx issues.json \
  --out reviewed.docx --author "Codex审校"
```

验证批注版没有改动可见正文，并检查批注结构与精确锚点：

```bash
python scripts/verify_commented_docx.py source.docx reviewed.docx \
  --expected-new-comments 3 --ledger issues.json
```

`issues.json` 示例：

```json
[
  {
    "anchor": "用于定位段落的唯一文本",
    "target": "最小问题文本",
    "comment": "【文字】说明问题并给出可执行修改。",
    "occurrence": 1
  }
]
```

## 边界

- 默认只添加批注，不静默改写正文。
- 期刊现行投稿规范优先于通用语言规则。
- 法规、政策、标准、期刊要求与文献元数据需要查询当前可靠来源。
- 不应将未公开稿件上传到公共服务来完成检查或转换。

## License

[MIT](LICENSE)
