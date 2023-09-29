API2ID = {'/wrk2-api/user/register': 0,
          '/wrk2-api/user/follow': 1,
          '/wrk2-api/user/unfollow': 2,
          '/get-media': 3,
          '/wrk2-api/home-timeline/read': 4,
          '/wrk2-api/post/compose': 5,
          '/upload-media': 6,
          '/wrk2-api/user-timeline/read': 7,
          '/wrk2-api/user/login': 8}
ID2API = {v: k for k, v in API2ID.items()}


API2EDGES = {
    '/upload-media': (
        ('istio-ingressgateway', 'media-frontend'),
        ('media-frontend', 'media-mongodb')
    ),
    '/get-media': (
        ('istio-ingressgateway', 'media-frontend'),
        ('media-frontend', 'media-mongodb')
    ),

    '/wrk2-api/user/follow': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'social-graph-service'),
            ('social-graph-service', 'social-graph-mongodb'),
            ('social-graph-service', 'social-graph-redis')
    ),
    '/wrk2-api/user/unfollow': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'social-graph-service'),
            ('social-graph-service', 'social-graph-mongodb'),
            ('social-graph-service', 'social-graph-redis')
    ),

    '/wrk2-api/user/login': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-service'),
            ('user-service', 'user-memcached'),
            ('user-service', 'user-mongodb')
    ),
    '/wrk2-api/user/register': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-service'),
            ('user-service', 'user-mongodb'),
            ('user-service', 'social-graph-service'),
                ('social-graph-service', 'social-graph-mongodb')
    ),

    '/wrk2-api/home-timeline/read': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'home-timeline-service'),
            ('home-timeline-service', 'home-timeline-redis'),
            ('home-timeline-service', 'post-storage-service'),
                ('post-storage-service', 'post-storage-mongodb'),
                ('post-storage-service', 'post-storage-memcached')
    ),
    '/wrk2-api/user-timeline/read': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-timeline-service'),
            ('user-timeline-service', 'user-timeline-redis'),
            ('user-timeline-service', 'post-storage-service'),
                ('post-storage-service', 'post-storage-mongodb'),
                ('post-storage-service', 'post-storage-memcached'),
            ('user-timeline-service', 'user-timeline-mongodb')
    ),

    '/wrk2-api/post/compose': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-service'),
            ('user-service', 'compose-post-service'),

        ('nginx-thrift', 'media-service'),
            ('media-service', 'compose-post-service'),

        ('nginx-thrift', 'unique-id-service'),
            ('unique-id-service', 'compose-post-service'),

        ('nginx-thrift', 'text-service'),
            ('text-service', 'user-mention-service'),
                ('user-mention-service', 'user-memcached'),
                ('user-mention-service', 'user-mongodb'),
                ('user-mention-service', 'compose-post-service'),
            ('text-service', 'url-shorten-service'),
                ('url-shorten-service', 'url-shorten-mongodb'),
                ('url-shorten-service', 'compose-post-service'),
            ('text-service', 'compose-post-service'),

        ('compose-post-service', 'post-storage-service'),
            ('post-storage-service', 'post-storage-mongodb'),
        ('compose-post-service', 'user-timeline-service'),
            ('user-timeline-service', 'user-timeline-mongodb'),
            ('user-timeline-service', 'user-timeline-redis'),
        ('compose-post-service', 'compose-post-redis'),
        ('compose-post-service', 'write-home-timeline-rabbitmq'),
        ('write-home-timeline-service', 'write-home-timeline-rabbitmq'),
        ('write-home-timeline-rabbitmq', 'write-home-timeline-service'),
            ('write-home-timeline-service', 'home-timeline-redis'),
            ('write-home-timeline-service', 'social-graph-service'),
                ('social-graph-service', 'social-graph-redis'),
                ('social-graph-service', 'social-graph-mongodb'),
    ),
}


