# 来源与证据范围

核对日期：2026-11-13。采用官方文档与仓库。滚动文档用于发现能力，实际兼容性以固定版本 POC 为准。

| 来源 | 支持的事实范围 |
| --- | --- |
| [LiteLLM](https://docs.litellm.ai/docs/) | 统一接口、代理、Key 与成本 |
| [端点目录](https://docs.litellm.ai/docs/supported_endpoints) | 官方列出的协议类型 |
| [虚拟 Key](https://docs.litellm.ai/docs/proxy/virtual_keys) | 模型访问与用量治理 |
| [透传](https://docs.litellm.ai/docs/proxy/pass_through) | 透传及路由控制参考 |
| [Higress](https://higress.io/en/ai-gateway) | 转换、限流、观测与插件 |
| [多模型指南](https://higress.ai/en/docs/ai/scene-guide/multi-proxy/) | 多模型及 Docker 部署 |
| [New API](https://docs.newapi.pro/en/docs/guide/wiki/basic-concepts/features-introduction) | 渠道、权限、控制台和成本 |
| [Bifrost](https://github.com/maximhq/bifrost) | 接入、插件和治理方向 |
| [Portkey](https://portkey.ai/docs/product/ai-gateway) | 路由、预算和观测 |
| [Portkey 方案](https://portkey.ai/docs/product/product-feature-comparison) | 版本与部署方案差异 |
| [Kong](https://developer.konghq.com/ai-gateway/) | AI 接入与治理 |
| [Cloudflare](https://developers.cloudflare.com/ai-gateway/) | 托管观测和路由 |
| [Anthropic](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk) | 兼容层能力限制 |
| [Google](https://ai.google.dev/gemini-api/docs/partner-integration) | 原生与兼容能力不等价 |
| [vLLM 服务](https://docs.vllm.ai/en/latest/serving/online_serving/) | 自部署服务入口 |
| [vLLM 指标](https://docs.vllm.ai/en/latest/usage/metrics/) | 运行与排队指标 |
| [SGLang](https://docs.sglang.io/docs/basic_usage/openai_api_completions) | 自部署兼容接口 |

文档确认不代表实测；实测确认必须有固定版本、输入、预期与证据；设计建议包括架构、优先级与权重；证据不足记待验证。

当前没有实测排名、实际成本或内部系统细节。更新时记录核对日期与来源。公开证据使用合成数据，真实追踪和账单存于私有系统。

## 小团队方案补充来源

- [LiteLLM 快速开始](https://docs.litellm.ai/docs/proxy/docker_quick_start)：网关、PostgreSQL 与基础使用路径。
- [LiteLLM 管理台](https://docs.litellm.ai/docs/proxy/ui)：模型、Key 和用量管理入口。
- [兼容上游](https://docs.litellm.ai/docs/providers/openai_compatible)：自定义兼容服务接入。
- [企业功能](https://docs.litellm.ai/docs/enterprise)与[许可证](https://github.com/BerriAI/litellm/blob/main/LICENSE)：企业能力和目录授权边界。
- [New API 官方仓库](https://github.com/QuantumNous/new-api)：备选网关能力方向。

本轮用户规模来自需求约束；部署、试验并发档位与复用范围是设计建议，非已测容量。
