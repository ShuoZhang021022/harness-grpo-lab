# 利用 GRPO 学习 LLM Agent 的 Harness

[English](README.md) | [简体中文](README.zh-CN.md)

本项目研究：能否通过 GRPO 与 LoRA，提高主 agent 选择和生成 Python 工具的能力。参数固定的外部解题模型使用这些工具编写并执行 Python 解题程序；另一个参数固定的外部模型检查新工具的功能相似性。训练只更新主 agent。

仓库已实现工具库、轨迹控制、GRPO 核心、数据集、统计与绘图。项目提示词均为英文，并要求自然语言输出使用英文，同时保留规定的答案格式与程序接口。真实模型适配器和隔离执行后端尚未接入。模型配置现已选择自建部署的 Qwen3-8B 作为可训练主 agent，并使用 Qwen3-32B 作为固定的解题模型、相似性检查模型和离线参考答案审核模型。尚未下载或加载模型权重，也没有进行真实 LLM 训练或评估。数值测试样例和测试绘图不代表实验结果。

## 已确认的研究方案

主 agent 仅看到问题描述，以及初始工具的文本功能描述和接口。它在执行前通过自回归生成配置工具，不接收执行反馈，也不进行后续重新调度。实施 agent 是不能调用 LLM 的 Python 工具。初始工具库固定为 50 个。新工具仅在当前轨迹内可用，结束后删除执行副本；生成 token、源代码和检查理由保留在训练及审计记录中。LoRA 更新覆盖主 agent 生成的全部 token，包括工具选择、功能描述和新工具代码。外部解题模型、相似性检查模型和执行环境不参与梯度计算。每批 100 道题，每题 8 条独立轨迹。完成全部 800 条轨迹后，进行一次完整梯度更新；下一批使用更新后的权重。每个训练系统遍历训练集一次，共 30 批、30 次更新、24,000 条轨迹。目标函数采用原始的、按序列长度平均的 clipped GRPO loss。同题 8 条轨迹的奖励减去组均值，再除以组标准差。clip 参数为 0.2，KL 系数为 0。普通奖励为正确性奖励（成功 +1、失败 -1）减去每个交付工具 0.01 的成本。相似性拒绝立即终止轨迹，最终奖励严格为 -1，并覆盖工具成本。因此，相似性拒绝的奖励可能高于扣除工具成本后的普通失败轨迹。每个新工具都与全部 50 个初始工具，以及当前轨迹已接受的新工具比较。如果某一个已有工具能够实质替代其核心功能，则拒绝。检查针对功能重复，不保证工具能够跨题复用，也不排除单题专用解法。解题模型提示词要求实质使用所有收到的工具。三个领域分别有 1,000 道训练题和 100 道测试题。四个系统使用相同测试集，每题进行 8 次独立尝试，合计 9,600 条测试轨迹。四个系统分别是：解题模型使用全部 50 个固定工具；未训练主 agent 选择并生成工具；独立训练的仅选择工具主 agent；独立训练的选择并生成工具主 agent。两个训练系统从相同初始权重出发，各使用 24,000 条训练轨迹。训练题只打乱一次，不增加额外奖励、正则化或自动失败重试。

## 当前实现中的具体选择

以下内容描述已有实现，包括此前实现审计中披露的选择。列在这里不意味着每项细节都已单独得到确认。英文转换和本次双语文档整理不改变这些行为。初始 50 个工具包括数学工具 18 个、代码工具 17 个、生活场景工具 15 个。目录包含接口示例。工具还禁止联网和执行作为输入提供的 Python 源代码。主 agent 使用 JSONL 输出 `select`、`create` 和 `finish` 动作。新工具可以是单个 Python 文件，也可以是显式声明入口函数的多文件程序包；入口接收一个 `arguments` 对象。一个程序包计为一个工具。通过检查的新工具自动加入交付集合；同一工具重复选择只计一次。目前允许不选择任何工具。生成代码在相似性检查之前进行有效性验证，因此非法动作或代码可能在调用检查模型前终止轨迹。基础设施故障记录为未评分，并停止当前批次，不自动重试。不自动跳过失败组或零方差组，也不提前停止训练。工具调用覆盖率只用于诊断，没有针对违反解题提示词的额外惩罚。记录到调用也不能证明工具结果被实质使用。解题模型可自行实现哪些业务逻辑、是否可以修改工具，仍未确定。数值设置为 LoRA rank=32、alpha=64、dropout=0；学习率 1e-5；AdamW、weight decay=0；总体标准差（correction=0）和 epsilon=1e-8。不使用梯度裁剪、熵奖励或额外 loss。主模型已选为 Qwen3-8B；LoRA 目标层、确切模型版本和思考模式仍未确定。训练打乱种子为 20260920；评估种子列表目前也只包含 20260920。参考更新器每个 microbatch 处理一条轨迹，累计全部 800 条后进行一次优化器更新。它关闭 dropout，同时保留梯度，并只允许 LoRA 参数具有梯度。答案解析、任务生成规则、数据过滤和错误处理均属于已有实现选择，其研究影响仍需审核；语言转换不会解决这些问题。

