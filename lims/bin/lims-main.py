#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import sys
import getpass
import argparse

from ConfigParser import ConfigParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# print os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

from lims.tools.report import parser_add_report
from lims.tools.sample import parser_add_sample
from lims.tools.project import parser_add_project
from lims.tools.check import parser_add_check
from lims.tools.release import parser_add_release


__doc__ = '''
\033[1;32m========================================================
{}
                --toolkits to operate lims for novogene
========================================================\033[0m
'''.format(open(os.path.join(BASE_DIR, 'banner.txt')).read())

__version__ = '1.0'
__author__ = 'suqingdong <suqingdong@novogene.com>'

conf = ConfigParser()

configfile = os.path.join(BASE_DIR, 'config.ini')
conf.read(configfile)

BASE_URL = conf.get('lims', 'base_url')

print 'BaseURL: \033[32m{}\033[0m'.format(BASE_URL)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='lims',
        version='%(prog)s {}'.format(__version__),
        description=__doc__,
        usage='%(prog)s [OPTIONS] SUBCMD [SUB-OPTIONS]',
        epilog='contact: {}'.format(__author__),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-u',
        '--username',
        help='the username to login lims[default=%(default)s]',
        default=getpass.getuser())

    parser.add_argument('-p', '--password', help='the password to login lims')

    parser.add_argument(
        '-c',
        '--config',
        help='the config file to login lims[default=%(default)s]',
        default=os.path.join(os.path.expanduser('~'), '.lims.ini'))

    parser.add_argument(
        '-debug',
        '--verbose',
        action='store_true',
        help='show verbose processing for debugging')

    # 子命令解析
    subparser = parser.add_subparsers(
        title='sub-commands',
        # description='valid sub-commands',
        # help='help information',
        dest='subparser_name',
        metavar='',)

    # 0 项目信息
    parser_project = subparser.add_parser(
        'project',
        formatter_class=argparse.RawTextHelpFormatter,
        help='show project informations')
    parser_add_project(parser_project)

    # 1 上传报告
    parser_report = subparser.add_parser(
        'report',
        formatter_class=argparse.RawTextHelpFormatter,
        help='upload report')
    parser_add_report(parser_report)

    # 2 获取样本信息
    parser_sample = subparser.add_parser(
        'sample',
        formatter_class=argparse.RawTextHelpFormatter,
        help='get sample_info or sample_list')
    parser_add_sample(parser_sample)

    # 3 DoubleCheck报告
    parser_check = subparser.add_parser(
        'check',
        formatter_class=argparse.RawTextHelpFormatter,
        help='doublecheck report')
    parser_add_check(parser_check)

    # 4 数据释放
    parser_release = subparser.add_parser(
        'release',
        formatter_class=argparse.RawTextHelpFormatter,
        help='data release')
    parser_add_release(parser_release)

    # print dir(subparser)
    # print subparser.nargs
    if not sys.argv[1:]:
        parser.print_help()
        exit()

    args = parser.parse_args()

    args.author = __author__

    args.func(base_url=BASE_URL, **vars(args))
