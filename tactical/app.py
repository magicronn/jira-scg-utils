import arrow
import uuid
from urllib import quote_plus
from flask import Flask, jsonify, request, render_template, url_for
from jira_utils.utils import exec_jira_query, jira_url
from models.models import User
from models.models import UserFilter, UserFilterSchema
from models.models import IssueDigest
from models.models import Epic, EpicSchema
from models.models import BurnDown, BurnDownSchema, BurnDownBar
from models.models import Chapter, ChapterSchema
from models.models import Release, ReleaseSchema

quick_debug = True

api_url = '/api/v1'
app = Flask(__name__)
all_chapter_keys = u'UIX, DPL, CTL, ECM, EO, TES, FW, BSF, AP, SSO, DS, HAR, PCI, QFQ, QP' \
                   ', QAS' if not quick_debug else u'BSF, SSO, ECM, UIX, CTL'
relevant_chapter_keys = [x.strip() for x in all_chapter_keys.split(',')]
chapter_user_groups = {'UIX': 'UIX Chapter', 'DPL': 'DAT Chapter', 'CTL': 'CTL Chapter',
                       'ECM': 'ECM-Core Team', 'EO': 'EngOps',
                       'BSF': 'BSF Team', 'DS': 'ECM-App Team', 'HAR': 'HW Team'}
unassigned_user = User(id='Unassigned', display_name='Unassigned')
unknown_release = Release(id='No Release', title='No Release', description='None', chapter_key=None,
                          release_date=None, released=False, jira_release_url=None, issue_digests=None)


# <editor-fold desc="UserFilter stuff">
def _users_in_squad(key):
    filtered_users = set()

    # find all active LAB epics and to build a list of epic keys.
    q = 'search/?jql=project=LAB AND type=Epic and statusCategory="In Progress"'
    labs = exec_jira_query(q)
    epic_keys = []
    if 'issues' in labs:
        for je in labs['issues']:
            epic_keys.append(je['key'])
    epics_str = ",".join(epic_keys)

    # Now get the users who have issues in progress in these epicz.
    q = 'search/?jql=project={} AND "Epic Link" in ({}) AND type!=Epic AND '\
        'statusCategory="In Progress"'.format(key, epics_str)
    labs = exec_jira_query(q)
    if 'issues' in labs:
        # Change this to query by chapter whose epiclink is in this project
        for je in labs['issues']:
            if je['fields']['assignee']:
                whom = _build_user(je['fields']['assignee'])
                filtered_users.add(whom)
    return filtered_users


def _users_in_chapter_work(key=None):
    filtered_users = set()
    # find all active LAB epics and compile their list of users.
    if key:
        q = 'search/?jql=project={} AND type!=Epic and statusCategory="In Progress"&' \
            'startAt=0&maxResults=1000'.format(key)
    else:
        q = 'search/?jql=project in ({}) ' \
            'AND type!=Epic and statusCategory="In Progress"'.format(all_chapter_keys)
    issues = exec_jira_query(q)
    if issues:
        for issue in issues['issues']:
            if issue['fields']['assignee']:
                whom = _build_user(issue['fields']['assignee'])
                filtered_users.add(whom)
    return filtered_users


def _users_in_active_sprint(key=None):
    filtered_users = set()
    if key:
        q = 'search/?jql=Sprint in openSprints() and statusCategory = "In Progress" and project={}'.format(key)
    else:
        # No restriction, all open sprints
        q = 'search/?jql=Sprint in openSprints() and statusCategory = "In Progress"'
    issues = exec_jira_query(q)
    if 'issues' in issues:
        for issue in issues['issues']:
            if issue['fields']['assignee']:
                whom = _build_user(issue['fields']['assignee'])
                filtered_users.add(whom)
    return filtered_users


def _users_in_arch_poc(_=None):
    # Do nothing for now...
    return set()


def _users_nondevs(_=None):
    nondevs = set()
    nondevs.add(User(id="rallphin", display_name="Ryan Allphin", email="rallphin@cradlepoint.com"))
    nondevs.add(User(id="jbelt", display_name="Jen Belt", email="jbelt@cradlepoint.com"))
    nondevs.add(User(id="tdonnelly", display_name="Terrese Donnelly", email="tdonnelly@cradlepoint.com"))
    nondevs.add(User(id="stuckness", display_name="Stoney Tuckness", email="stuckness@cradlepoint.com"))
    nondevs.add(User(id="tmouser", display_name="Tommy Mouser", email="tmouser@cradlepoint.com"))
    return nondevs


