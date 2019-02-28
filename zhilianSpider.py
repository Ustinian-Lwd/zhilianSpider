#!C:/SoftWare/Virtualenv/python3
# @FileName: 01-智联招聘
# @Author: 李易阳
# @Time: 2019/2/28
# @Soft: PyCharm


# 导包
import urllib.request
import urllib.parse
from lxml import etree
import time
from selenium import webdriver
import json
import pymysql
import os


# 存储智联招聘工作信息
# 分析
# 一级页面
# 职位(job)  工资(salary)  经验experience
# 学历education  福利welfare   公司company  people人数
# 二级页面
# 职位信息jobInfo  公司地址address、公司概况companyInfo
class JobItem(object):
    def __init__(self, job="", salary="", experience="", education="", welfare="", company="", people="", jobInfo="", address="", companyInfo=""):
        self.job = job
        self.salary = salary
        self.experience = experience
        self.education = education
        self.welfare = welfare
        self.company = company
        self.people = people
        self.jobInfo = jobInfo
        self.address = address
        self.companyInfo = companyInfo


# 爬取页面
# 起始页、结束页
# url
# 应该要输入城市
# https://sou.zhaopin.com/?jl=%E5%B9%BF%E5%B7%9E&sf=0&st=0&kw=python%E5%AE%9E%E4%B9%A0&kt=3
# https://sou.zhaopin.com/?p=3&jl=%E5%B9%BF%E5%B7%9E&kw=python
# 得出结论
# https://sou.zhaopin.com/?p=页码&jl=城市&kw=工作
# 需要注意url的编码格式，可以使用urlencode
class zhilianSpider(object):
    def __init__(self, start_page, end_page, city, job, url):
        self.start_page = start_page
        self.end_page = end_page
        self.city = city
        self.job = job
        self.url = url

        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
        }

        # selenium
        # 无头模式
        chrome_opt = webdriver.ChromeOptions()
        chrome_opt.add_argument("--headless")

        # 浏览器驱动对象
        self.browser = webdriver.Chrome(options=chrome_opt)

    # 请求模块
    # 一级界面
    def first_job_request(self, url):
        # 模拟浏览器运行
        # 发起请求
        print("一级界面：", url)
        self.browser.get(url)
        time.sleep(1)
        return self.browser.page_source

    # 二级界面
    def second_job_request(self, url, callback, item):
        # 创建请求
        req = urllib.request.Request(url, headers=self.headers)
        print("二级页面：", url)
        # 发起请求
        res = urllib.request.urlopen(req)

        # 回调函数
        # 为什么要有这个东西，是这样的，我们从一级界面中获取了job的url然后，我们利用这个url发起请求，这个时候得到相应，然后回调出解析二级界面的函数
        yield callback(res.read().decode("utf-8"), item)

    # 解析模块
    # 一级界面
    def first_job_parse(self, html):
        html_etree = etree.HTML(html)

        # 一页的职位
        job_list = html_etree.xpath('//div[@id="listContent"]/div')
        # print("job_list", job_list)

        for job in job_list:
            # 创建职位对象
            jobitem = JobItem()

            try:
                # 职位
                jobitem.job = job.xpath('.//span[contains(@class,"jobname__title")]/text()')[0]
                # print("jobitem.job", jobitem.job)
                # 工资
                jobitem.salary = job.xpath('.//p[contains(@class, "job__saray")]/text()')[0]
                # 经验要求
                jobitem.experience = job.xpath('.//li[2]/text()')[0]
                # 学历要求
                jobitem.education = job.xpath('.//li[3]/text()')[0]
                # 福利
                jobitem.welfare = "|".join(job.xpath(".//div[contains(@class,'welfare')]//text()"))
                # 公司名称
                jobitem.company = job.xpath('.//a[contains(@class,"company_title")]/@href')[0]
                # 人数
                jobitem.people = job.xpath('.//div[contains(@class,"job__comdec")]/span[2]/text()')[0]
                # 获取二级页面的url
                second_url = job.xpath('.//a[contains(@zp-stat-id,"jd_click")]/@href')[0]
                yield self.second_job_request(url=second_url, callback=self.second_job_parse, item=jobitem)
            except:
                jobitem.job = "职位空空如也"
                jobitem.education = "学历不作要求"
                jobitem.welfare = "福利未说明"



    # 二级界面
    def second_job_parse(self, html, item):
        html_tree = etree.HTML(html)
        jobItem = item
        # print(jobItem.job)
        jobItem.companyInfo = r"\n".join(html_tree.xpath("//div[@class='jjtxt']//text()"))
        jobItem.address = html_tree.xpath("//p[@class='add-txt']//text()")[0] if html_tree.xpath("//p[@class='add-txt']//text()") else "未提供地址"
        jobItem.jobInfo = r"\n".join(html_tree.xpath("//div[contains(@class,'pos-common')]//text()"))

        return jobItem

    # 写入文件txt
    def write_to_txt(self, list1, job_kw):
        if os.path.exists("./智联工作信息-" + str(job_kw) + ".txt"):
            pass
        else:
            with open("./智联工作信息-" + str(job_kw) + ".txt", "w+", encoding="utf-8") as fp:
                for job in list1:
                    fp.write(json.dumps(job, ensure_ascii=False) + "\n\n")

    # 写入mysql数据库
    def write_to_sql(self, list1):
        # 创建数据库的连接
        conn = pymysql.connect(host="127.0.0.1", port=3306, user="lwd", password="123456", db="study", charset="utf8")

        # 游标
        cursor = conn.cursor()

        # 创建sql语句
        for job in list1:
            try:
                sql = 'insert into zhilianInfo values (null,"{}","{}","{}","{}","{}","{}","{}","{}")'.format(job["job"], job["salary"], job["experience"], job["education"], job["welfare"], job["company"][:200]+"···", job["people"], job["address"])
                # 开始
                conn.begin()
                # 写入数据库
                cursor.execute(sql)
                # 提交
                conn.commit()
            except:
                continue
        # 关闭游标
        cursor.close()
        # 关闭连接
        conn.close()

    # 对外接口
    def crawl_spider(self):
        all_job_list = []

        for page in range(int(self.start_page), int(self.end_page)+1):
            # 处理url
            page_url = self.url.format(str(page), self.city, self.job)
            # 发起一级界面的请求
            html_text = self.first_job_request(page_url)
            # 解析界面
            # 在解析完一级界面的时候
            # 发起对二级界面的请求
            # 并且回调对二级界面的解析
            result = self.first_job_parse(html_text)
            # print(result)

            for i in result:
                # print(i)
                for jobItem in i:
                    # print(jobItem)
                    job_dic = {}
                    job_dic["job"] = jobItem.job
                    job_dic["salary"] = jobItem.job
                    job_dic["experience"] = jobItem.experience
                    job_dic["education"] = jobItem.education
                    job_dic["welfare"] = jobItem.welfare
                    job_dic["company"] = jobItem.company
                    job_dic["people"] = jobItem.people
                    job_dic["jobInfo"] = jobItem.jobInfo
                    job_dic["address"] = jobItem.address
                    job_dic["company"] = jobItem.companyInfo
                    # print(job_dic)
                    all_job_list.append(job_dic)

        # 写入文件txt
        # print(all_job_list)
        self.write_to_txt(all_job_list, job_kw=self.job)

        # 写入数据mysql
        # self.write_to_sql(list1=all_job_list)

        # 关闭驱动
        self.browser.close()


# 主函数
def main():
    url = "https://sou.zhaopin.com/?p={}&jl={}&kw={}"
    # 开始页
    start_page = input("开始页：")
    # 结束页
    end_page = input("结束页：")
    # 请输入城市
    city = input("城市：")
    # 职位
    job = input("职位：")
    # 初始化爬虫对象
    zhilian = zhilianSpider(start_page=start_page, end_page=end_page, city=city, job=job, url=url)
    # 调用接口
    zhilian.crawl_spider()


if __name__ == '__main__':
    main()
