#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import sys
# import time
import getpass
import binascii
import requests
import ConfigParser

import utils


reload(sys)
sys.setdefaultencoding('utf8')


def login(args):
    '''
    need params: base_url, config, username, password
    '''

    logger = utils.get_logger(**args)

    session = requests.session()

    conf = ConfigParser.ConfigParser()

    ori_username, ori_password = get_username_password(conf=conf, logger=logger, **args)

    # real username and password to login
    username = ori_username.upper()
    password = map(binascii.b2a_hex, ori_password)
    password = ''.join(map('{:0>4}'.format, password)).upper()

    args['password'] = ori_password

    # step1: get user info
    url = '{base_url}/Authentication.GetUserInfoHtml.lims'.format(**args)
    logger.debug('GetUserInfo from {}'.format(url))

    payload = [username, password]
    user_info = session.post(url, json=payload).json()

    if not user_info:
        logger.error('login failed, wrong username or password!')
        exit(1)

    logger.debug('get user info successfully')
    depts = user_info[0]['Tables'][0]['Rows']
    roles = user_info[1]['Tables'][0]['Rows']

    dept_idx = role_idx = 0

    if len(depts) > 1:
        logger.warn('There are {} depts for {}:'.format(len(depts), username))
        print '\n'.join('{} {}'.format(idx, dept['Dept']) for idx, dept in enumerate(depts))
        dept_idx = input('please choose your dept:')

    if len(roles) > 1:
        logger.warn('There are {} roles for {}:'.format(len(roles), username))
        print '\n'.join('{} {}'.format(idx, role['ROLE']) for idx, role in enumerate(roles))
        role_idx = input('please choose your role:')

    dept = user_info[0]['Tables'][0]['Rows'][dept_idx]['Dept']
    role = user_info[1]['Tables'][0]['Rows'][role_idx]['ROLE']
    logger.debug('用户名:{username}  实验室:{dept}  角色:{role}'.format(**locals()))

    # step2: login
    url = '{base_url}/Authentication.LoginMobile.lims'.format(**args)
    # print '>>>[auth GET]', url
    logger.debug('Login with {}'.format(url))
    payload = {
        'user': username,
        'password': password,
        'dept': dept,
        'role': role,
        'platforma': 'HTML',
        # 'FormId': '',
        # 'FormArgs': '',
        # 'no_c': int(time.time()),
    }
    result = session.get(url, params=payload).text

    if 'Error' in result:
        print result
        exit(1)

    logger.debug('login successfully!')

    if args.get('config'):

        if os.path.exists(args['config']):
            conf.read(args['config'])

        with open(args['config'], 'w') as out:
            if not conf.has_section(ori_username):
                conf.add_section(ori_username)
            conf.set(ori_username, 'password', ori_password)
            conf.write(out)
            logger.debug('updated config file: {config}'.format(**args))

    return session


def get_username_password(conf, logger, **args):

    username = args.get('username')

    password = args.get('password')

    if not password:

        if args.get('config') and os.path.exists(args['config']):

            logger.debug('read config file: {config}'.format(**args))
            conf.read(args['config'])

            if conf.has_section(username):
                password = conf.get(username, 'password')

    if not password:
        logger.warn('password or config file is required to login for user {}'.format(username))
        password = getpass.getpass()

    return username, password


# if __name__ == '__main__':

#     import sys

#     if len(sys.argv) < 3:
#         print 'usage: python %s <username> <password>' % sys.argv[0]
#         exit(1)

#     username, password = sys.argv[1:3]

#     base_url = 'http://172.17.8.19/starlims11.novogene'

#     login(**locals())
