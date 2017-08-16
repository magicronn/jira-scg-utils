import flask
from app import get_epics_api, get_epic_by_key_api
from app import get_chapters_api, get_chapter_by_key_api, get_chapter_releases_api
from app import get_burndown_by_key_api
from app import get_userfilters_api
from models.models import UserFilterSchema, ChapterSchema, ReleaseSchema
from models.models import EpicSchema, BurnDownSchema


chapter_key = 'CTL'
epic_key = 'LAB-241'

"""
/
/chapters/
/chapters/<key>
/chapters/<key>/releases
/userfilters/
/epics/
/epics/<key>
/epics/<key>/burndown
"""


app = flask.Flask(__name__)


def test_chapter_endpoints():
    with app.test_request_context():
        resp = get_userfilters_api()
        assert(resp)
        assert(resp.status_code == 200)
        data = resp.data
        assert(data)
        userfilters = UserFilterSchema().loads(data, many=True).data
        assert(len(userfilters)>=4)


def test_releases_endpoints():
    with app.test_request_context():
        resp = get_chapter_releases_api(chapter_key)
        assert (resp)
        assert (resp.status_code == 200)
        data = resp.data
        assert (data)
        ctl_releases = ReleaseSchema().loads(data, many=True).data
        assert (ctl_releases)
        assert (len(ctl_releases) > 0)
        assert (ctl_releases[0].id)
        assert (ctl_releases[0].title)
        assert (ctl_releases[0].chapter_key == chapter_key)
        assert (ctl_releases[0].jira_release_url)
        assert (ctl_releases[0].issue_digests)
        assert (len(ctl_releases[0].issue_digests) > 0)


def test_chapter_by_key_endpoint():
    with app.test_request_context():
        resp = get_chapter_by_key_api(chapter_key)
        assert (resp)
        assert (resp.status_code == 200)
        data = resp.data
        assert (data)
        ctl_chapter = ChapterSchema().loads(data, many=False).data
        assert (ctl_chapter)
        assert (ctl_chapter.id)
        assert (ctl_chapter.title)
        assert (ctl_chapter.jira_project_url)
        assert (ctl_chapter.users)
        assert (len(ctl_chapter.users) > 1)


def test_chapters_endpoint():
    with app.test_request_context():
        resp = get_chapters_api()
        assert(resp)
        assert(resp.status_code == 200)
        data = resp.data
        assert (data)
        all_chapters = ChapterSchema().loads(data, many=True).data
        assert(len(all_chapters) > 1)


def test_epics_endpoint():
    with app.test_request_context():
        resp = get_epics_api()
        assert (resp)
        assert (resp.status_code == 200)
        data = resp.data
        assert (data)
        lab_epics = EpicSchema().loads(data, many=True).data
        assert (lab_epics)
        assert (len(lab_epics) > 0)


def test_epics_by_chapter_endpoint():
    with app.test_request_context('/?chapter=CTL'):
        resp = get_epics_api()
        assert (resp)
        assert (resp.status_code == 200)
        data = resp.data
        assert (data)
        ctl_epics = EpicSchema().loads(data, many=True).data
        assert(ctl_epics)


def test_epic_by_key_endpoint():
    with app.test_request_context():
        resp = get_epic_by_key_api(epic_key)
        assert (resp)
        assert (resp.status_code == 200)
        data = resp.data
        assert (data)
        epic = EpicSchema().loads(data, many=False).data
        assert(epic)


def test_burndown_endpoint():
    with app.test_request_context():
        resp = get_burndown_by_key_api(epic_key)
        assert (resp)
        assert (resp.status_code == 200)
        data = resp.data
        assert (data)
        burndown = BurnDownSchema().loads(data, many=False).data
        assert(burndown)