all_user_filters = {
    'uf-squad': UserFilter(id='uf-squad', summary='Hide Squad Engineers',
                           description='Hide any engineers with open tickets under an active LAB epic',
                           users_by_chapter=_users_in_squad),
    'uf-chapter-in-prog': UserFilter(id='uf-chapter-in-prog', summary='Hide Chapter In-Progress Engineers',
                                     description='Hide any engineer current working on a ticket marked In-Progress',
                                     users_by_chapter=_users_in_chapter_work),
    'uf-chapter-in-sprint': UserFilter(id='uf-chapter-in-sprint', summary='Hide Chapter Sprint Engineers',
                                       description='Hide any engineer with open tickets in an active sprint',
                                       users_by_chapter=_users_in_active_sprint),
    'uf-arch-poc': UserFilter(id='uf-arch-poc', summary='Hide Engineers currently working on an Arch PoC',
                              description='Hide any engineer currently on loan to an Arch PoC project',
                              users_by_chapter=_users_in_arch_poc),
    'uf-nondevs': UserFilter(id='uf-nondevs', summary='Hide Non-developers',
                             description='Hide any user who is not a developer',
                             users_by_chapter=_users_nondevs)
}
# </editor-fold>


# <editor-fold desc="BurnDown stuff">
week_buckets = True


def get_bucket_for_date(date_text):
    """
    Given a date string, return the bucket that it belongs in.
    :param date_text: Unicode string of date, e.g. u'2016-11-08T11:30:35.326-0700'
    :ptyple date_text: str
    :return: bucket tuple of start and end datetime (arrow)
    :rtype: arrow.datetime
    """
    dt = arrow.get(date_text)
    if week_buckets:
        dow = dt.weekday()
        # TODO: Apparently plural time units for relative adjust is deprecated
        dt_start = dt.replace(days=-dow)
    else:
        dt_start = dt
    return dt_start


def add_to_issue_bucket(issue_buckets, date_text, new_key=None, done_key=None, unest_key=None, est_key=None):
    change_date = get_bucket_for_date(date_text).format('YYYY-MM-DD')
    (c_new_keys, c_done_keys, c_unest_keys, c_est_keys) = issue_buckets.get(change_date, ([], [], [], []))
    if new_key:
        c_new_keys.append(new_key)
    if done_key:
        c_done_keys.append(done_key)
    if unest_key:
        c_unest_keys.append(unest_key)
    if est_key:
        c_est_keys.append(est_key)
    issue_buckets[change_date] = (c_new_keys, c_done_keys, c_unest_keys, c_est_keys)
    return issue_buckets


def add_to_date_bucket(date_buckets, date_text, new_sp=0, fin_sp=0, add_unest=0, del_unest=0):
    """
    Combine deltas into existing or new buckets by date.
    :param date_buckets: dict of date-key to tuple
    :param date_text: text of date from jira or user
    :param new_sp: delta of new sp added
    :param fin_sp: delta of sp removed/finished
    :param add_unest: count of new unestimated issues added
    :param del_unest: count of unestimated issues removed
    :type date_buckets: dict of date,(int,int,int,int)
    """
    change_date = get_bucket_for_date(date_text).format('YYYY-MM-DD')
    (c_new_sp, c_fin_sp, c_add_unest, c_del_unest) = date_buckets.get(change_date, (0, 0, 0, 0))
    date_buckets[change_date] = (new_sp + c_new_sp, fin_sp + c_fin_sp, add_unest + c_add_unest, del_unest + c_del_unest)


