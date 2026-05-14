# ppt-helper

一个面向 AI agent 的 PPT 生成与重建 skill。它的目标不是只“出图”，而是帮助用户把素材整理成完整的 PPT 工作流：规划文案、生成或导入页面图、生成无字底图，并重建出可编辑的 `.pptx`。

这个仓库保持轻量：

- `SKILL.md` 是主入口，定义 agent 的行为规则。
- `references/` 存放只在特定阶段按需加载的提示模板。
- `scripts/` 存放稳定、可复用的脚本，用来做上传、OCR 预检和可编辑 PPT 重建。

## 这个项目解决什么问题

`ppt-helper` 适合下面几类任务：

- 根据文档、产品资料、方案说明、截图和参考图，帮用户写一套 PPT。
- 用户已经有页面图，只需要导入、补无字底图并重建可编辑 PPT。
- 用户已经有带字页图和无字底图，只需要做重建。
- 在不同机器、不同 Python 环境里，自动选择合适的 OCR 路径，而不是把运行时假设写死。

它的核心理念是：

- 文案和页面意图交给 AI。
- 文件落盘、OCR、重建、上传桥接交给脚本。
- 阶段状态写进项目目录，而不是只靠聊天上下文记忆。

## 默认工作流

默认是一次连续完成，而不是每个阶段都停下来等确认：

1. 规划整套 PPT 的结构和逐页文案。
2. 保存 `source/approved_plan.md`。
3. 生成或导入带文字页面图到 `ppt/`。
4. 生成或导入无字底图到 `ppt-clean/`。
5. 运行重建脚本，输出 `ppt-editable/*.pptx`。
6. 把关键信息写入 `MANIFEST.md`。

只有在下面这些情况才应该暂停：

- 输入素材不全。
- 依赖、权限、额度或外部服务不可用。
- 用户明确要求阶段式审查。
- 本地文件没有真正落盘或校验失败。

## 仓库结构

```text
ppt-helper/
  SKILL.md
  README.md
  references/
    prompt-pack.md
  scripts/
    ocr_preflight.py
    run_editable_ppt.py
    evolink_upload.py
    build_editable_ppt_vision.py
```

## 脚本说明

- `scripts/ocr_preflight.py`
  用来检查当前运行时到底能不能做 OCR。它会探测 Python、平台、CPU 特征、PaddleOCR / RapidOCR 的真实导入能力，并给出推荐 backend。

- `scripts/run_editable_ppt.py`
  是 Phase 3 的稳定入口。它会先做 preflight，再根据环境变量或命令行参数选择 OCR Python，最后调用真正的重建脚本。

- `scripts/build_editable_ppt_vision.py`
  负责把 `ppt/` 与 `ppt-clean/` 重建成可编辑 PPT，并缓存 OCR JSON。

- `scripts/evolink_upload.py`
  在远程图像模型必须依赖公网 URL 时，把本地图片上传到 Evolink Files，返回可临时复用的 `file_url`。

## OCR 与跨环境适配

这个项目不是把某一个 OCR 后端写死，而是按运行环境选择：

- 能正常导入 PaddleOCR，就优先用 `paddleocr`。
- PaddleOCR 不可用时，回退到 `rapidocr`。
- 两者都不可用时，使用 `json` 模式，读取预先生成好的 OCR 结果。

这也是为什么项目提供独立 OCR Python 入口。主 agent Python 不一定就是最适合跑 OCR 的 Python。

可选环境变量：

```text
COMMERCIAL_PPT_OCR_PYTHON
AI_PPT_OCR_PYTHON
PPT_OCR_PYTHON
OCR_RUNTIME_PYTHON
```

例如：

```bash
export COMMERCIAL_PPT_OCR_PYTHON=/absolute/path/to/ocr-runtime/bin/python
```

然后通过统一入口运行：

```bash
python scripts/run_editable_ppt.py --base /path/to/project --output demo_editable.pptx
```

先做运行前检查：

```bash
python scripts/ocr_preflight.py
python scripts/ocr_preflight.py --json --require-ready
```

## 兼容矩阵

| 环境 | 推荐 OCR | 说明 |
| --- | --- | --- |
| macOS 本地开发机 | `paddleocr`，不可用时回退 `rapidocr` | 适合内容生产与调试。 |
| Linux 服务器，CPU 支持 AVX，且 Paddle wheel 可用 | `paddleocr` | 质量优先的 CPU 路径。 |
| Linux 服务器，无 AVX 或 Paddle wheel 不兼容 | `rapidocr` | 更稳妥、更常见的服务器回退路径。 |
| Windows 本地或服务器 | `paddleocr`，不可用时回退 `rapidocr` | 建议把 OCR Python 与主运行时分开。 |
| 没有可用 OCR 运行时的任意环境 | `json` | 使用预先生成的 OCR JSON。 |

`run_editable_ppt.py` 会把当前运行时的判断写进 `MANIFEST.md` 的 `OCR Runtime` 区块，包括：

- 实际使用的 Python
- 请求的 backend
- 推荐的 backend
- 最终采用的 backend
- probe 结果
- blocker 信息

这样每一个输出目录都能解释自己“为什么这样跑”。

## 输出约定

一次完整执行通常会得到这样的目录：

```text
<project>/
  source/
    approved_plan.md
    imported_assets.md
  ppt/
  ppt-clean/
  ppt-editable/
  prompts/
  remote_assets.json
  evolink_uploads.json
  MANIFEST.md
```

`MANIFEST.md` 应至少记录：

- 项目目录绝对路径
- `ppt/`、`ppt-clean/`、`ppt-editable/` 绝对路径
- 图像来源与远程 URL 映射
- 最终 `.pptx` 路径
- OCR Runtime 信息
- 已知限制和异常页

## 运行时注意事项

- 不要把 `ppt-helper` 当成只会出图的 prompt，它本质上是一个“写稿 + 文件落盘 + 重建”的 workflow skill。
- 不要在没有真实工具输出和本地文件的情况下声称“已生成”“已执行”“已验证”。
- 不要在 Phase 2 和 Phase 3 之间重复上传已经有可用 `file_url` 的图片。
- 不要把机器私有路径、单一操作系统假设、某个团队的部署方式写进开源默认逻辑。

## License

MIT，见 [LICENSE](LICENSE)。
