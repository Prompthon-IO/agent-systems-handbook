# 第 4 课：Structure → Operate → Analyze

目标：把乱表整理成可用数据，操作有身份和审计记录的业务对象，再用只读分析解释数据。三种技能不混为“修改表格”。

## 课前准备与五分钟起步

运行共享安装器 `--lesson 4`，每位学员使用独立 demo workspace；准备 Python 3.10+，XLSX 另装 Structure 指定的 openpyxl。数据全部虚构，不连接真实客户 CRM，也不发送邮件。按 [Structure README](../../business-data-structuring/README.md) 预览 CSV，检查 schema、日期格式、CAD 与美元符号对应关系，再使用实际返回的计划 hash 写到新目录。

## 25 分钟练习

1. 0–8 分钟：确认一行代表一笔虚构商机，批准精确去重后观察 6 行变成 5 行、7 列，姓名/日期空值保留；生成 XLSX 并核对两种格式结果。
2. 8–17 分钟：按 [Operate](../../crm-operations/README.md) 依次预览并应用 contact、deal、activity、task 四个请求。读取 id、revision、audit。试一次缺少额外批准的 close-deal，确认没有偷偷改变阶段，再明确批准虚构案例并回读。
3. 17–25 分钟：按 [Analyze](../../business-data-analysis/README.md) 只读分析 clean.json，逐行核对已关闭商机胜率 0.5、开放 pipeline CAD 4150；说明分母、空值与数据粒度，不推断因果。

变化练习：保留重复行比较汇总，或在副本中引入第二种货币并分币种报告；修改跟进日期，比较审计前后，不把任务当成真实消息发送。

## 教师检查与重置

检查原文件 hash 未变、清理计划/结果、CRM 的原子审计和分析报告的来源。默认远端只保存数据集元信息；上传清理后的虚构行需要明确选择 share-rows。课程 API/Neon 未部署时使用 local 并标明状态，禁止让学生直接连数据库。

共享 reset 先预览、再按 workspace 确认，会清除此工作区各课的课程记录，不删除原始文件或报告。重做时换新 workspace/目录。遇到解析错误、重复身份、并发更新或范围不匹配时先解决，不能静默丢行、覆盖文件、删除联系人或关闭商机。
