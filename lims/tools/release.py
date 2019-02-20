#!/usr/bin/env python
# -*- coding=utf-8 -*-
import sys
import json

from lims.tools.login import login
import utils

# reload(sys)
# sys.setdefaultencoding('utf8')


class Release(object):

    def __init__(self, **kwargs):

        self.kwargs = kwargs
        self.__dict__.update(**kwargs)

        self.session = login(kwargs)

        self.cluster = self.get_cluster()

        self.logger = utils.get_logger(**kwargs)

    def start(self):

        if not self.kwargs['releaseid']:

            fields = 'RID PROJECTCODE PROJECTNAME APPLYREMARK ADDDATE OPERATOR INFORMATIONLEADERDESC INFORMATIONDOUBLE ORIGREC'.split()
            if self.kwargs['show_history']:
                fields += 'RELEASERESULT RELEASETIME RELEASEURL RELEASETYPE RELEASEADDRESS FTPURL DATASIZE COMMENTS'.split()

            rows = self.get_releases(history=self.kwargs['show_history'])

            if not rows:
                if self.kwargs['show_history']:
                    self.logger.info('no release history')
                else:
                    self.logger.info('nothing to release 1')
                exit(0)

            self.logger.debug(json.dumps(rows[0], ensure_ascii=False, indent=2))

            for n, row in enumerate(rows, 1):

                row['APPLYREMARK'] = row['APPLYREMARK'].replace('\n', ';') if row['APPLYREMARK']  else ''
                row['RELEASERESULT'] = '\033[32m{}\033[0m'.format(row['RELEASERESULT'])

                linelist = [row.get(field) for field in fields]

                print '\033[36m----- {n}. {RID} {PROJECTCODE} -----\033[0m'.format(n=n, **row)
                for field,line in zip(fields, linelist):
                    # line = line.replace('\n', ';')
                    print '\033[1m{:25}:\033[0m\t{}'.format(field, line)

        elif not self.kwargs['release_path']:
            self.logger.error('please supply the path to release')

        else:
            self.update_release()

    def update_release(self):

        row = self.get_releases()[0]

        # print json.dumps(row, ensure_ascii=False, indent=2)

        release_size = self.get_release_size()

        release_way = self.get_release_way(release_size)

        # 换了? ...
        # origrec = row['ORIGREC']
        origrec = row['ORIGREC'] - 102

        payload = [
            origrec,
            [
                release_size,
                self.kwargs['release_path'],
                'GB',
                self.kwargs['release_remark'],
                self.cluster,
                release_way,
                release_size
            ]
        ]

        # print json.dumps(payload, ensure_ascii=False)

        url = '{base_url}/KF_AnalysisReport.kf_UpdateRelease.lims'.format(**self.kwargs)
        self.logger.debug('UpdateRelease: ' + url)
        self.logger.debug(payload)
        resp = self.session.post(url, json=payload).json()

        if resp:
            self.logger.warn('release failed because of' + resp[1])
        else:
            self.logger.info('release successfully!')

    def get_cluster(self):

        cluster_map = {
            'TJ': '天津集群',
            'NJ': '南京集群',
            'USA': '美国集群'
        }

        return cluster_map.get(self.kwargs['cluster_name'])

    def get_release_size(self):

        url = '{base_url}/KF_WebServices.kf_GetReleaseSize.lims'.format(**self.kwargs)
        self.logger.debug('GetReleaseSize: ' + url)

        payload = [self.kwargs['release_path'], self.cluster]
        self.logger.debug(payload)

        resp = self.session.post(url, json=payload)

        return resp.text

    def get_release_way(self, release_size):

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_AnalysisReport.cmbReleaseWay&Type=json&p1={cluster}&p2={release_size}'.format(
            **dict(self.__dict__, **locals()))
        self.logger.debug('GetReleaseWay: ' + url)

        resp = self.session.get(url)

        if resp.status_code != 200:
            self.logger.error('please check your release path: {release_path}'.format(**self.kwargs))
            exit(1)

        rows = resp.json()['Tables'][0]['Rows']

        ways = [row['TEXT'] for row in rows]

        release_way = self.kwargs['release_way']

        if release_way and release_way not in ways:
            self.logger.warn('your input release way is unavailable: {release_way}'.format(**self.kwargs))
            release_way = None

        if not release_way:
            if len(ways) > 1:
                self.logger.warn('There are {} ways to release, please choos from follows:\n{}'.format(
                    len(ways),
                    '\n'.join('{} {}'.format(idx, way) for idx, way in enumerate(ways))))
                while True:
                    choice = input('choose the number:')
                    if choice not in range(len(ways)):
                        print 'bad choice, please choose from {}'.format(range(len(ways)))
                        continue
                    release_way = ways[choice]
                    break
            else:
                release_way = ways[0]

        self.logger.info('release_way: \033[32m{}\033[0m'.format(release_way))

        return release_way

    def get_releases(self, history=False):

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_AnalysisReport.kf_GetRelease&Type=json'.format(
            **self.kwargs)

        if history:
            url += '&p1=Y'
            self.logger.debug('GetReleaseHistory:' + url)
        else:
            self.logger.debug('GetRelease:' + url)

        rows = self.session.get(url).json()['Tables'][0]['Rows']

        if not rows:
            self.logger.error('nothing to release 3')
            exit(0)

        ret_rows = []

        if self.kwargs['releaseid']:
            for row in rows:
                if self.kwargs['releaseid'] == row['RID']:
                    ret_rows = [row]
                    break
        elif self.kwargs['project_code']:
            for row in rows:
                if self.kwargs['project_code'] == row['PROJECTCODE']:
                    ret_rows.append(row)
        else:
            ret_rows = rows

        if ret_rows and (self.kwargs['project_code'] or self.kwargs['releaseid']):
        # if ret_rows:
            new_rows = []
            self.logger.debug('get release info ...')
            for row in ret_rows:
                info = self.get_release_info(row['RID'])
                new_rows.append(dict(row, **info))
            return new_rows
        else:
            return ret_rows

    def get_release_info(self, releaseid):

        url = '{base_url}/RUNTIME_SUPPORT.GetData.lims?Provider=KF_AnalysisReport.dgSubDataReleaseInfo&Type=json&p1={releaseid}'.format(
            **dict(self.kwargs, **locals()))

        self.logger.debug('GetReleaseInfo: ' + url)

        infos = self.session.get(url).json()['Tables'][0]['Rows']

        if not infos:
            self.logger.warn('no release info for releaseid: {releaseid}'.format(**locals()))
            return {}

        return infos[0]


def parser_add_release(parser):

    parser.add_argument(
        '-rid', '--releaseid', help='the release id')

    parser.add_argument(
        '-project', '--project-code', help='the project code')

    parser.add_argument('-path', '--release-path', help='the path to release')

    parser.add_argument('-remark', '--release-remark', help='the remark information for this release')

    parser.add_argument(
        '-way',
        '--release-way',
        help='the release way if available',
        choices=['FTP', 'HWFTP', '阿里云', '拷盘'])

    parser.add_argument(
        '-cluster',
        '--cluster-name',
        help='the cluster to release, choose from (%(choices)s)',
        choices=['TJ', 'NJ', 'USA'],
        default='TJ')

    parser.add_argument(
        '-history',
        '--show-history',
        help='show the release history',
        action='store_true')

    parser.set_defaults(func=main)


def main(**args):

    Release(**args).start()


# if __name__ == "__main__":

#     main()