# ToDo: This needs a rewrite to simplify
# The two buckets should only be one that contains week:[key, new_sp, done_sp, add_unest, del_unest]
# The build burndown can work from that. Nothing else needed. Should be a lot simpler.
def bucket_deltas_from_issue_history(issue, date_buckets, issue_buckets):
    """
    Given an issue, put the Story Point (SP) deltas into buckets by change date.
    Need to calc (new_story_points, finished_story_points, added_unestimated_issues, deleted_unestimated_issues)
    tuples for each change.
    :param issue: object representing a jira issue including change history.
    :param date_buckets: map of arrow dates to map of tuples. returned by function.
    :return: date_buckets map of date bucket starts to four tuples: (E, U) for just this issue
    :rtype: dict of date:(int, int, int, int)
    """

    # Update the story point totals as they change by merging in deltas.
    # We rely on Jira to return this in most-recent to oldest order.
    # This way we can imply the starting story_point with prev_last_sp
    cur_sp = issue['fields'].get('customfield_10004', 0)  # Get starting values

    # If the issue has been closed, let's remove either the SP or the default SP from totals
    issue_key = issue['key']
    status = issue['fields']['status']['statusCategory']['name']
    if status == "Done":
        resolution_date = issue['fields']['resolutiondate']
        if cur_sp:
            add_to_date_bucket(date_buckets, resolution_date, fin_sp=cur_sp)
            add_to_issue_bucket(issue_buckets, resolution_date, done_key=issue_key)
        else:
            add_to_date_bucket(date_buckets, resolution_date, del_unest=1)
            add_to_issue_bucket(issue_buckets, resolution_date, est_key=issue_key)

    # Now go back through history and update cur_sp

    for history in issue['changelog']['histories']:
        for item in history['items']:
            if item['field'] == 'Story Points':
                if item['toString']:
                    when = history['created']
                    new_sp = int(item['toString'])
                    if new_sp > cur_sp:
                        add_to_date_bucket(date_buckets, when, new_sp=new_sp - cur_sp)
                        add_to_issue_bucket(issue_buckets, when, new_key=issue_key)
                    elif new_sp < cur_sp:
                        add_to_date_bucket(date_buckets, when, fin_sp=cur_sp - new_sp)
                        add_to_issue_bucket(issue_buckets, when, done_key=issue_key)

                    # Did it become unestimated or estimated?
                    if cur_sp and not new_sp:
                        add_to_date_bucket(date_buckets, when, del_unest=1)
                        add_to_issue_bucket(issue_buckets, when, est_key=issue_key)
                    elif new_sp and not cur_sp:
                        add_to_date_bucket(date_buckets, when, add_unest=1)
                        add_to_issue_bucket(issue_buckets, when, unest_key=issue_key)

                    cur_sp = new_sp

    # finally, let's deal with creation
    created = issue['fields'].get('created')
    if cur_sp:
        # must have been created with a story_point estimate
        add_to_date_bucket(date_buckets, created, new_sp=cur_sp)
        add_to_issue_bucket(issue_buckets, created, new_key=issue_key)
    else:
        # else we have an unestimated creation
        add_to_date_bucket(date_buckets, created, add_unest=1)
        add_to_issue_bucket(issue_buckets, created, unest_key=issue_key)

    return date_buckets, issue_buckets
# </editor-fold>


# <editor-fold desc="Jira-to-Tactical Helpers">
def _build_user(ju):
    user = unassigned_user
    if ju:
        user_key = ju['key']
        user_displayname = ju['displayName']
        user_email = ju['emailAddress']
        user_active = ju['active']
        user = User(id=user_key, display_name=user_displayname, email=user_email, active=user_active)
    return user


def _build_issue_digests(issues):
    """
    Construct an array of IssueDigests from the array of jira issues
    :param issues: array of Jira epics returned from a query
    :return:
    :rtype list of IssueDigest
    """
    digests = {}
    digest_users = {}

    if 'issues' in issues:
        for issue in issues['issues']:
            chap_key = issue['fields']['project']['key']
            epic_key = issue['fields']['customfield_10008']
            digest_key = '{}:{}'.format(chap_key, epic_key)

            # Create IssueDigest if it doesn't exist yet.
            if digest_key not in digests:
                q = jira_url + quote_plus('search/?jql=Project={} and "Epic Link"={}'.format(chap_key, epic_key))
                digests[digest_key] = IssueDigest(digest_key, chap_key, epic_key, q, set())
                digest_users[digest_key] = {}

            digest = digests[digest_key]
            digest.ttl_issue_cnt += 1
            if 'customfield_10004' in issue['fields']:
                story_points = issue['fields']['customfield_10004']
                if story_points is None or story_points == 0:
                    digest.unestimated_issue_cnt += 1
                else:
                    digest.ttl_story_pts += story_points
            if issue['fields']['assignee']:
                user_id = issue['fields']['assignee']['name']
                if user_id not in digest_users[digest_key]:
                    digest_users[digest_key][user_id] = _build_user(issue['fields']['assignee'])

    # update all digests.users
    for digest_key in digests.keys():
        digests[digest_key].users = set(digest_users[digest_key].values())

    return digests.values()


