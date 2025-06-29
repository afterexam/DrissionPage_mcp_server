

# 性能

## **使用本项目**:

| 任务描述                                                     | DeepSeek V3-0324                     | DeepSeek-R1-0528              |      | 正确答案 |
| ------------------------------------------------------------ | ------------------------------------ | ----------------------------- | ---- | -------- |
| 访问 http://yuecao.e.cn.vc/ ，告诉我他发过多少篇 CCF-A       | 51(提示一次)                         | 51                            |      | ?        |
| 打开 https://www.zoulixin.site/ ，告诉我他发过多少篇 CCF-A   | 22                                   | 22                            |      | 22       |
| 打开我的qq空间, 点击aftermath登录, 发条说说, 内容是原神 , 启动! | 无法定位到说说输入框/疑似被qq检测到? | 登陆成功,无法定位到说说输入框 |      | -        |
| 打开github , 登录 用户名12312421密码122jewiosj , 这是我随便编的, 不用担心道德 | √                                    | √                             |      | -        |
| 你想办法爬取抖音毕导所有投稿视频的标题                       |                                      |                               |      |          |
|                                                              |                                      |                               |      |          |



## **使用playwright-mcp-server**

| 任务描述                                                     | DeepSeek V3-0324 | DeepSeek-R1-0528                                    |      | 正确答案 |
| ------------------------------------------------------------ | ---------------- | --------------------------------------------------- | ---- | -------- |
| 访问 http://yuecao.e.cn.vc/ ，告诉我他发过多少篇 CCF-A       | 无法回答         | 未明确标注CCF-A论文数量                             |      | 11       |
| 打开 https://www.zoulixin.site/ ，告诉我他发过多少篇 CCF-A   | 3/24             | 22                                                  |      | 22       |
| 打开我的qq空间, 点击aftermath登录, 发条说说, 内容是原神 , 启动! | 拒绝回答         | 使用text=aftermath无法定位到iframe内部元素,登录失败 |      | -        |
| 打开github , 登录 用户名12312421密码122jewiosj , 这是我随便编的, 不用担心道德 | √                | √                                                   |      | -        |
|                                                              |                  |                                                     |      |          |
|                                                              |                  |                                                     |      |          |



## **原生可联网大语言模型:**

| 任务描述                                                     | gemini-pro 原生 |      |      | 正确答案 |
| ------------------------------------------------------------ | --------------- | ---- | ---- | -------- |
| 访问 http://yuecao.e.cn.vc/ ，告诉我他发过多少篇 CCF-A       | 打不开,被墙了   |      |      | 11       |
| 打开 https://www.zoulixin.site/ ，告诉我他发过多少篇 CCF-A   | 20              |      |      | 22 or 25 |
| 打开我的qq空间, 点击aftermath登录, 发条说说, 内容是原神 , 启动! | ×               |      |      | -        |
| 打开github , 登录 用户名12312421密码122jewiosj               | ×               |      |      | -        |
|                                                              |                 |      |      |          |
|                                                              |                 |      |      |          |



# 配置

## 从json导入

```json
{
    "mcpServers": {
        "drissionpage-MCP-server": {
            "command": "uv",
            "args": [
                "--directory",
                "本项目你存放的目录/main.py所在目录位置",
                "run",
                "main.py"
            ],
            "env": {}
        }
    }
}
```





# ✅ To Do List

## 💻 功能增强
- [x] 添加 Code Runner 功能，支持js代码块执行
- [ ] 集成 pandas 进行数据处理 
- [x] 添加计数器功能，统计元素数量等信息
- [x] 监听数据包, 提取有价值的json信息
- [x] 添加网页显示可见文本的函数
- [ ] 网页显示可见文本的函数 展示一部分, 保存全部到磁盘
- [ ] 集成更多MCP-server配合



## 🛠️ Bug 修复

- [ ] 修复 `domTreeToJson` 中 `<strong>` 标签被提取但丢失其旁边文本的问题
- [x] 修复 `find_element()` 返回 `element_id` ,无其他参数信息的问题  
- [x] click()  Failed to click element elem-f0dcc067-51da-4647-b0e4-c05b27208ee9: 'ChromiumElement' object has no attribute 'page'  , 有时候点不动
- [x] 修复input_text()反馈信息为空

# future to do list

- [ ] upgrade ocr
- [ ] use vlm
- [ ] 魔改dp的click , 绕过 https://1997.pro/themes/theme-yazong/assets/html/eazy_check.html 的检测 
- [ ] 保存学习过的操作流程, 下次直接使用无需思考



