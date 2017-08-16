from marshmallow_jsonapi import Schema, fields


class User(object):
    def __init__(self, id, first_name='', last_name='', email=''):
        super(User, self).__init__()
        self.__dict__.update(locals())


class UserFilter(object):
    def __init__(self, id, summary='', description='', user_issues_jql=''):
        super(UserFilter, self).__init__()
        self.__dict__.update(locals())


class IssueDigest(object):
    def __init__(self, chapter_key, epic_key, jira_nav_url, users,
                 ttl_story_pts=0, ttl_issue_cnt=0, unestimated_issue_cnt=0):
        id = "{}:{}".format(epic_key, chapter_key)
        super(IssueDigest, self).__init__()
        self.__dict__.update(locals())


class Epic(object):
    def __init__(self, id, summary, description,
                 created, assignee,
                 priority, status, rank,
                 jira_epic_url, issue_digests,
                 due_date=None):
        super(Epic, self).__init__()
        self.__dict__.update(locals())


class Release(object):
    def __init__(self, id, summary, chapter_key, release_date, jira_release_url, issue_digests):
        super(Release, self).__init__()
        self.__dict__.update(locals())


class Chapter(object):
    def __init__(self, id, summary, description, jira_project_url, users, releases):
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
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    email = fields.Str(required=True)

    class Meta:
        type_ = 'users'
        strict = True


class UserFilterSchema(Schema):
    id = fields.Str(required=True)
    summary = fields.Str(required=True)
    description = fields.Str(required=True)
    user_issues_jql = fields.Str(required=True)

    class Meta:
        type_ = 'user-filters'
        strict = True


class IssueDigestSchema(Schema):
    id = fields.Str(required=True)
    chapter_key = fields.Str(required=True)
    epic_key = fields.Str(required=True)
    jira_nav_url = fields.Url(required=True)
    ttl_story_pts = fields.Int(required=True, default=0)
    ttl_issue_cnt = fields.Int(required=True, default=0)
    unestimated_issue_cnt = fields.Int(required=True, default=0)
    users = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='users',
        schema='UserSchema'
    )

    class Meta:
        type_ = 'issue-digests'
        strict = True


class EpicSchema(Schema):
    id = fields.Str(required=True)
    summary = fields.Str(required=True)
    description = fields.Str(required=True)
    due_date = fields.DateTime()
    created = fields.DateTime(required=True)
    assignee = fields.Relationship(
        many=False,
        include_resource_linkage=True,
        type_='users',
        schema='UserSchema'

    )
    priority = fields.Str(required=True)
    status = fields.Str(required=True)
    rank = fields.Str(required=True)
    jira_epic_url = fields.Url(required=True)
    issue_digests = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='issue-digests',
        schema='IssueDigestSchema'
    )

    class Meta:
        type_ = 'epics'
        strict = True


class ReleaseSchema(Schema):
    id = fields.Str(required=True)
    summary = fields.Str(required=True)
    chapter_key = fields.Str(required=True)
    release_date = fields.Date()
    jira_release_url = fields.Url(required=True)
    issue_digests = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='issue-digests',
        schema='IssueDigestSchema'
    )

    class Meta:
        type_ = 'releases'
        strict = True


class ChapterSchema(Schema):
    id = fields.Str(required=True)
    summary = fields.Str(required=True)
    description = fields.Str(required=True)
    jira_project_url = fields.Url(required=True)
    users = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='users',
        schema='UserSchema'
    )
    releases = fields.Relationship(
        many=True,
        include_resource_linkage=True,
        type_='releases',
        schema='ReleaseSchema'
    )

    class Meta:
        type_ = 'chapters'
        strict = True


class BurnDownBarSchema(Schema):
    id = fields.Str(required=True)
    start_dt = fields.Date(required=True)
    remaining_work = fields.Int(default=0, required=True)
    new_work = fields.Int(default=0, required=True)
    unestimated_count = fields.Int(default=0, required=True)
    predicted_work = fields.Int(default=0, required=True)
    remaining_url = fields.Url()
    new_url = fields.Url()
    unestimated_url = fields.Url()

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

    class Meta:
        type_ = 'burndowns'
        strict = True
