#!/usr/bin/env python
# -*- coding=utf-8 -*-
import sys
import getpass

from lims.tools.login import login
from lims.tools import utils

reload(sys)
sys.setdefaultencoding('utf8')


class Check(object):

    def __init__(self, **kwargs):

        self.kwargs = kwargs

        self.session = login(kwargs)

        self.logger = utils.get_logger(**kwargs)

    def start(self):

        if not self.kwargs['stage_code']:
            tasks = self.get_approve_task()
            if tasks:
                fields = 'REPORT_GUID STAGECODE REPORT_TYPE FULLNAME REPORT_NAME REPORT_URL SAMPLECOUNT SUMDATA COMMENTS'.split()
                for n, row in enumerate(tasks, 1):
                    # print row
                    reports = self.get_approve_report(stage_code=row['STAGECODE'])
                    print '\033[36m----- {n}. {STAGECODE} {PROJECTNAME} -----\033[0m'.format(n=n, **row)
                    print '\t'.join(fields)
                    for report in reports:
                        line = '\t'.join(map(lambda x: '{%s}' % x, fields)).format(**report)
                        print line
            else:
                self.logger.info('no check task')
            exit(0)

        reports = self.get_approve_report(**self.kwargs)

        if not reports:
            print 'no report to check'
            exit(0)

        if not self.kwargs['report_guid']:
            print 'There are {} reports to check:'.format(len(reports))
            fields = 'REPORT_GUID REPORT_TYPE FULLNAME REPORT_NAME REPORT_URL SAMPLECOUNT SUMDATA METHOD COMMENTS'.split()
            for n, report in enumerate(reports, 1):
                print '\033[32m----- {n} {REPORT_NAME} {ADDTIME} -----\033[0m'.format(n=n, **report)
                for field in fields:
                    print '{:11}:  {}'.format(field, report.get(field))
        else:
            self.operate_report(reports)

    def get_approve_task(self):

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_DataAnalysis.dgStagingTask_H&Type=json&p1=Approve'.format(
            **self.kwargs)
        self.logger.debug('GET ' + url)
        
        rows = self.session.get(url).json()['Tables'][0]['Rows']

        return rows

    def get_approve_report(self, **kwargs):

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_DataAnalysis.dgReport&Type=json&p1={stage_code}&p2=Approve'.format(
            **dict(self.kwargs, **kwargs))
        self.logger.debug('GET {}'.format(url))
        rows = self.session.get(url).json()['Tables'][0]['Rows']

        if kwargs.get('report_guid'):
            for row in rows:
                if row['REPORT_GUID'] == kwargs.get('report_guid'):
                    return row
            return None

        return rows

    def operate_report(self, report):

        self.logger.info('dealing with report: {REPORT_GUID} {REPORT_NAME}'.format(**report))

        payload = [report['REPORT_GUID'], 'Approve', self.kwargs['operation'].title()]

        if self.kwargs['operation'] == 'reject':
            # print self.kwargs['password']
            # exit()
            reason = raw_input('> reject reason:')
            payload.append(unicode(reason))

            while True:
                # password = getpass.getpass('> please input your password:')
                password = self.kwargs['password']

                url = '{base_url}/AuditTrail.Authenticate.lims'.format(**self.kwargs)
                self.logger.debug('authenticate {}'.format(url))
                context = [self.kwargs['username'].upper(), password]
                resp = self.session.post(url, json=context).json()

                if resp:
                    break
                else:
                    print '[error] password error!'

        url = '{base_url}/KF_DataAnalysis.SubmitStaging_H2.lims'.format(**self.kwargs)
        self.logger.debug('POST {}'.format(url))
        self.logger.debug(str(payload))
        resp = self.session.post(url, json=payload).json()

        self.logger.debug(resp)

        if not resp[0]:
            self.logger.error('\033[31mfail to {operation} the report! try again or concat {author}\033[0m'.format(**self.kwargs))
        else:
            self.logger.info('\033[36m{operation} the report successfully\033[0m'.format(**self.kwargs))


def parser_add_check(parser):

    parser.add_argument(
        '-stage', '--stage-code', help='the stage code')

    parser.add_argument('-report', '--report-guid', help='the report guid')

    parser.add_argument(
        '-operation',
        help='the operation to do, choose from (%(choices)s) [default=%(default)s]',
        choices=['submit', 'reject'],
        default='submit')

    parser.set_defaults(func=main)


def main(**args):

    # print args
    # exit()

    Check(**args).start()


# if __name__ == "__main__":

#     main()
