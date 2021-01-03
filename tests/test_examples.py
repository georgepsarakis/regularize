import unittest

from regex_composer.expression import Pattern, pattern


class TestExamples(unittest.TestCase):
    def setUp(self):
        self.pattern = pattern()
        self.apache_webserver_combined_log = (
            '127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] '
            '"GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" '
            '"Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:84.0) '
            'Gecko/20100101 Firefox/84.0"'
        )

    def tearDown(self) -> None:
        Pattern.registry.clear()

    def test_html_tag_extension(self):
        class HTMLTag(Pattern):
            def __call__(self, opening=True):
                if opening:
                    new = self.literal('<')
                else:
                    new = self.literal('</')
                return new.any_of(Pattern.ANY_ASCII_CHARACTER). \
                    quantify(minimum=1).literal('>')
        self.pattern.ext.registry.add('html_tag', HTMLTag)
        self.assertEqual(self.pattern.ext.html_tag().build(), '<[a-z]+>')

    def test_apache_combined_log_parsing(self):
        ip = pattern().any_of('.', Pattern.ANY_NUMBER).quantify(minimum=7).group('ip')
        identd_client_id = pattern().literal('-')
        http_auth_user = pattern().any_of(Pattern.ANY_ASCII_CHARACTER, '_', '.').\
            at_least_one().group('http_auth_user')
        time = pattern().literal('[').none_of(']').quantify(minimum=26).literal(']')
        http_verb = pattern().literal('"').group(
            'http_verb',
            pattern=pattern().uppercase_ascii_letters().at_least_one())
        url = pattern().group(
            name='url',
            pattern=pattern().none_of(Pattern.ANY_WHITESPACE).at_least_one())
        http_version = pattern().literal('HTTP/').any_of('1', '2').literal('.').\
            any_of('0', '1').group('http_version').literal('"')
        http_status_code = pattern().group(
            name='http_status_code',
            pattern=pattern().any_of(Pattern.ANY_NUMBER).exactly(3))
        response_bytes = pattern().group(
            name='response_bytes_without_headers',
            pattern=pattern().any_of(Pattern.ANY_NUMBER).at_least_one())
        referer = pattern().literal('"').\
            group(name='referer',
                  pattern=pattern().none_of('"').at_least_one()).literal('"')
        user_agent = pattern().literal('"').\
            group(name='user_agent',
                  pattern=pattern().none_of('"').at_least_one())

        p = Pattern.join(
            pattern().whitespace(),
            [ip, identd_client_id, http_auth_user, time,
             http_verb, url, http_version, http_status_code,
             response_bytes, referer, user_agent]
        )
        self.assertDictEqual(
            {'ip': '127.0.0.1', 'http_auth_user': 'frank',
             'http_verb': 'GET', 'url': '/apache_pb.gif',
             'http_version': 'HTTP/1.0', 'http_status_code': '200',
             'response_bytes_without_headers': '2326',
             'user_agent': 'http://www.example.com/start.html'},
            p.compile().match(self.apache_webserver_combined_log).groupdict()
        )
