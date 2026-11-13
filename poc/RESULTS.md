# POC 实测验收报告

日期：2026-11-13。执行环境：Linux x86_64、Python 3.12.3、LiteLLM Proxy 1.109.1、Prisma Python 0.15.0、PostgreSQL 16.2（pgserver 0.1.4 提供）。

**最终完整集成验收：22 项通过，0 失败，0 错误，0 跳过。** 本轮总耗时约 98.2 秒，包含新建 PG、初始化表结构及代理重启；这不是请求性能基准。

执行命令：`make test`。使用随机端口和隔离测试数据库。没有使用真实公司 MaaS、GPU 或付费模型，也没有用 mock 替代 LiteLLM 或 PostgreSQL。

## 逐项结果

| 测试 | 结果 |
| --- | --- |
| test_real_postgres_and_hashed_key | 通过 |
| test_two_protocols[local-chat-self-hosted] | 通过 |
| test_two_protocols[maas-chat-MaaS] | 通过 |
| test_sdk_streaming[local-chat] | 通过 |
| test_sdk_streaming[maas-chat] | 通过 |
| test_native_anthropic_entry | 通过 |
| test_model_allowlist_and_filtered_catalog | 通过 |
| test_invalid_key_and_management_denied | 通过 |
| test_revocation | 通过 |
| test_expiry | 通过 |
| test_parallel_tool_roundtrip | 通过 |
| test_structured_output | 通过 |
| test_error_no_retry_no_fallback[[poc:429]-429] | 通过 |
| test_error_no_retry_no_fallback[[poc:500]-500] | 通过 |
| test_timeout | 通过 |
| test_rpm_limit | 通过 |
| test_concurrency_limit | 通过 |
| test_spend_persisted_without_prompt | 通过 |
| test_other_key_details_denied | 通过 |
| test_z_restart_preserves_key_and_data | 通过 |
| test_budget_after_spend_settlement | 通过 |
| test_ui_and_openapi_available | 通过 |

## 验证了什么

- 两种真实 HTTP 协议路径：统一聊天入口转换到模拟 Anthropic MaaS，兼容接口转发到模拟自部署上游；同时验证原生 Messages 入口。
- OpenAI SDK 能解析两种上游的流式事件、结束原因与 usage。
- 原生管理 API 创建用户和绑定用户的 Key；SQL 查询确认数据库保存的是 Key 哈希。
- 模型白名单、管理端点限制、不同用户 Key 信息隔离、过期和撤销生效。
- 工具 ID 与参数能够完成双工具回传；结构化结果通过独立 JSON Schema 校验。
- RPM 和并发限制生效，结束后释放并发名额；429 与 500 不自动重试或转入另一模型。
- 超时能够结束请求；示例用量与非零演示成本写入 PG，spend 记录不含测试正文或原始 Key。
- LiteLLM 代理重启后，数据库中的已有 Key 仍可调用。此项未重启 PG，也未执行备份恢复演练。
- 管理台 HTML 与 OpenAPI 文档可获取；未执行浏览器中的登录和点击回归。

## 两个实现要点

1. Key 必须明确绑定 `user_id`。无归属 Key 不能作为用户隔离方案。演示与测试先创建普通用户，再发 Key；project metadata 只是标签，不提供项目级授权。
2. 本版本在 Key 用量结算超预算后返回 `422`，错误类型为 `budget_exceeded`。测试先发生一笔超过极小预算的调用，再验证后续请求被拒绝，因此只能证明结算后拦截，不能证明严格零超支。

## 尚未验证的能力

真实 MaaS 认证和配额、真实模型工具质量、任意 JSON Schema、多模态、真实断流与取消、长上下文容量、80 人负载、共享项目预算、多副本一致性、SSO、生产迁移和 PG 备份恢复仍需独立验收。

该 POC 为原生开源组件组合的功能验证。PostgreSQL 临时实例和模拟上游均由运行器管理；生产需要受维护的数据库版本、正式凭证与恢复方案。完整原始日志和 JUnit 位于本地忽略目录，不随公开仓库发布。
