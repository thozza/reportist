# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Tomas Hozza
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import datetime
import calendar
import argparse
import logging

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import todoist

from reportist.log import log


CONF_PATH = '~/.reportist.yaml'


class Reportist:

    def __init__(self, apikey):
        self._todist_api = todoist.api.TodoistAPI(apikey)
        self._todist_api.sync()
        self._projects_by_id = {project['id']: project for project in self._todist_api.state['projects']}

    def get_completed(self, projects, subprojects=True):
        seen = set()
        projects_to_check = [seen.add(project.data['id']) or project
                             for project in projects if project.data['id'] not in seen]

        if subprojects:
            for project in projects_to_check:
                for subp in self.get_subprojects(project):
                    if subp.data['id'] not in seen:
                        seen.add(subp.data['id'])
                        projects_to_check.append(subp)

        log.debug("Getting completed tasks for projects: %s", [project.data['name'] for project in projects_to_check])
        completed = list()
        for project in projects_to_check:
            completed.extend(self._todist_api.items.get_completed(project.data['id']))

        return completed

    def get_projects(self):
        return self._todist_api.state['projects']

    def get_project_by_name(self, name):
        for p in self._todist_api.state['projects']:
            if name in p.data['name']:
                return p

    def get_subprojects(self, project):
        subprojects = list()
        project_ids = [project.data['id']]

        for project_id in project_ids:
            for p in self._todist_api.state['projects']:
                if p.data['parent_id'] == project_id:
                    subprojects.append(p)
                    project_ids.append(p.data['id'])
        return subprojects

    def get_project_str(self, project_id):
        project = self._projects_by_id[project_id]
        string = project['name']
        if project['parent_id'] is not None:
            string = self.get_project_str(project['parent_id']) + '/' + string
        return string

    @staticmethod
    def filter_completed_by_date(completed, start, end=None):
        if end is None:
            end = datetime.date.today()
        filtered = list()
        for item in completed:
            date_completed = datetime.datetime.strptime(item['date_completed'], '%Y-%m-%dT%H:%M:%SZ').date()
            if start <= date_completed <= end:
                filtered.append(item)
        return filtered

    @staticmethod
    def filter_completed_by_month(completed, month=None, year=None):
        if month is None:
            month = datetime.date.today().month
        if year is None:
            year = datetime.date.today().year
        log.debug("Filtering for month %d year %d", month, year)

        start = datetime.date(year, month, 1)
        log.debug("Start date: %s", start.strftime('%a %Y-%m-%d %H:%M:%S'))
        end = datetime.date(year, month, calendar.monthrange(year,month)[1])
        log.debug("End date: %s", end.strftime('%a %Y-%m-%d %H:%M:%S'))

        return Reportist.filter_completed_by_date(completed, start, end)

    @staticmethod
    def filter_completed_by_week(completed, week=None, year=None):
        if week is None:
            week = datetime.date.today().strftime("%W")
        if year is None:
            year = datetime.date.today().year
        log.debug("Filtering for week %d year %d", week, year)

        start = datetime.datetime.strptime("{}-{}-1".format(year, week), "%Y-%W-%w").date()
        log.debug("Start date: %s", start.strftime('%a %Y-%m-%d %H:%M:%S'))
        end = datetime.datetime.strptime("{}-{}-0".format(year, week), "%Y-%W-%w").date()
        log.debug("End date: %s", end.strftime('%a %Y-%m-%d %H:%M:%S'))

        return Reportist.filter_completed_by_date(completed, start, end)


def get_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        default=False,
        help='Show debug messages.'
    )
    parser.add_argument(
        '-k', '--apikey',
        action='store',
        default=None,
        help='API Key to use when communicating with Todoist.'
    )
    parser.add_argument(
        '--store-apikey',
        action='store_true',
        default=False,
        help='Store the provided API Key in ~/.reportinst.yaml.'
    )
    parser.add_argument(
        '-p', '--project',
        action='store',
        default=None,
        help='Report on project that contains the provided string. First matching project is used.'
    )
    parser.add_argument(
        '--no-subprojects',
        action='store_true',
        default=False,
        help="Don't check any subprojects of the requested project"
    )
    parser.add_argument(
        '-w', '--week',
        action='store',
        type=int,
        default=None,
        help='Number of week to report on. (Default: current week)'
    )
    parser.add_argument(
        '-m', '--month',
        action='store',
        type=int,
        default=None,
        help='Number of month to report on. (Default: current month)'
    )
    parser.add_argument(
        '-y', '--year',
        action='store',
        type=int,
        default=None,
        help='Year to report on. (Default: current year)'
    )
    parser.add_argument(
        '-r', '--report',
        action='store',
        choices=['week', 'month'],
        default='week',
        help='Type of report to generate. (Default: week)'
    )

    return parser


def save_apikey(apikey):
    with open(os.path.expanduser(CONF_PATH), 'w+') as f:
        f.write(yaml.dump({'APIKEY': apikey}, Dumper=Dumper))


def load_apikey():
    key = None

    try:
        with open(os.path.expanduser(CONF_PATH)) as f:
            key = yaml.load(f.read(), Loader=Loader)['APIKEY']
    except FileNotFoundError:  # The config file does not exist
        pass
    except KeyError:  # The file exist, but it does not contain the apikey
        pass

    return key


def application(options=None):
    conf = get_argparser().parse_args(options)

    if conf.apikey and conf.store_apikey:
        save_apikey(conf.apikey)
    apikey = conf.apikey if conf.apikey else load_apikey()
    if apikey is None:
        raise RuntimeError("No API Key provided. You must provide one to authenticate to Todoist.")

    reportist = Reportist(apikey)

    if conf.project is not None:
        project = reportist.get_project_by_name(conf.project)
        completed = reportist.get_completed([project], not conf.no_subprojects)
    else:
        completed = reportist.get_completed(reportist.get_projects(), subprojects=False)

    if conf.report == 'week':
        completed_filtered = reportist.filter_completed_by_week(completed, conf.week, conf.year)
    # month
    else:
        completed_filtered = reportist.filter_completed_by_month(completed, conf.month, conf.year)

    print('Completed {} tasks.'.format(len(completed_filtered)))
    for c in completed_filtered:
        print('{}: ({})\t {}'.format(
            datetime.datetime.strptime(c['date_completed'], '%Y-%m-%dT%H:%M:%SZ').strftime('%a %Y-%m-%d %H:%M:%S'),
            reportist.get_project_str(c['project_id']), c['content']))


def main(options=None):
    """
    Main function.

    :param options: command line options
    :return: None
    """
    try:
        # Do this as the first thing, so that we don't miss any debug log
        if get_argparser().parse_args(options).debug:
            log.setLevel(logging.DEBUG)
        application(options)
    except KeyboardInterrupt:
        log.info("Application interrupted by the user.")
        sys.exit(0)
    #except Exception as e:
    #    logger.critical("Unexpected error occurred: %s", str(e))
    #    sys.exit(1)
    else:
        sys.exit(0)


def run_main():
    main(sys.argv[1:])