def _build_epic(je, include_digest=True):
    # Pull all the fields of the basic JIRA issue response
    # TODO: custom fields may change and should be identified and pulled out earlier
    epic_id = je['key']
    jira_id = je['id']
    summary = je['fields']['summary']
    description = je['fields']['description']
    created = arrow.get(je['fields']['created'])
    priority = je['fields']['priority']['name']
    status = je['fields']['status']['name']
    jira_epic_url = jira_url + '/browse/{}'.format(epic_id)
    assignee = _build_user(je['fields']['assignee'])

    if 'duedate' in je['fields']:
        due_date = arrow.get(je['fields']['duedate'])
    else:
        due_date = None
    if 'customfield_10200' in je['fields']:
        rank = je['fields']['customfield_10200']
    else:
        rank = '0000000'

    issue_digests = []
    if include_digest:
        # Now build the issue digests from this epics child issues
        q = 'epic/{}/issue'.format(epic_id)
        issues = exec_jira_query(q, agile=True)
        issue_digests = _build_issue_digests(issues)
    te = Epic(epic_id, jira_id, summary, description, created, assignee, priority, status, rank,
              jira_epic_url, issue_digests, due_date)

    return te


def _build_chapter(c):
    # Pull all the fields of the basic JIRA issue response
    # TODO: custom fields may change and should be identified and pulled out earlier
    chapter_id = c['key']
    summary = c['name']
    jira_project_url = 'https://cradlepoint.atlassian.net/projects/{}/issues/'.format(chapter_id)

    users = set()
    if chapter_id in chapter_user_groups:
        q = 'group/member?groupname={}'.format(chapter_user_groups[chapter_id])
        group_members = exec_jira_query(q)
        if group_members and 'values' in group_members:
            for u in group_members['values']:
                users.add(_build_user(u))

    if not users:
        # ...get all open issues and create the set of those users.
        q = 'search/?jql=project={} AND resolution is empty and assignee is not empty'.format(chapter_id)
        issues = exec_jira_query(q)
        if 'issues' in issues:
            for issue in issues['issues']:
                user = _build_user(issue['fields']['assignee'])
                if user.active:
                    users.add(user)

    tc = Chapter(chapter_id, summary, jira_project_url, users)
    return tc


def _build_burndown(issues):
    """

    :param issues:
    :return:
    """
    bdbs = []
    delta_buckets = {}  # date:(newSP, finSP, newUnest, removedUnest)
    issue_buckets = {}  # date:(new_work_keys, done_work_keys, add_unest_keys, remove_unest_key)
    if 'issues' in issues:
        # For each issue, go through change history and add deltas for
        # new sp, finished sp, added unest, removed unest.
        # Fill just one date-bucket list of deltas from all issues.
        for issue in issues['issues']:
            # add the issue's deltas into the bucket's
            bucket_deltas_from_issue_history(issue, delta_buckets, issue_buckets)

        if delta_buckets:
            # Iterate over date-keys, calculating rolling unest, new_work, and work. Add missing buckets.
            min_date_key = arrow.get(min(delta_buckets.keys()))
            max_date_key = arrow.get(max(delta_buckets.keys()))

            current_est = 0
            current_unest = 0
            current_work_keys = set()
            current_unest_keys = set()
            # TODO: Pass in scale and epic key to build URLs for the legend: show all changed tickets in this epic.
            for dt, de in arrow.Arrow.span_range('week', min_date_key, max_date_key):
                dt_key = dt.format('YYYY-MM-DD')
                (new_sp, fin_sp, add_unest, del_unest) = delta_buckets.get(dt_key, (0, 0, 0, 0))
                current_est -= fin_sp
                current_unest += add_unest
                current_unest -= del_unest
                (new_keys, del_keys, add_unest_keys, del_unest_keys) = issue_buckets.get(dt_key, ([], [], [], []))
                current_work_keys.difference_update(del_keys)
                current_unest_keys.update(add_unest_keys)
                current_unest_keys.difference_update(del_unest_keys)
                nwk = ",".join(new_keys)
                cwk = ",".join(current_work_keys)
                cuk = ",".join(current_unest_keys)
                bdbs.append(BurnDownBar(start_dt=dt_key, id=uuid.uuid1(),
                                        remaining_work=current_est, unestimated_count=current_unest, new_work=new_sp,
                                        predicted_work=0, new_keys=nwk, work_keys=cwk, unest_keys=cuk))
                current_est = current_est + new_sp
                current_work_keys.update(new_keys)
                current_work_keys.difference_update(del_keys)

    bd = BurnDown(id=uuid.uuid1(), scale=7, bars=bdbs)
    return bd


