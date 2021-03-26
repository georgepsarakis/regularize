# regularize - Easily compose regular expressions

![Github Actions Status](https://github.com/georgepsarakis/regularize/actions/workflows/python-app.yml/badge.svg)

## Motivation

Writing complex regular expressions can prove to be difficult and error-prone. This library aims to provide a simple interface for constructing patterns, finding matches and performing substitutions.

### Key Features

- **Pattern Builder:** a clean and robust API to build complex regular expressions.
- **Flag Interface:** easily add and remove flags using a friendly interface.
- **Immutable Pattern Objects:** in order to increase composability and reusability, `Pattern` instances do not modify internal state, but instead return copies with the modifications.
- **Find/Replace with LRU cache:** using a shared cache, different pattern instances that compile to the same regular expression can benefit from the same cache entries.

## Examples

### Match compressed / uncompressed log filenames

```python
from regularize import pattern, finder

# Start a new pattern
logfile_pattern = pattern()

# Create a base pattern for the logfile names
logfile_pattern = logfile_pattern.\
                  literal('application.').\
                  any_number().\
                  quantify(minimum=1).case_insensitive()

uncompressed_logfile = logfile_pattern.literal('.log').end_anchor()
compressed_logfile = logfile_pattern.literal('.log.gz').end_anchor()

print(uncompressed_logfile)
# Expression: /application\.[0-9]+\.log$/

print(compressed_logfile)
# Expression: /application\.[0-9]+\.log\.gz$/

print(finder(uncompressed_logfile).match('application.1.log'))
# <re.Match object; span=(0, 17), match='application.1.log'>
print(finder(compressed_logfile).match('application.1.log.gz'))
# <re.Match object; span=(0, 20), match='application.1.log.gz'>
```

### Match and extract URL components

```python
from urllib.parse import urlparse

from regularize import pattern

# Valid characters for DNS names
ascii_alphanumeric = pattern().lowercase_ascii_letters(). \
    uppercase_ascii_letters().any_number()

domain_pattern = \
    ascii_alphanumeric.close_bracket() + \
    ascii_alphanumeric.literal('-').quantify(1, 61)

# At least one alphanumeric character before the dot and after the dash
domain_pattern += ascii_alphanumeric.close_bracket()

# Add TLD
tld_pattern = pattern().lowercase_ascii_letters(closed=False). \
    uppercase_ascii_letters(). \
    quantify(minimum=2)

# Add optional subdomain group
subdomain_pattern = domain_pattern.\
    group(name='subdomain', optional=True).\
    literal('.').\
    group(optional=True)

# Full domain pattern
domain_pattern = subdomain_pattern + domain_pattern.literal('.') + tld_pattern

# Match HTTP or HTTPS scheme
scheme_pattern = pattern().literal('http').any_of('s').\
    quantify(minimum=0, maximum=1).\
    group('scheme').\
    literal('://')

# Match the URL path (if any exists)
path_pattern = pattern().literal('/').any_number().\
    lowercase_ascii_letters().literal('%-_').\
    quantify(minimum=1).match_all()

# Compose the complete pattern
url_pattern = (scheme_pattern + domain_pattern.group('domain') +
               path_pattern.group(name='path', optional=True)).case_insensitive()

url = 'https://www.example.com/p/1'

compiled_url_pattern = url_pattern.compile()
url_regex_matches = compiled_url_pattern.match(url).groupdict()

parsed_url = urlparse(url)

print(url_regex_matches)
# {'scheme': 'https', 'domain': 'www.example.com', 'subdomain': 'www', 'path': '/p/1'}
print(parsed_url)
# ParseResult(scheme='https', netloc='www.example.com', path='/p/1', params='', query='', fragment='')
assert parsed_url.scheme == url_regex_matches['scheme']
assert parsed_url.hostname == url_regex_matches['domain']
assert parsed_url.path == url_regex_matches['path']
assert url_regex_matches['subdomain'] == 'www'
```

### Parse HTTP Logs

The following example is taken from the common format sample of the [Apache web server combined log](https://httpd.apache.org/docs/current/logs.html#combined).

```python
from regularize.expression import Pattern, pattern

apache_webserver_combined_log = (
    '127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] '
    '"GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" '
    '"Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:84.0) Gecko/20100101 Firefox/84.0"'
)

ip = pattern().any_of('.', Pattern.ANY_NUMBER).quantify(minimum=7).group('ip')
identd_client_id = pattern().literal('-')
http_auth_user = pattern().any_of(Pattern.ANY_ASCII_CHARACTER, '_', '.').\
    at_least_one().group('http_auth_user')
time = pattern().literal('[').none_of(']').quantify(minimum=26).literal(']')
http_verb = pattern().literal('"').group('http_verb',
                                         pattern=pattern().uppercase_ascii_letters().at_least_one())
url = pattern().group(name='url',
                      pattern=pattern().none_of(Pattern.ANY_WHITESPACE).at_least_one())
http_version = pattern().literal('HTTP/').any_of('1', '2').literal('.').\
    any_of('0', '1').group('http_version').literal('"')
http_status_code = pattern().group(name='http_status_code',
                                   pattern=pattern().any_of(Pattern.ANY_NUMBER).exactly(3))
response_bytes = pattern().group(name='response_bytes_without_headers',
                                 pattern=pattern().any_of(Pattern.ANY_NUMBER).at_least_one())
# Note the repetition here. For multiple groups using the same expression,
# we can create a lambda, e.g:
# lambda name: pattern().literal('"').group(name=name, pattern=pattern().none_of('"').at_least_one()).literal('"')
referer = pattern().literal('"').\
    group(name='referer', pattern=pattern().none_of('"').at_least_one()).literal('"')
user_agent = pattern().literal('"').\
    group(name='user_agent', pattern=pattern().none_of('"').at_least_one())

p = Pattern.join(
    pattern().whitespace(),
    [ip, identd_client_id, http_auth_user, time,
     http_verb, url, http_version, http_status_code,
     response_bytes, referer, user_agent]
)
assert {'ip': '127.0.0.1', 'http_auth_user': 'frank', 'http_verb': 'GET', 'url': '/apache_pb.gif',
             'http_version': 'HTTP/1.0', 'http_status_code': '200', 'response_bytes_without_headers': '2326',
             'user_agent': 'http://www.example.com/start.html'} == \
        p.compile().match(apache_webserver_combined_log).groupdict()
```

### Strip HTML tags

```python
from regularize import pattern
from regularize.replace import substitution

html = '''<h1>Article Title</h1>
<p>This is a <b>blog post</b></p>'''
p = pattern().literal('<').any_of('/').quantify(minimum=0).ascii_letters().any_number().at_least_one().literal('>')
s = substitution(p)
text = s.replace(html)
print(text)
'''
Article Title
    This is a blog post
'''
```

## API

### Pattern Builder

### Finder

### Substitution (Replace) 

## Extending

### Writing Extensions

Commonly used patterns can be easily added either by creating a sub-class of the `Pattern` class,
or by using the extension registry.

#### Using a Pattern sub-class

There are two prerequisites for new pattern builder methods:
- The return value should be a `Pattern` instance.
- Internal state is not modified, but instead all changes are applied to an instance clone.

```python
from regularize.expression import Pattern

class MyPattern(Pattern):
    def html_tag(self, opening=True):
        if opening:
            new = self.literal('<')
        else:
            new = self.literal('</')
        return new.any_of(Pattern.ANY_ASCII_CHARACTER).at_least_one().literal('>')    
```  

#### Registering an extension

```python
from regularize.expression import Pattern

class HTMLTag(Pattern):
    def __call__(self, opening=True):
        if opening:
            new = self.literal('<')
        else:
            new = self.literal('</')
        return new.any_of(Pattern.ANY_ASCII_CHARACTER). \
            quantify(minimum=1).literal('>')


p = Pattern()
# The registry is attached to the Pattern class:
Pattern.registry.add('html_tag', HTMLTag)
# But is also accessible through the instance for convenience:
p.extensions.registry.add('html_tag', HTMLTag)
# We can now call the pattern wrapper by its given alias, through the `ext` object:
p = p.ext.html_tag()

print(p.build())
# <[a-z]+>
```
