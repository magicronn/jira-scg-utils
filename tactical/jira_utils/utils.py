import json
from urllib import quote_plus
import requests

# https://docs.atlassian.com/jira/REST/cloud/
# https://docs.atlassian.com/jira-software/REST/cloud/
# sos_reports = 211  # Jira Board with all relevant projects in it. Hard to load, but necessary for some queries.

jira_url = 'http://cradlepoint.atlassian.net'
api_url = jira_url + '/rest/api/latest/'
agile_url = jira_url + '/rest/agile/latest/'
jira_user = "rd_reports@cradlepoint.com"
jira_pswd = "ptnoF500"


def build_url_for_query(q, agile=False):
    url = (agile_url if agile else api_url) + quote_plus(q)
    return url


def exec_jira_query(q, agile=False):
    res = {}
    url = (agile_url if agile else api_url) + q
    r = requests.get(url, auth=(jira_user, jira_pswd))
    if r.status_code == 200:
        res = json.loads(r.text)
    return res


def process_jira_request(q, fnc, map_key, agile=False):
    """
    :param q:
    :param fnc:
    :param map_key:
    :param agile:
    :type q: str
    :type fnc: f()
    :type map_key: str
    :type agile: bool
    :return: None
    """
    # the query shouldn't have a startAt param.
    if "startAt" in q:
        raise ValueError('query must not have startAt param')
    if "?" not in q:
        q = q + "?startAt={}"
    else:
        q = q + "&startAt={}"
    current_idx = 0
    while True:
        current_query = q.format(current_idx)
        api_result = exec_jira_query(current_query, agile)
        if not api_result:
            break
        map(fnc, api_result[map_key])
        total_issue_count = api_result['total']
        current_idx += len(api_result[map_key])
        if current_idx >= total_issue_count:
            break


if __name__ == '__main__':

    q_epics_for_board = 'search?jql=project=Lab+and+type=epic+and+status+in+("In Development","In Scoping")'
    epics = exec_jira_query(q_epics_for_board, agile=False)