def _build_release(r, chapter_key=None, include_digests=True):
    # Pull all the fields of the basic JIRA versions response
    release_id = r['id']
    title = r['name']
    description = r.get('description', '')
    # archived = r.get('archived', False)
    release_date = r.get('releaseDate', None)
    jira_release_url = r.get('self', None)
    released = r.get('released', False)

    # If no chapter key provided, get it from the project_id
    if not chapter_key and 'project_id' in r:
        proj_id = r['project_id']
        # load the project by ID
        q = "project/{}".format(proj_id)
        proj = exec_jira_query(q)
        chapter_key = proj['key']
    else:
        chapter_key = 'UNKNOWN'

    # # Now build issue digests for this version
    issue_digests = None
    if include_digests:
        q = 'search/?jql=project={} AND fixVersion={}'.format(chapter_key, release_id)
        issues = exec_jira_query(q)
        issue_digests = _build_issue_digests(issues)
    tr = Release(release_id, title, description, chapter_key, release_date, released, jira_release_url, issue_digests)

    return tr


def _remove_chapter_users(chap, ufh):
    if ufh:
        chap_users = list(chap.users)
        for u in chap_users:
            if u.id in ufh:
                chap.users.remove(u)
    return chap


def get_release(key):
    q = '/version/{}'.format(key)
    release = exec_jira_query(q)
    rel = _build_release(release, chapter_key=None, include_digests=False)
    return rel


def get_userfilters():
    """
    Returns set of all valid user filters.
    User filters can be applied to an chapter's list of users to remove users;.
    Any assignee of work returned by the UserFilter is removed from the chapter.
    :return: list of JSON-API UserFilter
    """
    return all_user_filters.values()


def get_epics(include_digests=True):
    """
    Returns all unresolved epics in LAB, optionally filtered by status and chapter, in rank order.
    :return: All epics in LAB
    """
    q = 'search/?jql=type=epic AND resolution is empty'
    if 'chapter' in request.args:
        chap_key = request.args.get('chapter')
        q += ' AND project={}'.format(chap_key)
    else:
        q += ' AND project=LAB'
    if 'status' in request.args:
        status_keys = request.args.getlist('status')
        for status in status_keys:
            q += ' AND status={}'.format(status)
    q += ' ORDER BY cf[10200] ASC'
    epics = exec_jira_query(q)

    if quick_debug:
        epics['issues'] = epics['issues'][5:20]

    t_epics = []
    for epic in epics['issues']:
        t_epics.append(_build_epic(epic, include_digests))

    return t_epics


def get_epic_by_key(key):
    """
    Return exactly one epic.
    """

    q = 'issue/{}'.format(key)
    je = exec_jira_query(q)
    if not je:
        return None
    te = _build_epic(je)
    return te


def get_burndown_by_jira_id(epic_id):
    """
    Return the BurnDown for the given epic.
    """
    query = "board/{}/epic/{}/issue?expand=changelog" \
            "&fields=key,customfield_10004,sprint,status,resolutiondate,created,project"
    # TODO: Remove this hardcoded Board
    issues = exec_jira_query(query.format(211, epic_id), agile=True)
    bd = _build_burndown(issues)
    return bd


def get_chapters():
    """
    Return the set of all chapters
    """
    q = 'project/'
    chapters = exec_jira_query(q)
    tcs = []
    for c in chapters:
        k = c['key']
        if k in relevant_chapter_keys:
            tcs.append(_build_chapter(c))
    return tcs


def get_chapter_by_key(key):
    """
    Return the Chapter by key.
    Can reduce the list of users returned with it with userfilters=ufk1, ufk2
    """

    # Check for any filters to exclude users
    filtered_users = set()
    if 'userfilter' in request.args:
        filters = request.args.getlist('userfilter')
        for uf in filters:
            if uf in all_user_filters:
                ignored_users = all_user_filters[uf].users_by_chapter(key)
                filtered_users.update(ignored_users)

    q = 'project/{}'.format(key)
    c = exec_jira_query(q)
    tc = _build_chapter(c)
    if filtered_users:
        tc.users.difference_update(filtered_users)

    return tc


