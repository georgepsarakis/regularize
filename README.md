# Regular Expression Composer

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
from regex_composer import pattern, finder

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

from regex_composer import pattern

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

## API

### Pattern Builder

### Finder

### Substitution (Replace) 

## Extending

