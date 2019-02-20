# toolkits to operate LIMS system

## login
- username 转成大写
- password 每个字符转成十六进制的ascii码，用0补齐4位，再拼到一起，转成大写
- 使用username和password获取用户信息，得到dept和role
- 最后使用username, password, dept, role进行登录验证，保留session

---

## 1 project
- 查看项目信息

## 2 sample
- 获取样本信息
- 获取sample_list(暂时没啥用)


## 3 report
- 上传报告
- 首次上传需指定SOP，样本数和数据量（样本数和数据量默认自动从qcstat.xls中读取）

## 4 check
- doublecheck报告
- 提交或退回

## 5 release
- 释放数据
- 查看释放历史
