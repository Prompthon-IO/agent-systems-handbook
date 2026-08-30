# 第 5 课：Plan → Distribute → Discover

目标：形成可迭代的内容策略，生成渠道化 campaign 预览，再用来源证据复查 AEO 内容。真实 demo 排程另需已部署并核实的隔离 Social 后端能力；课程请求不授权生产发布。

## 课前与五分钟起步

运行共享安装器 `--lesson 5`，使用独立 workspace 和虚构内容。按 [Plan](../../content-strategy/README.md) 预览/保存四个主题的策略，再按 [Distribute](../../prompthon-social-campaign-manager/README.md) 生成两个帖子预览。预期 `canonical_social_objects_created: false`，没有创建真实 campaign、post 或 schedule。Windows 等缺少时区库的环境需安装 tzdata；可选 Node 测试拦截所有请求，不连接外部平台。

## 25 分钟练习

1. 0–8 分钟：讨论目标、受众、内容支柱、searchable/shareable 和主观评分依据；保存 revision 1，修改一个判断，使用同一 strategy id 与 expected-revision 1 保存 revision 2。
2. 8–16 分钟：把核心主题改写为两个渠道的语气，检查策略版本、时间、provider 和 plan hash。没有服务端 demo attestation 时止步 prepared 并标明“未排程”；不能转用旧 bridge-token/apply-plan 或真实生产渠道绕过。已核实的课程后端需要分别批准 DRAFT 和 SCHEDULE，再回读真实对象与模拟投递记录。
3. 16–25 分钟：按 [Discover](../../ai-search-visibility/README.md) 检查两个页面中的五个问题，对照[虚构事实 brief](../../content-strategy/examples/synthetic-workshop-brief.md) 修改副本，再用同一 audit id/revision 复查。brief 明确列出样例交付物，支持补写 build 回答；四项有依据的修改应解决四个问题。没有相关且已检查的来源时，保留缺少证据引用的问题。区分已修复、仍存在和仅因查询范围改变而消失的问题。

变化练习：修改一个渠道文案并观察计划 hash 变化，或删除一个目标问题并观察 scope_comparable=false。不得编造搜索量，结构改善不等于获得搜索排名或模型引用。

## 证据与重置

老师检查策略版本、仅计划而未排程的日历、campaign 预览、AEO 来源 hash/片段与复查状态。真实 demo 服务若已就绪，还需另检查 Host receipt、canonical post/schedule、模拟投递及课程 run。离线 mock 不能充当后端已部署的证据。

共享 reset 仅清除选定工作区课程记录，不删除已有 Social 业务对象、页面、预览文件或平台内容。保留失败证据，需要清理时使用所属 App 的另行授权流程。课程隔离、模拟 worker 和 receipt 回写能力仍由依赖事项 #221 跟踪。