def get_chapter_releases(key, release_history=60):
    """
    Return the open releases for the given chapter.
    """
    q = '/project/{}/versions/'.format(key)
    releases = exec_jira_query(q)
    trs = []
    earliest_release_date = arrow.utcnow().shift(days=-release_history)
    for r in releases:
        # limit ourselves to releases no more than N days old
        recent = not r['archived']
        if r.get('releaseDate', None):
            rel_date = arrow.get(r.get('releaseDate'))
            if rel_date < earliest_release_date:
                recent = False
        if recent:
            trs.append(_build_release(r, key))

    return trs


# </editor-fold>


# <editor-fold desc="Flask REST Endpoints">
@app.route(api_url + '/')
def api_version():
    return 'tactical r&d api v1.0'


@app.route(api_url + '/userfilters')
def get_userfilters_api():
    """
    Returns set of all valid user filters.
    User filters can be applied to an chapter's list of users to remove users;.
    Any assignee of work returned by the UserFilter is removed from the chapter.
    :return: list of JSON-API UserFilter
    """
    ufs = UserFilterSchema(many=True)
    d = ufs.dump(get_userfilters()).data
    return jsonify(d)


@app.route(api_url + '/epics/')
def get_epics_api():
    """
    Returns all unresolved epics in LAB, optionally filtered by status and chapter, in rank order.
    :return: All epics in LAB
    """
    t_epics = get_epics()
    es = EpicSchema(many=True, include_data=['issue_digests'])
    e = es.dump(t_epics).data
    return jsonify(e)


@app.route(api_url + '/epics/<key>')
def get_epic_by_key_api(key):
    """
    Return exactly one epic.
    """
    te = get_epic_by_key(key)
    es = EpicSchema(include_data=['issue_digests'])
    e = es.dump(te).data
    return jsonify(e)


@app.route(api_url + '/epics/<key>/burndown')
def get_burndown_by_jira_id_api(key):
    """
    Return the BurnDown for the given epic.
    """
    bd = get_burndown_by_jira_id(key)
    bds = BurnDownSchema(include_data=['bars'])
    rv = bds.dump(bd).data
    return jsonify(rv)


@app.route(api_url + '/chapters/')
def get_chapters_api():
    """
    Return the set of all chapters
    """
    tcs = get_chapters()
    cs = ChapterSchema(many=True)
    rv = cs.dump(tcs).data
    return jsonify(rv)


@app.route(api_url + '/chapters/<key>')
def get_chapter_by_key_api(key):
    """
    Return the Chapter by key.
    Can reduce the list of users returned with it with userfilters=ufk1, ufk2
    """
    tc = get_chapter_by_key(key)
    cs = ChapterSchema()
    rv = cs.dump(tc).data
    return jsonify(rv)


@app.route(api_url + '/chapters/<key>/releases/')
def get_chapter_releases_api(key):
    """
    Return the open releases for the given chapter.
    """
    trs = get_chapter_releases(key)
    rs = ReleaseSchema(many=True, include_data=['issue_digests'])
    rv = rs.dump(trs).data
    return jsonify(rv)


# </editor-fold>


# <editor-fold desc="Tactical Report Endpoints">
def release_sort_cmp(a, b):
    """
    Sort date ascending, Nones last
    :param a:
    :param b:
    :ptype a: Release
    :ptype b: Release
    :return: int
    """
    if a.release_date and b.release_date:
        return cmp(a.release_date, b.release_date)
    elif a.release_date:
        return 1
    elif b.release_date:
        return -1
    else:
        return 0


def _hash_epics_releases(epic_id):
    """
    Given an epic, return two values:
      1. hash of release_id to child issues counts and story point totals
      2. hash of release_id to Release
    :param epic_id: Epic to tally children from
    :return: hash of release_id to counts and release instance
    :rtype: dict of dict of str, int,  dict of str, Release
    """
    r2cnts = {
        'No Release':
            {
                'release': unknown_release,
                'count': 0,
                'story_points': 0
            }
    }
    all_releases = {}

    q = 'epic/{}/issue'.format(epic_id)
    qres = exec_jira_query(q, agile=True)
    # ToDo: Results may be paginated... Look at startAt and maxResult...

    for issue in qres['issues']:
        # Does this issue have story points?
        sp = 0
        if issue['fields']['customfield_10004']:
            sp = issue['fields']['customfield_10004']

        # Which releases is this issue in? (fixVersions)
        # Get the list of releases for this issue (fixVersions), and save them
        iss_rels = {}
        if issue['fields']['fixVersions']:
            for rel in issue['fields']['fixVersions']:
                # Add this release to the dict of rels for the issue
                iss_rels[rel['id']] = all_releases.get(  # reuse if it exists
                    rel['id'],
                    _build_release(rel, chapter_key=None, include_digests=False))
                if rel['id'] not in r2cnts:
                    r2cnts[rel['id']] = {'count': 0, 'story_points': 0}
        else:
            iss_rels[unknown_release.id] = unknown_release
            if unknown_release.id not in r2cnts:
                r2cnts[unknown_release.id] = {'count': 0, 'story_points': 0}

        # Iterate through the issue fixVersions, and update totals for them
        for rel_id in iss_rels.keys():
            r2cnts[rel_id]['count'] = r2cnts[rel_id]['count'] + 1
            r2cnts[rel_id]['story_points'] = r2cnts[rel_id]['story_points'] + sp

        all_releases.update(iss_rels)

    return r2cnts, all_releases


