# -*- coding: utf-8 -*-
import re

from django.template import Template, TemplateSyntaxError
from django.template.base import Lexer, Parser, Token, VariableNode

# leave regexp only for vars

VARIABLE_TAG_START = '{{'
VARIABLE_TAG_END = '}}'
TOKEN_TEXT = 0
TOKEN_VAR = 1

tag_re = (re.compile('(%s.*?%s)' %
          (re.escape(VARIABLE_TAG_START), re.escape(VARIABLE_TAG_END))))

class CustomLexer(Lexer):
    def tokenize(self):
        in_tag = False
        lineno = 1
        result = []
        for bit in tag_re.split(self.template_string):
            if bit:
                result.append(self.create_token(bit, None, lineno, in_tag))
            in_tag = not in_tag
            lineno += bit.count('\n')
        return result

    def create_token(self, token_string, position, lineno, in_tag):
        """
        Convert the given token string into a new Token object and return it.
        If in_tag is True, we are processing something that matched a tag,
        otherwise it should be treated as a literal string.
        """
        if in_tag and not self.verbatim:
            if token_string.startswith(VARIABLE_TAG_START):
                token = Token(TOKEN_VAR, token_string[2:-2].strip(), position, lineno)
        else:
            token = Token(TOKEN_TEXT, token_string, position, lineno)
        return token

class CustomTemplateError(TemplateSyntaxError):
    def __unicode__(self):
        regexp = re.compile(r'from \'(.*)\'')
        bad_var = u'{{ ' + re.search(regexp, str(TemplateSyntaxError.__str__(self))).group(1) + u' }}'
        return u'Недопустимая переменная в шаблоне: %s' % bad_var

    def __str__(self):
        return self.__unicode__().encode('utf-8')

class CustomTemplate(Template):

    def __init__(self, *args, **kwargs):
        try:
            super(CustomTemplate, self).__init__(*args, **kwargs)
        except TemplateSyntaxError as e:
            raise CustomTemplateError(e)

    def compile_nodelist(self):
        lexer = CustomLexer(self.source)

        tokens = lexer.tokenize()
        parser = Parser(
            tokens, self.engine.template_libraries, self.engine.template_builtins,
            self.origin,
        )
        try:
            return parser.parse()
        except Exception as e:
            raise

    def get_template_tags(self):
        nodes = self.compile_nodelist()
        tags = [str(item.filter_expression) for item in nodes if isinstance(item, VariableNode)]
        return tags

