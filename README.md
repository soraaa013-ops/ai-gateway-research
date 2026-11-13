# 企业内部 AI 网关调研

面向使用内部 MaaS 和自部署模型的研发团队，研究如何提供通用、可治理、可调试的大模型 API 服务。

**建议采用统一管理、多协议入口和原生能力保留的架构。先验证现成网关，再补齐内部认证、模型目录与调试体验。**

研究日期：2026-11-13。适用规模：最多约 70–80 名内部用户。仓库现包含调研、设计建议及可运行的 LiteLLM 与临时 PostgreSQL POC。候选能力依据官方文档；具体版本与真实上游组合仍需 POC 验证。

## 运行 POC

[POC 使用说明](poc/README.md)：真实 LiteLLM Proxy + 自动创建的临时 PostgreSQL + 两种模拟模型协议。无需已有 PG、Docker 或 GPU。

```bash
make install
make poc
# 另一终端运行完整隔离验收
make test
```

具体环境要求、凭证位置、模拟边界及[实测结果](poc/RESULTS.md)见 POC 文档。

## 阅读路径

| 文档 | 回答的问题 |
| --- | --- |
| [可实施功能清单](docs/09-feature-checklist.md) | 按模块拆分功能、验收、依赖及开源实现方式 |
| [小团队开源方案](docs/10-open-source-plan.md) | 如何用 LiteLLM 等直接交付服务，减少自研 |
| [研究结论](docs/01-findings.md) | 产品边界是什么，为什么不能只统一请求格式 |
| [功能需求](docs/02-requirements.md) | 首期必须提供什么，如何验收 |
| [协议兼容](docs/03-compatibility.md) | 内部 MaaS 与自部署模型如何适配 |
| [架构与治理](docs/04-architecture.md) | 路由、身份、预算、观测和数据如何组织 |
| [候选产品](docs/05-products.md) | 现有产品怎么选，哪些结论仍需验证 |
| [POC 验收](docs/06-poc.md) | 用什么实验做出最终决策 |
| [实施路线](docs/07-roadmap.md) | 如何分阶段交付，谁负责什么 |
| [来源与证据](docs/08-sources.md) | 官方出处、证据范围与维护方法 |

配套材料：[开发功能清单 CSV](templates/feature-backlog.csv)、[上游盘点表](templates/upstream-inventory.csv)、[兼容性矩阵](templates/compatibility-matrix.csv)、[POC 记录表](templates/poc-results.csv)、[决策记录](templates/decision-record.md)、[模型目录示例](examples/model-catalog.json)。

## 场景假设

- 上游主要为内部 MaaS 和自部署推理服务，不假定可以直接访问外部模型厂商。
- 下游主要为开发者 SDK、业务应用和测试程序；开发工具协议按实际使用情况纳入。
- 尽可能复用企业身份、日志、密钥和基础设施；部署平台尚未限定。
- 示例全部为虚构数据。真实上游清单、地址、认证细节和测试正文应留在私有系统。

## 初步决策

优先直接验证 LiteLLM 开源自托管，复用管理台、虚拟 Key 和模型路由；管理员辅助流程可满足首期。只针对真实缺口补 MaaS 适配或薄门户。New API 为管理体验导向的备选；已有网关体系时评估 Higress。先试一个主候选，再按失败原因选择一个备选，不从零自研整个网关。

首期成功标准是开发者能拿到内部 Key、找到可用模型、完成真实工具调用，并凭请求 ID 解释失败原因。模型数量和厂商性能宣传不作为主要验收标准。
