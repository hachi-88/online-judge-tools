# Python Version: 3.x
# -*- coding: utf-8 -*-
import onlinejudge.service
import onlinejudge.problem
from onlinejudge.problem import LabeledString, TestCase
import onlinejudge.dispatch
import onlinejudge.implementation.utils as utils
import onlinejudge.implementation.logging as log
import io
import posixpath
import bs4
import requests
import urllib.parse
import zipfile
import collections
import itertools
from typing import *


@utils.singleton
class AOJService(onlinejudge.service.Service):

    def get_url(self):
        return 'http://judge.u-aizu.ac.jp/onlinejudge/'

    def get_name(self):
        return 'aoj'

    @classmethod
    def from_url(cls, s: str) -> Optional['AOJService']:
        # example: http://judge.u-aizu.ac.jp/onlinejudge/
        result = urllib.parse.urlparse(s)
        if result.scheme in ('', 'http', 'https') \
                and result.netloc == 'judge.u-aizu.ac.jp':
            return cls()
        return None


class AOJProblem(onlinejudge.problem.Problem):
    def __init__(self, problem_id):
        self.problem_id = problem_id

    def download(self, session: Optional[requests.Session] = None, is_system: bool = False) -> List[TestCase]:
        if is_system:
            return self.download_system(session=session)
        else:
            return self.download_samples(session=session)
    def download_samples(self, session: Optional[requests.Session] = None) -> List[TestCase]:
        session = session or utils.new_default_session()
        # get
        resp = utils.request('GET', self.get_url(), session=session)
        # parse
        soup = bs4.BeautifulSoup(resp.content, utils.html_parser)  # NOTE: resp.content is not decoded for workaround, see https://github.com/kmyk/online-judge-tools/pull/186
        samples = utils.SampleZipper()
        for pre in soup.find_all('pre'):
            log.debug('pre: %s', str(pre))
            hn = utils.previous_sibling_tag(pre)
            if hn is None:
                div = pre.parent
                if div is not None:
                    log.debug('div: %s', str(hn))
                    hn = utils.previous_sibling_tag(div)
            log.debug('hN: %s', str(hn))
            log.debug(hn)
            keywords = [ 'sample', 'example', '入力例', '出力例' ]
            if hn and hn.name in [ 'h2', 'h3' ] and hn.string and any(filter(lambda keyword: keyword in hn.string.lower(), keywords)):
                s = utils.textfile(pre.string.lstrip())
                name = hn.string
                samples.add(s, name)
        return samples.get()
    def download_system(self, session: Optional[requests.Session] = None) -> List[TestCase]:
        session = session or utils.new_default_session()
        get_url = lambda case, type: 'http://analytic.u-aizu.ac.jp:8080/aoj/testcase.jsp?id={}&case={}&type={}'.format(self.problem_id, case, type)
        testcases: List[TestCase] = []
        for case in itertools.count(1):
            # input
            # get
            resp = utils.request('GET', get_url(case, 'in'), session=session, raise_for_status=False)
            if resp.status_code != 200:
                break
            in_txt = resp.text
            if case == 2 and testcases[0].input.data == in_txt:
                break # if the querystring case=??? is ignored
            # output
            # get
            resp = utils.request('GET', get_url(case, 'out'), session=session)
            out_txt = resp.text
            testcases += [ TestCase(
                LabeledString('in%d.txt' % case, in_txt),
                LabeledString('out%d.txt' % case, out_txt),
                ) ]
        return testcases

    def get_url(self) -> str:
        return 'http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id={}'.format(self.problem_id)

    @classmethod
    def from_url(cls, s: str) -> Optional['AOJProblem']:
        # example: http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=1169
        # example: http://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=DSL_1_A&lang=jp
        result = urllib.parse.urlparse(s)
        querystring = urllib.parse.parse_qs(result.query)
        if result.scheme in ('', 'http', 'https') \
                and result.netloc == 'judge.u-aizu.ac.jp' \
                and utils.normpath(result.path) == '/onlinejudge/description.jsp' \
                and querystring.get('id') \
                and len(querystring['id']) == 1:
            n, = querystring['id']
            return cls(n)
        return None

    def get_service(self) -> AOJService:
        return AOJService()


onlinejudge.dispatch.services += [ AOJService ]
onlinejudge.dispatch.problems += [ AOJProblem ]
