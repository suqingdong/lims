#!/usr/bin/env python
# -*- coding=utf-8 -*-
import sys
import json
import tarfile
import dateutil.parser

from lims.tools.login import login
from lims.tools.project import Project
from lims.tools import utils


reload(sys)
sys.setdefaultencoding('utf8')


class Report(object):

    def __init__(self, **kwargs):

        self.kwargs = kwargs

        self.session = login(kwargs)

        self.project = Project(**kwargs).get_project_list(**kwargs)[0]

        self.logger = utils.get_logger(**kwargs)

    def start(self):

        if self.kwargs['filename'] and self.kwargs['type']:
            self.upload_report()
        elif self.kwargs['delete']:
            self.delete_report()
        elif not (self.kwargs['filename']  or self.kwargs['type']):
            self.show_report_status()
        elif not self.kwargs['filename']:
            self.logger.error('please supply the report file')
        elif not self.kwargs['type']:
            self.logger.error('please specific the report type')

    def has_upload_final(self):

        url = '{base_url}/KF_DataAnalysis.HasUploadFinalReport.lims'.format(**self.kwargs)
        self.logger.debug('check final: ' + url)

        payload = [self.kwargs['stage_code']]

        return self.session.post(url, json=payload).json()

    def upload_report(self):

        # step1: 上传文件
        url = '{base_url}/Runtime_Support.SaveFileFromHTML.lims?ScriptName=QuickIntro.uploadFileProcessingScript'.format(**self.kwargs)
        self.logger.debug('upload file: ' + url)
        with utils.safe_open(self.kwargs['filename'], 'rb') as f:
            resp = self.session.post(url, files={'file': f}).json()

        if not resp['success']:
            self.logger.error('upload file failed!')
            exit(1)

        # step2: 填写报告
        payload = resp['result'] + [self.kwargs['stage_code'], self.kwargs['type'].upper(), None, self.kwargs['message']]

        if self.kwargs['type'] == 'final':
            # if self.has_upload_final():  # False已上传， True未上传
            #     print '>>>首次上传结题报告sop和产量信息为必填项，后续无需再次填写'    ### 可以上传多个结题报告？？？
            sop_method = self.get_sops()
            payload += [sop_method]
        else:
            payload += ['']

        if self.kwargs['sample_count'] and self.kwargs['data_size']:
            sample_count = self.kwargs.get('sample_count')
            data_size = self.kwargs.get('data_size')
        else:
            sample_count, data_size = self.get_data_size()

        self.logger.info('\033[32m样本数：{sample_count}  数据量：{data_size}\033[0m'.format(**locals()))
        payload += [sample_count, data_size]

        self.logger.debug(payload)

        url = '{base_url}/KF_DataAnalysis.UploadReport_H.lims'.format(**self.kwargs)
        self.logger.debug('upload report: ' + url)
        resp = self.session.post(url, json=payload).json()
        self.logger.debug(resp)

        if resp[-1] == 'SUCCESS':
            report_name = resp[0]
            add_time = dateutil.parser.parse(resp[1]).strftime('%Y-%m-%d %H:%M:%S')
            self.logger.info('report upload successfully!')

            report_guid = self.get_reports(report_name=report_name, add_time=add_time)['REPORT_GUID']
            self.logger.debug('report guid: ' + report_guid)

        # step3: 提交给DoubleCheck
        url = '{base_url}/KF_DataAnalysis.SubmitStaging_H2.lims'.format(**self.kwargs)
        self.logger.debug('submit report: ' + url)
        payload = [report_guid, 'Draft', 'Submit']
        resp = self.session.post(url, json=payload).text

        self.logger.info('submit report to doublechecker "{DOUBLECHECKER}" successfully!'.format(**self.project))
        self.show_report_status(report_guid)

    def get_data_size(self):

        with tarfile.open(self.kwargs['filename']) as f:
            qcstat = [each for each in f.getnames() if 'qcstat.xls' in each]
            if not qcstat:
                self.logger.warn('qcstat.xls not found! please type sample_count and data_size manually.')
                sample_count = raw_input('sample count:')
                data_size = raw_input('data size:')
            else:
                self.logger.debug('found qcstat.xls: ' + qcstat[0])
                samples = set()
                data_size = 0
                for line in f.extractfile(qcstat[0]):
                    linelist = line.strip().split('\t')
                    if linelist[0] == 'Sample name':
                        continue
                    samples.add(linelist[0])
                    data_size += float(linelist[4])

                sample_count = len(samples)

        return sample_count, data_size

    def get_sops(self):

        product_code = self.project['PRODUCTCODE']

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_DataAnalysis.DS_TestRelMethod_H&Type=json&p1=&p2={product_code}'.format(
            **dict(self.kwargs, **locals()))
        self.logger.debug('get sop methods: ' + url)
        rows = self.session.get(url).json()['Tables'][0]['Rows']
        avail_sops = [sop['VALUE'] for sop in rows]
        if self.kwargs['sop_method']:
            if all(sop in avail_sops for sop in self.kwargs['sop_method'].split(',')):
                return self.kwargs['sop_method']

        # print rows
        self.logger.info('optional sop methods are as follows:')
        print '#code\tvalue'
        print '\n'.join('{}\t{}'.format(sop['VALUE'], sop['TEXT']) for idx, sop in enumerate(rows))
        while True:
            sops = raw_input('>>> please choose one or more sop code(separate by comma):')
            all_pass = True
            for choice in sops.split(','):
                if choice not in avail_sops:
                    print 'invalid input: {}'.format(choice)
                    all_pass = False
                    break
            if all_pass:
                return sops

    def get_reports(self, report_guid=None, report_name=None, add_time=None):

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_DataAnalysis.dgReport&Type=json&p1={stage_code}&p2=Draft'.format(**self.kwargs)
        self.logger.debug('get reports: ' + url)
        rows = self.session.get(url).json()['Tables'][0]['Rows']

        # print json.dumps(rows, indent=2, ensure_ascii=False)

        if report_guid:
            for row in rows:
                if row['REPORT_GUID'] == report_guid:
                    return row
            return None
        elif (report_name and add_time):
            for row in rows:
                if row['REPORT_NAME'] == report_name and row['ADDTIME'] == add_time:
                    return row
            return None

        return rows

    def delete_report(self):

        report = self.get_reports(self.kwargs['delete'])

        if not report:
            self.logger.error('no report guid {delete}'.format(**self.kwargs))
            exit(1)

        if report['STATUS'] != 'Draft':
            self.logger.error('the status of report "{delete}" is "{STATUS}", only "Draft" can be deleted'.format(**dict(self.kwargs, **report)))
            exit(1)

        url = '{base_url}/Sunway.DeleteRows.lims'.format(**self.kwargs)
        self.logger.debug('delete report: ' + url)
        payload = [
            'kf_geneticanalysis_report',
            [report['ORIGREC']]
        ]
        self.logger.debug(payload)
        resp = self.session.post(url, json=payload)

        if resp.text == 'true':
            self.logger.info('the report "{delete}" has been deleted'.format(**self.kwargs))

    def show_report_status(self, report_guid=None):

        rows = self.get_reports()
        if not rows:
            self.logger.info('This stage code has no report uploaded')
        else:
            fields = 'REPORT_GUID STATUS DISPSTATUS STAGECODE REPORT_NAME ANALYSTPERSON DOUBLECHECKERNAME OPERATIONSMANAGER REPORT_URL ADDTIME'.split()
            n = 0
            for row in rows:
                if report_guid and row['REPORT_GUID'] != report_guid:
                    continue
                n += 1
                print '\033[32m----- {n} {REPORT_NAME} -----\033[0m'.format(n=n, **row)
                for field in fields:
                    context = dict(self.project, **row)
                    if field in ('DISPSTATUS', 'REPORT_URL'):
                        context[field] = '\033[32m{}\033[0m'.format(context[field])
                    print '{:25}: {}'.format(field, context.get(field))


def parser_add_report(parser):

    parser.add_argument('filename', help='the report file to upload', nargs='?')

    parser.add_argument(
        '-stage', '--stage-code', help='the stage code', required=True)

    parser.add_argument(
        '-t',
        '--type',
        help='the type of report, choose from [%(choices)s]',
        choices=['qc', 'mapping', 'final'])

    parser.add_argument(
        '-sop', '--sop-method', help='the sop method for the product')

    parser.add_argument('-count', '--sample-count', help='the count of sample')

    parser.add_argument('-data', '--data-size', help='the total data size')

    parser.add_argument('-msg', '--message', help='the message for this report')

    parser.add_argument('-d', '--delete', help='the report_id to delete')

    parser.set_defaults(func=main)


def main(**args):

    Report(**args).start()


# if __name__ == "__main__":

#     main()