## 自建部署的模型

所有大模型角色均使用可下载的 Qwen 权重，在用户提供的算力上运行。model_access 设置为 self_hosted_open_weights；所选方案不包含付费模型 API。

| 角色 | 模型 | 参数更新 |
|---|---|---|
| 主 agent | Qwen/Qwen3-8B | 仅更新 LoRA |
| 解题模型 | Qwen/Qwen3-32B | 固定 |
| 相似性检查模型 | Qwen/Qwen3-32B | 固定 |
| 离线参考答案审核模型 | Qwen/Qwen3-32B | 固定 |

官方 [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) 和 [Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B) 仓库均标注 Apache 2.0 许可证。自建部署无需支付按请求计费的模型 API 费用，但 GPU 硬件、托管和电力仍有成本。

只需要两套模型权重。三个固定模型角色可以共用一个自建 Qwen3-32B 服务，分别使用独立请求、提示词和上下文。离线审核模型不得将参考答案传给在线 agent。同一个模型承担多个角色，不能作为其判断或答案正确的独立证据；隐藏测试、精确答案比较和参考答案核验仍按原方案执行。

所选模型 ID 与离线审核模型设置已记录在 configs/experiment.json 中。确切版本、思考模式、采样设置、服务地址和 GPU 分配仍未确定，没有默认新增量化、解码模式或资源分配。Qwen3 要求 Transformers 4.51.0 或更高版本，训练依赖的最低版本已相应调整；正式依赖版本仍需固定。部署可以使用[自建 vLLM 服务](https://qwen.readthedocs.io/en/latest/deployment/vllm.html)，但真实模型和执行适配器尚未实现。

## 数据集

`data/public/train.jsonl` 和 `data/public/test.jsonl` 分别包含 3,000 和 300 道题。另提供 math、code、life 各领域的训练与测试 JSONL。所有问题描述均为英文。

`data/public/assets/<task_id>/buggy.py` 保存每道代码修复题的程序，共 1,100 个文件。

`data/private/labels/verifiers.jsonl` 保存答案、隐藏测试和参考实现，不得挂载到 agent 环境中。

`artifacts/dataset_audit/audit.json` 记录来源版本与哈希、过滤规则、划分、数量和核验状态。

数学训练集包含 883 道 AIME 题和 117 道 MATH Level 4/5 补充题；数学测试集包含 100 道 AIME 题。来源镜像为 [Pandores AIME](https://huggingface.co/datasets/Pandores/aime-1983-2025) 和 [EleutherAI MATH](https://huggingface.co/datasets/EleutherAI/hendrycks_math)。来源提供的参考答案尚未独立核验，不能将它们统一称为已核验的官方答案。构建时排除了 51 道需要内嵌图形的 AIME 题，以及 1 道参考答案含糊或无效的题。补充题取自原始 MATH 训练划分中的整数答案题，并进行精确与近重复文本过滤。

代码题要求修复四步整数计算程序中一个被变异的操作。每题包含完整行为规格、公开例子和隐藏输入测试。训练与测试使用不同的有序操作序列。参考程序已执行并与声明式 oracle 比对；每个错误程序至少失败一项隐藏测试。这些数据支持对合成组合程序修复的研究，不代表真实代码仓库的缺陷修复任务。

此前发现的一个限制仍然存在：100 道代码测试题中，有 11 道在 -500 到 500 的全部整数输入上，与某个训练程序输出相同。这是已检查范围内的功能重叠证据，不是对所有整数输入功能等价的证明。语言转换没有更换题目或调整划分。

生活场景题使用包含 16 个地点的固定地图和 8 步路线。训练与测试地图不同，但共享生成规则。通过确定性路线重放核验唯一的最终地点 ID。该领域表示信息完整的虚构地图导航，不代表一般现实生活问题。

## PowerShell 使用方法

仓库包含源代码、配置模板、提示词、公共题目、工具目录和审计记录。`data/private/` 中的私有答案与来源下载、模型权重、密钥、运行输出和临时文件均不纳入 Git。下方完整测试命令除了公共题目，还需要本地私有判题文件。新克隆的仓库不包含该文件，运行数据集测试前需要在本地恢复。以下五个代码测试模块无需私有数据即可运行：

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p test_tools.py -v
python -m unittest discover -s tests -p test_experiment.py -v
python -m unittest discover -s tests -p test_grpo.py -v
python -m unittest discover -s tests -p test_lora_update.py -v
python -m unittest discover -s tests -p test_plotting.py -v
```

从项目根目录运行，要求 Python 3.11 或更高版本。绘图需要 matplotlib 和 numpy，GRPO 数值测试需要 torch，数据构建需要 pyarrow。正式环境及依赖版本仍需结合模型部署固定。

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
python scripts/check_experiment.py --validate-data
```

就绪检查在必要配置缺失时返回退出码 2，不会启动训练。

```powershell
# 输入应为实际运行产生的轨迹 JSONL，输出目录必须尚不存在。
python scripts/summarize_trajectories.py --input outputs/run/batch_001/trajectories.jsonl --output outputs/report --samples-per-question 8
python scripts/plot_results.py --input outputs/test_fixed/trajectories.jsonl outputs/test_untrained/trajectories.jsonl outputs/test_selection/trajectories.jsonl outputs/test_full/trajectories.jsonl --output outputs/figures --samples-per-question 8 --comparison
```

统计文件 `question_success.csv/jsonl` 每行记录一个问题，包括 8 个成败标记、8 个奖励、0 至 8 的成功数、状态、批次和策略版本。`batch_summary.csv/jsonl` 记录批次成功率、成功数直方图和奖励方差为零的组数。成功率使用显式 `success` 字段，而不是奖励正负。即便一组全部失败，工具数量不同也可能产生非零奖励方差。

统计默认拒绝重复、缺失或未评分的样本。`--allow-incomplete` 只用于故障诊断，不完整组不报告成功率。图表包括带题号映射的逐轨迹成败热图、训练批次成功率曲线，以及四系统总体和分领域测试成功率柱状图。各训练批次题目不同，因此训练曲线只用于诊断。评估不利用隐藏答案从 8 次尝试中选最优结果，也不声称提供置信区间或统计显著性。

## 实现状态与待完成事项

轨迹和训练模块提供可注入适配器的执行核心。测试覆盖逐工具拒绝、清理、800 条轨迹全部采样后再更新，以及策略版本切换。GRPO 模块显式实现 token 级 loss。LoRA 更新器是单进程参考实现，并非已在 A100 上验证的分布式训练器。30 次更新能否改善表现，仍需要实际实验回答。

模型 ID 已写入 configs/experiment.json，但尚未下载或加载权重。必要设置仍保持显式 null：确切模型版本与思考模式；LoRA 目标层；A100 卡数、单卡显存和运行主机；自建服务地址与鉴权配置；采样设置与输出长度上限；解题器权限；隔离后端、超时和执行预算；数学参考答案独立核验。参考答案审核模型的配置只是对离线审核方案的记录，不代表审核已经完成。此前提供的硬件表述不能证明已有 8 张 A100。密钥不得提交到仓库。正式实验需要补齐这些设置和适配器后才能启动。

方法依据：[DeepSeekMath GRPO](https://arxiv.org/html/2402.03300v3) 和 [TRL GRPO 文档](https://huggingface.co/docs/trl/main/en/grpo_trainer)。本项目显式实现已确认的原始按序列平均 loss，不直接继承可能不同的库默认值。

验证范围见 [artifacts/VERIFICATION.md](artifacts/VERIFICATION.md)，历史英文转换审计见 [artifacts/english_conversion.json](artifacts/english_conversion.json)。中文 README 和后续文档修改是在该次审计后新增的。原始第三方来源快照与临时参考资料在本地按原样保留，不上传到仓库。
