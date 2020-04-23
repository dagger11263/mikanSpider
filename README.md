# mikanSpider

一个python多线程爬虫,爬取了[蜜柑计划](https://mikanani.me)主页动画信息

## 实现功能

* 下载主页所有动画条目背景图片及种子,条目信息存储于sqlite3
* 爬虫日志,查询硬盘占用,清理老旧文件,重试超时任务
* 脚本自动部署,启用定时任务


## 程序效率

程序启用了128线程,若网络状况良好,  
首次运行时下载100+图片,3000+种子,  
耗时约为20秒,占用存储空间约为100M.

## 部署安装

### 运行环境

__本程序需要 python3.7 及以上版本__  
__本程序在 Manjaro 19.0.0, Ubuntu Server 18.04 LTS 测试部署成功__


### 自动部署

```bash
curl https://raw.githubusercontent.com/dagger11263/mikanspider/master/mikan.sh | sudo -H bash
```

### 手动运行任务

程序会在每天凌晨3点运行一次,若需手动运行任务

```bash
cd /srv/mikanSpider
source venv/bin/activate
python main.py
deactivate
```