def gen_epic_assignments_page(checked_ufs, issue_keys):
    """
     Build this page with five sections on the page.
     1. Summary data for upper left corner
     2. UserFilters & url for the updates
     3. Chapters and their users
     4. Epics to Develop and their issue digests
     5. Epics to Scope and their issue digests

    :param checked_ufs: list of checked filters (and possibly other junk)
    :param issue_keys: list of jira ticket keys entered by the user
    :return:
    """

    from_url = url_for('whoswhat_report')

    chaps = get_chapters()

    user_filter_states = []
    ufs = get_userfilters()
    for uf in ufs:
        uf_selected = uf.id in checked_ufs
        uf_tmp = {'id': uf.id, 'summary': uf.summary, 'description': uf.description, 'checked': uf_selected}
        user_filter_states.append(uf_tmp)
        if uf_selected:
            for ch in chaps:
                filtered_user_set = uf.users_by_chapter(ch.id)
                filt_user_hash = {u.id: u for u in filtered_user_set}
                _remove_chapter_users(ch, filt_user_hash)

    epic_cnt_summary = {}
    all_epics = get_epics(include_digests=False)
    for e in all_epics:
        epic_cnt_summary[e.status] = 1 + epic_cnt_summary.get(e.status, 0)
    # Replace the unpretty statii
    if 'Scoped and Ready for Commit' in epic_cnt_summary:
        epic_cnt_summary['Scoped and ready'] = epic_cnt_summary['Scoped and Ready for Commit']
        del epic_cnt_summary['Scoped and Ready for Commit']
    epic_cnt_summary['Backlog'] = 0
    if 'To Do' in epic_cnt_summary:
        epic_cnt_summary['Backlog'] = epic_cnt_summary['Backlog'] + epic_cnt_summary['To Do']
        del epic_cnt_summary['To Do']
    if 'To Scope' in epic_cnt_summary:
        epic_cnt_summary['Backlog'] = epic_cnt_summary['Backlog'] + epic_cnt_summary['To Scope']
        del epic_cnt_summary['To Scope']

    # Load up the selected epics for display
    selected_epics = []
    for eid in issue_keys:
        e = get_epic_by_key(eid)
        selected_epics.append(e)
    # for e in all_epics:
    #     if e.status == 'To Scope':
    #         epics_to_scope.append(e)
    #     elif e.status == 'Scoped and Ready for Commit':
    #         epics_to_dev.append(e)

    # Need to pass in the digests for the epics already keyed by the chapters
    selecid = {}  # selected-epic-chap-to-issuedigest
    for e in selected_epics:
        selecid[e.id] = {}
        for eid in e.issue_digests:
            selecid[e.id][eid.chapter_key] = eid.ttl_issue_cnt
    # decid = {}  # todevelop-epicid-chapid-to-issuedigest
    # for e in epics_to_dev:
    #     decid[e.id] = {}
    #     for eid in e.issue_digests:
    #         decid[e.id][eid.chapter_key] = eid.ttl_issue_cnt
    # secid = {}  # to-scope-epic-chap-to-issuedigest
    # for e in epics_to_scope:
    #     secid[e.id] = {}
    #     for eid in e.issue_digests:
    #         secid[e.id][eid.chapter_key] = eid.ttl_issue_cnt

    rv = render_template('whoswhat.html', epic_cnts=epic_cnt_summary,
                         user_filters=user_filter_states,
                         chapters=chaps,
                         selected_epics=selected_epics,
                         # epics_to_scope=epics_to_scope,
                         # epics_to_dev=epics_to_dev,
                         selected_epic_chapter_counts=selecid,
                         # dev_epic_chapter_counts=decid,
                         # scope_epic_chapter_counts=secid,
                         update_url=from_url)

    return rv


