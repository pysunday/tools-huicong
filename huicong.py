#coding: utf-8
import re
import xlsxwriter
import json
from io import BytesIO
from urllib.parse import urlencode
from sunday.core import Logger, getParser, Fetch, printTable, Auth, MultiThread, printTable, getException
from sunday.tools.huicong.params import CMDINFO
from bs4 import BeautifulSoup
from pydash import find, get

HcError = getException()

logger = Logger(CMDINFO['description']).getLogger()

class Huicong():
    def __init__(self, *args, **kwargs):
        urlBase = 'http://www.hc360.com'
        self.urls = {
                'list': urlBase + '/seller/{typename}',
                'detail': urlBase + '/supplyself/{goods_id}.html',
                'index': urlBase + '/index.html',
                }
        self.headers = {
                # 'Content-Type': 'application/x-www-form-urlencoded'
                'Accept-Language': 'zh-CN,zh;q=0.9'
                }
        self.fetch = Fetch()
        self.typename = None
        self.range = None
        self.isShowlist = False
        self.thread_num = 30
        self.datas = []
        self.errors = []
        self.companyFlag = {}
        self.tableTitleList = [{
                'key': 'name',
                'title': '公司名称',
                }, {
                'key': 'contactor',
                'title': '联系人',
                }, {
                'key': 'duty',
                'title': '职位',
                }, {
                'key': 'mp',
                'title': '手机1',
                }, {
                'key': 'otherTelephone',
                'title': '手机2',
                }, {
                'key': 'telephone',
                'title': '电话',
                }, {
                'key': 'regaddress',
                'title': '地址',
                }, {
                'key': 'introduce4SEO',
                'title': '公司描述',
                }, {
                'key': 'mainPro4SEO',
                'title': '货品描述',
                }, {
                'key': 'url',
                'title': '数据来源',
                }]

    def initAuth(self):
        auth = Auth('not', '[慧聪网]')
        self.typename = auth.addParams('typename', value=self.typename, tip='类型', isSave=False)

    def getPageUrl(self, typename):
        url = self.urls['list'].format(typename=f'{typename}.html')
        res = self.fetch.get(url)
        soup = BeautifulSoup(res.content, 'lxml')
        self.parseList(res.content, url)
        return [link.attrs.get('href').strip() for link in soup.select('.s-mod-page a')]

    def showlist(self):
        url = self.urls['index']
        res = self.fetch.get(url)
        soup = BeautifulSoup(res.content, 'lxml')
        typelist = [{
            'name': it.text,
            'url': it.attrs.get('href'),
            'typename': it.attrs.get('href', '').split('/')[-1].replace('.html', '')
            } for it in soup.select('.sub-menu-dd dd a')]
        return typelist

    def printList(self):
        typelist = self.showlist()
        printTable(['编号', '类型', '编码', '链接'])([[idx + 1, it['name'], it['typename'], it['url']] for idx, it in enumerate(typelist)])

    def parseDetail(self, goods, list_url, idx):
        goods_id = goods.get('id')
        url = self.urls['detail'].format(goods_id=goods_id)
        res = self.fetch.get(url)
        text = res.content.decode('utf-8')
        companyJson = re.match(r".*var\scompanyJson\s=\s{(.*?)};.*", text.replace('\n', ''))
        company = goods.copy()
        if companyJson:
            jsonstr = '{' + companyJson.groups()[0] + '}'
            company = json.loads(jsonstr)
            company.update({ 'url': url })
            self.companyFlag[goods['flag']] = True
            logger.info('添加公司%s' % company)
            self.datas.append(company)
        elif get(self.companyFlag, goods['flag']) is None:
            company.update({ 'url': url })
            self.companyFlag[goods['flag']] = False
            logger.info('添加公司%s' % company)
            self.datas.append(company)
        # else:
        #     self.errors.append({
        #         'detail': url,
        #         'list': list_url,
        #         'list_idx': idx,
        #         })

    def parseList(self, text, url):
        soup = BeautifulSoup(text, 'lxml')
        lis = soup.select('li.grid-list')
        for idx, li in enumerate(lis):
            try:
                name = li.select_one('.newCname p a')
                goods = {
                        'id': li.attrs.get('data-businid').strip(),
                        'mp': li.attrs.get('data-telphone').strip(),
                        'name': name.text.strip(),
                        }
                if goods['id'] and goods['mp'] and goods['name']:
                    goods['flag'] = goods['name'] + goods['mp']
                    if get(self.companyFlag, goods['flag']) != True:
                        self.parseDetail(goods, url, idx)
            except Exception as e:
                logger.exception(e)

    def parseListWrap(self, pages):
        for page in pages:
            url = self.urls['list'].format(typename=page)
            res = self.fetch.get(url)
            self.parseList(res.content, url)

    def saveExcel(self, filename='output'):
        workbook = xlsxwriter.Workbook(f'./{filename}.xlsx')
        bold = workbook.add_format({'bold': True})
        cell_format = workbook.add_format()
        cell_format.set_text_wrap()
        cell_format.set_align('center')
        cell_format.set_align('vcenter')
        worksheet = workbook.add_worksheet()
        worksheet.set_default_row(80)
        worksheet.set_row(0, 30)
        worksheet.set_column('B:F', 15)
        worksheet.set_column('A:A', 35)
        worksheet.set_column('G:G', 35)
        worksheet.set_column('H:H', 50)
        worksheet.set_column('I:I', 35)
        worksheet.set_column('J:J', 35)
        for idx, item in enumerate(self.tableTitleList):
            worksheet.write(0, idx, item.get('title'), cell_format)
            for didx, data in enumerate(self.datas):
                worksheet.write(didx + 1, idx, data.get(item.get('key')), cell_format)
        if len(self.errors) > 0:
            errorsheet = workbook.add_worksheet()
            errorsheet.set_column('A:A', 50)
            errorsheet.set_column('B:B', 50)
            errorsheet.set_column('C:C', 10)
            for idx, error in enumerate(self.errors):
                errorsheet.write(idx, 0, error.get('detail'))
                errorsheet.write(idx, 1, error.get('list'))
                errorsheet.write(idx, 2, error.get('list_idx'))
        workbook.close()

    def getDataByOne(self, typename):
        pages = self.getPageUrl(typename)
        if self.thread_num:
            multiData = [[item for item in pages[i::self.thread_num]] for i in range(self.thread_num)]
            MultiThread(multiData, lambda item, _: [self.parseListWrap, (item,)]).start()
        else:
            self.parseListWrap(pages)

    def getDataByAll(self):
        typelist = []
        if self.range:
            typerange = self.range.split('-')
            if len(typerange) == 2:
                start = int(typerange[0]) - 1
                end = int(typerange[1]) - 1
                typelist = self.showlist()[start:end]
            else:
                raise HcError(-1, 'range范围适用-隔离，如：1-10')
        else:
            typelist = self.showlist()
        def handler(arr):
            for it in arr:
                self.getDataByOne(it.get('typename'))
        if self.thread_num:
            multiData = [[item for item in typelist[i::self.thread_num]] for i in range(self.thread_num)]
            MultiThread(multiData, lambda item, _: [handler, (item,)]).start()
        else:
            handler(typelist)

    def run(self):
        # self.initAuth()
        if self.isShowlist:
            self.printList()
        elif self.typename:
            self.getDataByOne(self.typename)
            self.saveExcel(self.typename)
        else:
            self.getDataByAll()
            self.saveExcel(self.range or 'all')


def runcmd():
    parser = getParser(**CMDINFO)
    handle = parser.parse_args(namespace=Huicong())
    handle.run()


if __name__ == "__main__":
    runcmd()
