# 候选产品比较

以下为官方文档能力方向与场景判断，不是测试排名。固定候选版本后核对许可证、授权与功能边界。

| 候选 | 官方能力方向 | 本场景价值 | 待验证 |
| --- | --- | --- | --- |
| [LiteLLM](https://docs.litellm.ai/docs/) | 多协议、虚拟 Key、成本、路由 | 协议适配和开发集成 | MaaS 自定义认证、严格参数、透传治理和组织权限 |
| [Higress](https://higress.io/en/ai-gateway) | 代理、转换、限流、插件和观测 | 复用网关及基础设施经验 | 真实协议、开发者门户、项目成本和插件维护 |
| [New API](https://docs.newapi.pro/en/docs/guide/wiki/basic-concepts/features-introduction) | 渠道、令牌模型权限、控制台和成本分配 | 快速发 Key 与管理渠道 | 企业身份、参数保真、授权和深度追踪 |
| [Bifrost](https://github.com/maximhq/bifrost) | 路由、虚拟 Key、预算和插件 | 另一种网关底座 | 内部认证、协议覆盖、企业功能边界 |
| [Portkey](https://portkey.ai/docs/product/ai-gateway) | 统一接口、路由、预算、缓存和观测 | 商业平台对照 | 私网接入、控制面依赖和部署授权 |
| [Kong](https://developer.konghq.com/ai-gateway/) | 接入、治理、计量和观测 | 已有 Kong 团队时优先 | 产品代际、控制面、授权和适配 |
| [Cloudflare](https://developers.cloudflare.com/ai-gateway/) | 托管观测、缓存和路由 | 允许相应网络路径时评估 | 私网服务连接和数据路径，默认非首选 |

## 短名单建议

面向最多约 70–80 名内部用户，先直接验证 LiteLLM 开源自托管，复用后台和基础功能。按真实缺口再选择一个备选：管理体验优先看 New API，已有网关运维体系优先看 Higress。无需默认同时部署两个候选。

开发功能映射、企业版边界和最小拓扑见[小团队开源方案](10-open-source-plan.md)。不因用户少忽略权限与备份，也不以人数直接推导并发或引入多集群。

## 决策方法

硬门槛：MaaS 认证可接入、必需协议通过、无权限绕过和密钥泄漏、严格模式不静默切换、请求可排障。失败不得靠总分抵消。

通过后按 0 至 5 分评分：兼容性 30%、调试体验 25%、身份与资源治理 20%、运维升级 15%、总成本 10%。权重在测试前确定；未验证项不填假分。

总成本包括运行资源、数据库和缓存、授权、适配开发、升级回归、日常运维与培训。自部署还有 GPU 和空闲资源成本。

逐项标记开源版提供、商业版提供、外部集成、自研、未确认。产品总体特性不等于开源版自带；Portkey 官方有方案区分。[方案比较](https://portkey.ai/docs/product/product-feature-comparison)

固定 release 或镜像 digest 后测试，核对官方发布说明与安全公告。滚动文档不代表旧版能力；厂商压测数据不能直接用于内部容量规划。