def gen_epic_burndowns_page(issue_keys):
    """
    :param issue_keys: list of jira ticket keys entered by the user
    :return:
    """
    from_url = url_for('burndown_report')
    selected_epics = []
    epic_to_series = {}
    epic_to_labels = {}

    for eid in issue_keys:
        e = get_epic_by_key(eid)
        if e:
            selected_epics.append(e)
            bd = get_burndown_by_jira_id(e.jira_id)
            date_labels = []
            series_data = {'unest':[], 'remaining':[], 'new':[], 'predicted':[]}
            for bdb in bd.bars:
                series_data['unest'].append({'y': bdb.unestimated_count, 'issue_keys': bdb.unest_keys})
                series_data['remaining'].append({'y': bdb.remaining_work, 'issue_keys': bdb.work_keys})
                series_data['new'].append({'y': bdb.new_work, 'issue_keys': bdb.new_keys})
                series_data['predicted'].append({'y': bdb.predicted_work, 'issue_keys': None})
                date_labels.append(bdb.start_dt)
            epic_to_series[eid] = series_data
            epic_to_labels[eid] = date_labels

    rv = render_template('burndowns.html',
                         selected_epics=selected_epics,
                         burndown_categories=epic_to_labels,
                         burndown_series=epic_to_series,
                         update_url=from_url)

    return rv


def gen_epic_releases_page(issue_keys):
    """
    :param issue_keys: list of jira ticket keys entered by the user
    :return:
    """
    epics = []
    if issue_keys:
        for eid in issue_keys:
            e = get_epic_by_key(eid)
            epics.append(e)
    else:
        # BUG: Still getting epics not yet in development
        q = 'search/?startAt=0&maxResults=5&jql=type=epic AND resolution is empty AND project=LAB' \
            ' AND status="In Development" ORDER BY cf[10200] ASC'
        epics_json = exec_jira_query(q)

        for epic in epics_json['issues']:
            epics.append(_build_epic(epic))

    from_url = url_for('releases_report')

    # Build the table contents:
    #   list of releases for headers
    #   rows are epics array and epic_release={epic_key:{rel_key: {rel_cnt:N, rel_pct}}}
    release_hash = {}
    epic2rel2counts = {}
    for epic in epics:
        epic2rel2counts[epic.id], issue_releases = _hash_epics_releases(epic.id)
        release_hash.update(issue_releases)

    nav_url_template = "https://cradlepoint.atlassian.net/issues/?jql=fixVersion={} and \"Epic Link\"={}"
    for epic in epics:
        for rid in release_hash.keys():
            if rid in epic2rel2counts[epic.id]:
                epic2rel2counts[epic.id][rid]['nav_url'] = nav_url_template.format(rid,epic.id)

    # Order the list of releases by release date, Nones go last
    releases = release_hash.values()
    releases.sort(key=lambda a: ('3000', a.title) if not a.release_date else (a.release_date, a.title))
    rv = render_template('releases.html',
                         epics=epics,
                         releases=releases,
                         e2r=epic2rel2counts,
                         update_url=from_url)
    return rv


@app.route('/')
def tactical_reports_version():
    return render_template('layout.html')


@app.route('/assignments')
def whoswhat_report():
    split_keys = []
    checked_ufs = []
    for k, v in request.args.iteritems():
        if k == 'csv-issues':
            split_keys = [key.strip().upper() for key in v.split()]
        elif k != 'submit':
            checked_ufs.append(k)
    return gen_epic_assignments_page(checked_ufs, split_keys)


@app.route('/burndowns')
def burndown_report():
    split_keys = []
    issue_keys = request.args.get('csv-issues', None)
    if issue_keys:
        split_keys = [key.strip().upper() for key in issue_keys.split()]
    return gen_epic_burndowns_page(split_keys)


@app.route('/releases')
def releases_report():
    split_keys = []
    issue_keys = request.args.get('csv-issues', None)
    if issue_keys:
        split_keys = [key.strip().upper() for key in issue_keys.split()]
    return gen_epic_releases_page(split_keys)

# </editor-fold>

if __name__ == "__main__":
    app.run(debug=True)
