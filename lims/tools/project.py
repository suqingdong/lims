#!/usr/bin/env python
# -*- coding=utf-8 -*-
'''
    List the project information
'''
import sys
import urllib
import getpass

from lims.tools.login import login
from lims.tools.utils import get_logger


reload(sys)
sys.setdefaultencoding('utf8')


class Project(object):

    def __init__(self, **kwargs):

        self.kwargs = kwargs

        self.session = login(kwargs)

        self.logger = get_logger(**kwargs)

    def start(self):

        if self.kwargs['change_status']:
            if not self.kwargs['stage_code']:
                print 'please supply the stage code to change status'
            else:
                self.change_display_status()
            exit(0)

        rows = self.get_project_list(**self.kwargs)
        # rows = self.get_project_list()

        if rows:
            self.logger.info('There are {} projects'.format(len(rows)))
            fields = 'STAGECODE PROJECTCODE DISPSTATUS ANALYSTPERSON DOUBLECHECKERNAME PROJECTNAME PRODUCTCODE'.split(
            )
            if self.kwargs['show_information']:
                fields.append('INFORMATIONCONTENT')
            # print '\t'.join(fields)

            for n, row in enumerate(rows, 1):
                # for k,v in row.items():
                #     print k, v
                if self.kwargs['show_information']:
                    row['INFORMATIONCONTENT'] = '\033[32m{}\033[0m'.format(row['INFORMATIONCONTENT'])

                # line = '\t'.join(map(lambda x: '{%s}' % x, fields))
                # print line.format(**row)

                print '\033[36m----- {n}. {STAGECODE} {PROJECTNAME} -----\033[0m'.format(n=n, **row)
                linelist = [row[field] for field in fields]
                for field, value in zip(fields, linelist):
                    print '{:20}\t{}'.format(field, value)
        else:
            print 'There are not project analysis for your keywords'

    def get_project_list(self, **kwargs):

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_DataAnalysis.dgStagingTask_H&Type=json&p1=Draft'.format(**self.kwargs)

        self.logger.debug('GET {}'.format(url))
        rows = self.session.get(url).json()['Tables'][0]['Rows']

        if not kwargs:
            return rows

        for key in ('stage_code', 'project_code', 'analyst_person_code'):
            if not kwargs.get(key):
                continue
            KEY = key.replace('_', '').upper()

            # print key, KEY

            new_rows = [row for row in rows if row.get(KEY) == kwargs.get(key)]
            if new_rows:
                return new_rows

    def change_display_status(self):

        row = self.get_project_list(stage_code=self.kwargs['stage_code'])

        if not row:
            print 'no such project with stage code {stage_code}'.format(**self.kwargs)
            exit(1)


        old_status = row[0]['DISPSTATUS']
        new_status = unicode(self.kwargs['change_status'])

        if new_status == old_status:
            print 'the current status is already "{new_status}"'.format(**locals())
            exit(0)

        # keys = '''
        #     ORIGREC STAGECODE STAGES PROJECTCODE PROJECTNAME SUBPROJECTCODE SUBPROJECTNAME CONTRACTNO
        #     CONTRACTNAME SALEMANCODE SALEMAN ANALYSTPERSONCODE ANALYSTPERSON OPERATIONSMANAGERCODE STATUS
        #     DISPSTATUS RETURNCRM PRODUCTCODE OPERATIONSMANAGER DOUBLECHECKER DOUBLECHECKERNAME FTP_URL
        #     INFORMATIONCONTENT FILENAME REMARK COMMENTS SELECTED
        # '''.split()

        # *** bugs here: all fields can be modified
        fields = [
            ['DISPSTATUS', new_status, 'S', old_status],
        ]

        payload = [
            'dgStagingTask1', 'KF_GENETICANALYSIS', fields, row[0]['ORIGREC'],
            None
        ]

        url = '{base_url}/WS_UPDATEPROVIDER.lims'.format(**self.kwargs)
        print '[change_display_status POST]', url
        resp = self.session.post(url, json=payload).json()

        if resp:
            print 'display status changed: {old_status} ==> {new_status}'.format(**locals())
        else:
            print 'change display status failed:', resp


def parser_add_project(parser):

    parser.description = __doc__

    parser.add_argument(
        '-person',
        '--analyst-person-code',
        help='the analysis persion code[default=%(default)s]',
        default=getpass.getuser())

    parser.add_argument(
        '-stage',
        '--stage-code',
        help='the stage code')

    parser.add_argument(
        '-project',
        '--project-code',
        help='the project code')

    parser.add_argument(
        '-info',
        '--show-information',
        help='show the information content',
        action='store_true')

    parser.add_argument(
        '-change',
        '--change-status',
        help='change the display status for a stage code, choose from (%(choices)s)',
        choices=['新建', '进行中', '完成'])

    parser.set_defaults(func=main)


def main(**args):

    Project(**args).start()


# if __name__ == "__main__":

#     main()
