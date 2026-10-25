# Wenmai 纹脉 · 可解释纹样共创原型

一个可在 Windows 本地运行的 Python + Web 代码包。从图片解析几何结构，手动修改结构，检索有来源的馆藏元数据，进行双模式共创，导出 PNG、SVG、来源卡与变化记录。**不需要 API 密钥，也不需要 GPU。**

这是技术方案的第一阶段可运行实现，不是已经完成训练和试点的最终文化大模型。真实图片的年代、地域、寓意需要资料与人工确认。

## Windows 快速运行

1. 从本仓库 `releases/Wenmai_Prototype_v0.1.0.zip` 下载代码包，解压到例如 `D:\Wenmai`（文件名与目录均为英文）。不要在压缩包内直接运行。
2. 安装 **64位 Python 3.11 或 3.12**，保留 Python Launcher。首次安装依赖需要联网。
3. 双击 `start.bat`。脚本在项目内建立 `.venv`，安装固定版本依赖，再启动本地服务。
4. 浏览器打开 `http://127.0.0.1:8000`。点击“使用原创几何示例”，选择排布方式，再点击生成；底部可下载完整设计包。
5. 按 `Ctrl+C` 停止服务。运行产物保存在项目内 `runtime`，默认不会上传到 GitHub。

如需手动运行，在项目目录打开 PowerShell：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn wenmai.app:app --host 127.0.0.1 --port 8000
```

若要把 pip 缓存也放到 D 盘，可先执行 `$env:PIP_CACHE_DIR='D:\DevCache\pip'`。项目依赖和输出已保存在项目所在盘。首次安装不是离线安装；完成后正常使用内置资料与示例不需要联网。

## 已实现功能

- PNG/JPEG/WebP 上传、大小与像素限制、透明背景处理、自适应二值化。
- 四邻域连通域、包围框、前景比例、水平与垂直镜像 IoU；输出可查看的几何结构 JSON。
- 在画布上拖出矩形添加连接块或删除区域；新建资产版本并保留父资产与操作历史。
- 传统表达模式锁定原单元；当代共创支持重复排布、镜像并置、换色和一次局部闭运算。
- 区分未知、仅展示、允许衍生三种素材状态；后端强制阻断未确认允许衍生的生成和编辑。
- 根据用户指定的实际宽度检查安全区、候选细线与连通性；报告检查假设，不把数字检查当作实际工艺验证。
- 检索28条真实机构开放元数据，保留原始 JSON、固定源提交、来源链接、许可与 SHA-256；可将资料作为参考加入来源卡。
- 导出 PNG、SVG、JSON 来源卡、变化说明和 ZIP 设计包；SQLite 保存生成审计记录。
- 本地运行前端无需 Node.js 构建。提供 Dockerfile、启动脚本、数据刷新工具和自动化测试。

## 联网资料与许可

内置资料来自 [Cooper Hewitt, Smithsonian Design Museum 开放馆藏仓库](https://github.com/cooperhewitt/collection)。2026-10-25 读取固定提交，系统抽取240条分布样本，按纸艺、花卉、纹饰、纺织与中国等关键词筛选，得到28条记录；240次抓取均成功。不是穷尽检索，不代表蔚县剪纸专用数据集。

- [官方使用说明](https://github.com/cooperhewitt/collection/blob/master/README.md)说明元数据采用 CC0。
- **图片不在该元数据许可范围内**：本包不包含馆藏图片，不把图像链接当成可训练许可。
- 数据源原始文件见 `data/raw`；规范化子集见 `data/catalog.json`；抓取统计见 `data/fetch_report.json`；原始许可见 `data/COOPER_HEWITT_CC0.md`。
- 部分记录没有年代、地域或描述，界面保留缺失状态。原始地域数字是 WOE 标识，不能直接当作地域名称。
- 示例是本项目原创程序几何，不是馆藏、传统非遗原作或训练样本。
- [Met 官方开放数据说明](https://github.com/metmuseum/openaccess)可作下一阶段来源，但其馆藏 API、UNESCO 和其他博物馆官网在本次云环境内返回代理403，因此没有声称下载这些站点的数据。

联网刷新内置固定版本元数据：

```powershell
.\.venv\Scripts\python.exe scripts\refresh_data.py
```

扩展工具 `scripts/import_met.py` 使用官方 Met API，只保留 `isPublicDomain=true` 记录，可选下载图片。该工具需要对应域名可达；本环境已确认 API 访问受阻，**未验证在线导入成功**。新增资料保存在 `runtime/met_import`，须人工核对后接入数据集，不会自动混入内置目录。

```powershell
.\.venv\Scripts\python.exe scripts\import_met.py --query "Chinese paper cut" --limit 10
```

## 测试与验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖完整生成与下载、模式锁定、权利闸门、结构编辑版本记录、无效文件、超限上传、透明背景、引用绑定、元数据校验、非法参数和工艺检查。独立新建 Python 3.12 虚拟环境安装后，15项测试全部通过；另以 Chromium 实测桌面与390像素移动端，完成“示例→重复共创→检查→下载设计ZIP”流程。Windows 批处理与 Docker 启动尚未在对应系统实际执行，不冒充已验证。

## 目录

```text
wenmai/                  Python API、几何引擎、静态前端
scripts/                 数据刷新、可选Met导入、打包工具
tests/                  自动化测试
data/                   28条开放元数据、原始记录、许可
docs/                   技术方案、实现说明、验证记录
releases/               可直接下载的源码运行包
start.bat               Windows 启动入口
start.sh                Linux/macOS 启动入口
requirements-lock.txt   完整固定版本依赖
runtime/                本地运行输出（不提交）
```

## 当前能力边界

尚未实现训练后的母题分类、文化语义知识图谱推理、向量检索、扩散/LoRA生成、自动寓意判断、语义错误修复或实际打样。当前结构图是连通域几何表示，未推断母题层级和语义关系。局部修复是一轮可复现形态学处理，不是训练得到的智能修复模型。

SVG采用二值逐行路径矢量化，适合检查与二次编辑，未进行轮廓简化及刀路优化。透明度、连通性与工艺限制均为简化检查；输出始终标注待人工审核。用户勾选允许衍生不等于系统已独立核实权利。

默认服务仅监听本机。这个原型没有多用户鉴权、配额和外网运维能力，不能直接作为公开生产服务部署；运行目录保存上传衍生数据，需要删除时停止服务后清理 `runtime`。

下一阶段须先取得合法的蔚县剪纸图像和专家标注，建立按原作分组的数据划分，再训练和评估母题识别；之后接入许可允许的生成模型，并与当前确定性基线进行对照实验。不要把本版本演示当作最终方案指标已达成。

源码许可与第三方数据许可分开管理，见 `LICENSE` 和 `data` 内的第三方许可。机构资料引用不代表相关机构对本项目背书。