SPAN_MAPPING = {
    # /wrk2-api/post/compose
    ('url-shorten-service', 'MongoInsertUrls'): ('url-shorten-mongodb', 'InsertUrls'),
    ('user-mention-service', 'MmcGetUsers'): ('user-memcached', 'GetUsers'),
    ('user-mention-service', 'MongoFindUsers'): ('user-mongodb', 'FindUsers'),
    ('post-storage-service', 'MongoInsertPost'): ('post-storage-mongodb', 'InsertPost'),
    ('user-timeline-service', 'MongoInsertPost'): ('user-timeline-mongodb', 'InsertPost'),
    ('social-graph-service', 'RedisGet'): ('social-graph-redis', 'Get'),
    ('user-timeline-service', 'RedisUpdate'): ('user-timeline-redis', 'Update'),
    ('social-graph-service', 'MongoFindUser'): ('social-graph-mongodb', 'FindUser'),
    ('social-graph-service', 'RedisInsert'): ('social-graph-redis', 'Insert'),
    ('write-home-timeline-service', 'RedisUpdate'): ('home-timeline-redis', 'Update'),
    ('compose-post-service', 'RabbitMQPublish'): ('write-home-timeline-rabbitmq', 'Publish'),
    ('compose-post-service', 'RedisUpdate'): ('compose-post-redis', 'Update'),
    ('compose-post-service', 'RedisGet'): ('compose-post-redis', 'Get'),
    # /upload-media
    ('media-frontend', 'MongoInsertMedia'): ('media-mongodb', 'InsertMedia'),
    # /wrk2-api/home-timeline/read
    ('home-timeline-service', 'RedisFind'): ('home-timeline-redis', 'Find'),
    ('post-storage-service', 'MmcGetPosts'): ('post-storage-memcached', 'GetPosts'),
    ('post-storage-service', 'MongoFindPosts'): ('post-storage-mongodb', 'FindPosts'),
    ('post-storage-service', 'MmcSetPosts'): ('post-storage-memcached', 'SetPosts'),
    # /wrk2-api/user/login
    ('user-service', 'MmcGetLogin'): ('user-memcached', 'GetLogin'),
    ('user-service', 'MongoFindUser'): ('user-mongodb', 'FindUser'),
    ('user-service', 'MmcSetLogin'): ('user-memcached', 'SetLogin'),
    # /wrk2-api/user-timeline/read
    ('user-timeline-service', 'RedisFind'): ('user-timeline-redis', 'Find'),
    ('user-timeline-service', 'MongoFindUserTimeline'): ('user-timeline-mongodb', 'FindUserTimeline'),
    ('user-timeline-service', 'RedisUpdate'): ('user-timeline-redis', 'Update'),
    ('post-storage-service', 'MmcGetPosts'): ('post-storage-memcached', 'GetPosts'),
    ('post-storage-service', 'MongoFindPosts'): ('post-storage-mongodb', 'FindPosts'),
    ('post-storage-service', 'MmcSetPosts'): ('post-storage-memcached', 'SetPosts'),
    # /wrk2-api/user/register
    ('user-service', 'MongoFindUser'): ('user-mongodb', 'FindUser'),
    ('user-service', 'MongoInsertUser'): ('user-mongodb', 'InsertUser'),
    ('social-graph-service', 'MongoInsertUser'): ('social-graph-mongodb', 'InsertUser'),
    # /get-media
    ('media-frontend', 'MongoGetMedia'): ('media-mongodb', 'GetMedia'),
    # /wrk2-api/user/follow
    ('social-graph-service', 'MongoUpdateFollower'): ('social-graph-mongodb', 'UpdateFollower'),
    ('social-graph-service', 'MongoUpdateFollowee'): ('social-graph-mongodb', 'UpdateFollowee'),
    ('social-graph-service', 'RedisUpdate'): ('social-graph-redis', 'Update'),
    # /wrk2-api/user/unfollow
    ('social-graph-service', 'MongoDeleteFollower'): ('social-graph-mongodb', 'DeleteFollower'),
    ('social-graph-service', 'MongoDeleteFollowee'): ('social-graph-mongodb', 'DeleteFollowee'),
    ('social-graph-service', 'RedisUpdate'): ('social-graph-redis', 'Update'),
}


READABLE_NAME = {
    '/wrk2-api/user/login': '/login',
    '/wrk2-api/user/register': '/register',
    '/wrk2-api/user/follow': '/follow',
    '/wrk2-api/user/unfollow': '/unfollow',
    '/wrk2-api/home-timeline/read': '/home-timeline',
    '/wrk2-api/user-timeline/read': '/user-timeline',
    '/get-media': '/get-media',
    '/upload-media': '/upload-media',
    '/wrk2-api/post/compose': '/compose',
}
NAME2READABLE = {v: k for k, v in READABLE_NAME.items()}


def get_timeseries_xaxis():
    xs = []
    day = 6
    hour = 0
    minute = 24
    for i in range(8 * 60):
        minute += 24
        if minute >= 60:
            minute = minute % 60
            hour += 1
        if hour >= 24:
            hour = hour % 24
            day += 1
        xs.append('07/%.2d %.2d:%.2d' % (day, hour % 24, minute % 60))
    xs_val = [0, 60, 120, 180, 240, 300, 360, 420]
    xs_labels = ['07/06<br>(TUE)', '07/07<br>(WED)', '07/08<br>(THU)', '07/09<br>(FRI)', '07/10<br>(SAT)',
                 '07/11<br>(SUN)', '07/12<br>(MON)', 'NOW']
    return xs, xs_val, xs_labels


TS_XS, TS_XTICKS, TS_LABELS = get_timeseries_xaxis()
