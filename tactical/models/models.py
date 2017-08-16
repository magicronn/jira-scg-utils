from marshmallow import post_load
from marshmallow_jsonapi import Schema, fields

# TODO: All jira_nav_* member schema should be type URL, but they are not validating as URLs even when perfect

class User(object):
    def __init__(self, id, display_name='', email='', active=True):
        super(User, self).__init__()
        self.__dict__.update(locals())

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.id == other.id
        return NotImplemented

    def __ne__(self, other):
        """Define a non-equality test"""
        if isinstance(other, self.__class__):
            return self.id != other.id
        return NotImplemented

    def __hash__(self):
        """Override the default hash behavior (that returns the id or the object)"""
        return hash(tuple(self.id))


class UserFilter(object):
    def __init__(self, id, summary='', description='', users_by_chapter=None):
        super(UserFilter, self).__init__()
        self.__dict__.update(locals())


class IssueDigest(object):
    def __init__(self, id, chapter_key, epic_key, jira_nav_url, users,
                 ttl_story_pts=0, ttl_issue_cnt=0, unestimated_issue_cnt=0):
        id = "{}:{}".format(epic_key, chapter_key)
        super(IssueDigest, self).__init__()
        self.__dict__.update(locals())


class Epic(object):
    def __init__(self, id, jira_id, summary, description,
                 created, assignee,
                 priority, status, rank,
                 jira_epic_url, issue_digests,
                 due_date=None):
        super(Epic, self).__init__()
        self.__dict__.update(locals())


class Release(object):
    def __init__(self, id, title, description, chapter_key, release_date, released, jira_release_url, issue_digests):
        super(Release, self).__init__()
        self.__dict__.update(locals())


class Chapter(object):
    def __init__(self, id, title, jira_project_url, users):
        super(Chapter, self).__init__()
        self.__dict__.update(locals())


class BurnDownBar(object):
    def __init__(self, id, start_dt, remaining_work, new_work, unestimated_count, predicted_work,
                 remaining_url, new_url, unestimated_url):
        super(BurnDownBar, self).__init__()
        self.__dict__.update(locals())


class BurnDown(object):
    def __init__(self, id, scale, bars):
        super(BurnDown, self).__init__()
        self.__dict__.update(locals())


class UserSchema(Schema):
    id = fields.Str(required=True)
    display_name = fields.Str(required=True)
    email = fields.Str()

    @post_load
    def make_user(self, data):
        return User(**data)

    class Meta:
        type_ = 'users'
        strict = True


class UserFilterSchema(Schema):
    id = fields.Str(required=True)
    summary = fields.Str(required=True)
    description = fields.Str()

    @post_load
    def make_userfilter(self, data):
        return UserFilter(**data)

    class Meta:
        type_ = 'user-filters'
        strict = True


class IssueDigestSchema(Schema):
    id = fields.Str(required=True)
    chapter_key = fields.Str(required=True)
    epic_key = fields.Str(required=True)
    jira_nav_url = fields.Str(required=True)
    ttl_story_pts = fields.Int(required=True, default=0)
    ttl_issue_cnt = fields.Int(required=True, default=0)
    unestimated_issue_cnt = fields.Int(required=True, default=0)
    users = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='users',
        schema='UserSchema'
    )

    @post_load
    def make_issuedigest(self, data):
        return IssueDigest(**data)

    class Meta:
        type_ = 'issue-digests'
        strict = True


class EpicSchema(Schema):
    id = fields.Str(required=True)
    jira_id = fields.Str()
    summary = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    due_date = fields.DateTime()
    created = fields.DateTime(required=True)
    priority = fields.Str()
    status = fields.Str()
    rank = fields.Str()
    jira_epic_url = fields.Str()
    assignee = fields.Relationship(
        many=False,
        include_resource_linkage=True,
        type_='users',
        schema='UserSchema'

    )
    issue_digests = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='issue-digests',
        schema='IssueDigestSchema'
    )

    @post_load
    def make_epic(self, data):
        return Epic(**data)

    class Meta:
        type_ = 'epics'
        strict = True


class ReleaseSchema(Schema):
    id = fields.Str(required=True)
    title = fields.Str()
    description = fields.Str()
    chapter_key = fields.Str(required=True)
    release_date = fields.Date()
    jira_release_url = fields.Str(required=True)
    issue_digests = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='issue-digests',
        schema='IssueDigestSchema'
    )

    @post_load
    def make_release(self, data):
        return Release(**data)

    class Meta:
        type_ = 'releases'
        strict = True


class ChapterSchema(Schema):
    id = fields.Str(required=True)
    title = fields.Str(required=True)
    jira_project_url = fields.Str(required=True)
    users = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='users',
        schema='UserSchema'
    )

    @post_load
    def make_chapter(self, data):
        return Chapter(**data)

    class Meta:
        type_ = 'chapters'
        strict = True


class BurnDownBarSchema(Schema):
    id = fields.Str(required=True)
    start_dt = fields.Date(required=True)
    remaining_work = fields.Int(default=0, required=True)
    new_work = fields.Int(default=0, required=True)
    unestimated_count = fields.Int(default=0, required=True)
    predicted_work = fields.Int(default=0)
    remaining_url = fields.Str()
    new_url = fields.Str()
    unestimated_url = fields.Str()

    @post_load
    def make_burndownbar(self, data):
        return BurnDownBar(**data)

    class Meta:
        type_ = 'burndown-bars'
        strict = True



class BurnDownSchema(Schema):
    id = fields.Str(required=True)
    scale = fields.Str(required=True)
    bars = fields.Relationship(
        related_url='/bursdowns/{epic_id}/bars',
        related_url_kwargs={'epic_id': '<id>'},
        many=True,
        include_resource_linkage=True,
        type_='burndown-bars',
        schema='BurnDownBarSchema'
    )

    @post_load
    def make_burndown(self, data):
        return BurnDown(**data)

    class Meta:
        type_ = 'burndowns'
        strict = True
