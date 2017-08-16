from json import dumps
from models.models import *
import arrow


print_on = False

def test_user():
    ###
    ### User
    ###
    bob = User(id='pvaca', display_name='Phil Vaca', email='pvaca@cradlepoint.com')
    user_schema = UserSchema()
    x = user_schema.dump(bob).data
    assert (x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nUser\n" + xs


###
### UserFilter
###
def user_tasks_fn():
    pass


def test_userfilter():
    uf1 = UserFilter(id='uf1', summary='Hide Squad Eng', description='Hides users with open tickets in active LAB epics',
                     users_by_chapter=user_tasks_fn)
    ufs = UserFilterSchema()
    x = ufs.dump(uf1).data
    assert (x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nUserFilter\n" + xs


###
### IssueDigest
###
def test_issuedigest():
    bob = User(id='pvaca', display_name='Phil Vaca', email='pvaca@cradlepoint.com')
    url ='https://cradlepoint.atlassian.net/browse/?'\
         'jql=%22Epic%20Link%22%3D%20LAB-63%20and%20project%3D%22Control%20Plane%22%20' \
         'and%20resolution%20is%20empty'
    issues = IssueDigest(id='foo', chapter_key='CTL', epic_key='LAB-63', jira_nav_url=url,
                         users = [bob], ttl_issue_cnt=1, ttl_story_pts=5, unestimated_issue_cnt=0)
    ids = IssueDigestSchema()
    x = ids.dump(issues).data
    assert (x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nIssueDigest\n" + xs

###
### Epic
###
def test_epic():
    bob = User(id='pvaca', display_name='Phil Vaca', email='pvaca@cradlepoint.com')
    desc = 'API Changes to the MC for allowing users to be added to an NCE overlay network. As well as' \
           ' changes to any existing APIs/new APIs for switching a gateways network via the UI.'
    url = 'https://cradlepoint.atlassian.net/browse/CTL-151'
    created = arrow.get('29/May/17 3:00 PM', 'DD/MMM/YY H:mm A').naive
    issues = IssueDigest(id='foo', chapter_key='CTL', epic_key='LAB-63', jira_nav_url=url,
                         users=[bob], ttl_issue_cnt=1, ttl_story_pts=5, unestimated_issue_cnt=0)
    epic = Epic(id='CTL-151', summary='MC - API changes', description=desc,
                created=created, assignee=bob,
                priority='Medium', status='To Do', rank='0|i07s2v:',
                jira_epic_url=url, issue_digests=[issues])
    es = EpicSchema(include_data=['issue_digests', 'assignee'])
    x = es.dump(epic).data
    assert (x)
    assert (x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nEpic\n" + xs


###
### Release
###
def test_releases():
    url = 'https://cradlepoint.atlassian.net/projects/CTL/versions/19805/tab/release-report-in-progress'
    rel_issue_digest = IssueDigest(id='CTL:LAB-64', chapter_key='CTL', epic_key='LAB-64', jira_nav_url=url,
                         users=set(), ttl_issue_cnt=1, ttl_story_pts=3, unestimated_issue_cnt=0)
    rel_date = arrow.get('26/Feb/17 3:25 PM', 'DD/MMM/YY H:mm A').naive
    url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3D%20LAB-64%20and%20project%3D%22' \
          'Control%20Plane%22%20and%20resolution%20is%20empty'
    bob = User(id='pvaca', display_name='Phil Vaca', email='pvaca@cradlepoint.com')
    issues = IssueDigest(id='foo', chapter_key='CTL', epic_key='LAB-63', jira_nav_url=url,
                         users=[bob], ttl_issue_cnt=1, ttl_story_pts=5, unestimated_issue_cnt=0)
    release = Release(id='R133', title='NCE CTL 780', description='Big release', chapter_key='CTL',
                      release_date=rel_date, jira_release_url=url, issue_digests=[rel_issue_digest, issues])
    rs = ReleaseSchema(include_data=['issue_digests'])
    x = rs.dump(release).data
    assert (x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nRelease\n" + xs


###
### Chapter
###
def test_chapter():
    url = 'https://cradlepoint.atlassian.net/secure/RapidBoard.jspa?projectKey=CTL&rapidView=242'
    bob = User(id='pvaca', display_name='Phil Vaca', email='pvaca@cradlepoint.com')
    tony = User(id='nbliss', display_name='Neil Bliss', email='nbliss@cradlepoint.com')
    fred = User(id='eanderson', display_name='Eric Anderson', email='eanderson@cradlepoint.com')
    chapter = Chapter(id='CTL', title='NCE Control Plane', jira_project_url=url, users=[bob, tony, fred])
    cs = ChapterSchema(include_data=['users'])
    x = cs.dump(chapter).data
    assert (x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nChapter\n" + xs


###
### BurnDownBar
###
def test_burndownbar():
    r_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty'
    n_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty%20and%20created%3E-3d'
    u_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty%20and%20%22Story%20Points%22%20is%20empty'
    bar_start = arrow.get('15/May/17', 'DD/MMM/YY').date()
    bdb = BurnDownBar(id='LAB-63:W01', start_dt=bar_start,
                      remaining_work=8, new_work=0, unestimated_count=4, predicted_work=0,
                      remaining_url = r_url, new_url = n_url, unestimated_url = u_url)
    bdbs = BurnDownBarSchema()
    x = bdbs.dump(bdb).data
    assert(x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nBurnDownBar\n" + xs


###
### BurnDown
###
def test_burndown():
    r_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty'
    n_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty%20and%20created%3E-3d'
    u_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty%20and%20%22Story%20Points%22%20is%20empty'
    bar_start = arrow.get('22/May/17', 'DD/MMM/YY').date()
    bdb = BurnDownBar(id='LAB-63:W01', start_dt=bar_start,
                      remaining_work=8, new_work=0, unestimated_count=4, predicted_work=0,
                      remaining_url=r_url, new_url=n_url, unestimated_url=u_url)
    bdb1 = BurnDownBar(id='LAB-63:W02', start_dt=bar_start,
                      remaining_work=9, new_work=0, unestimated_count=3, predicted_work=0,
                      remaining_url = r_url, new_url = n_url, unestimated_url = u_url)
    r_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty'
    n_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty%20and%20created%3E-3d'
    u_url = 'https://cradlepoint.atlassian.net/issues/?jql=%22Epic%20Link%22%3DLAB-63%20and%20resolution%20is%20empty%20and%20%22Story%20Points%22%20is%20empty'
    bar_start = arrow.get('29/May/17', 'DD/MMM/YY').date()
    bdb2 = BurnDownBar(id='LAB-63:W03', start_dt=bar_start,
                      remaining_work=5, new_work=0, unestimated_count=2, predicted_work=0,
                      remaining_url = r_url, new_url = n_url, unestimated_url = u_url)
    bars = [bdb, bdb1, bdb2]
    burndown = BurnDown(id='BD:LAB-63', scale='weeks', bars=bars)
    bds = BurnDownSchema(include_data=['bars'])
    x = bds.dump(burndown).data
    assert (x)
    if print_on:
        xs = dumps(x, sort_keys=True, indent=4, separators=(',', ': '))
        print "\n\nBurnDown\n" + xs
