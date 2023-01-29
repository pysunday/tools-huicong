# coding: utf-8
import argparse

CMDINFO = {
    "version": '0.0.1',
    "description": "慧聪网供应商信息采集",
    "epilog": """
使用案例:
    %(prog)s -l
    %(prog)s -t y791o07blv
    %(prog)s -r 1-10
    %(prog)s
    """,
    'params': {
        'DEFAULT': [
            {
                'name': ['-t', '--type'],
                'help': '类型',
                'dest': 'typename',
            },
            {
                'name': ['-l', '--list'],
                'dest': 'isShowlist',
                'help': '全部类型',
                'default': False,
                'action': 'store_true'
            },
            {
                'name': ['-r', '--range'],
                'help': '采集范围',
                'dest': 'range',
            },
        ],
    }
}

