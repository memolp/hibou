# -*- coding:utf-8 -*-

import asyncio
import cgi
import importlib
import io
import os
import queue
import re
import selectors
import socket
import ssl
import sys
import time
import logging
import types
import urllib.parse
import uuid
import threading


RESPONSE_CODE_DEFINED = {
    100: 'Continue',
    101: 'Switching Protocols',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
}


MINE_TYPE_DEFINED = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.html': 'text/html',
    '.jpg': 'image/jpg',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.woff': 'text/font',
    '.woff2': 'text/font',
    '.ttf': 'text/font',
    ".xls": "application/xls",
    ".xlsx": "application/xlsx",
    ".doc": "application/doc",
    ".docx": "application/docx",
    ".pdf": "application/pdf",
    ".avi": "application/x-mplayer2",
    ".mp4": "video/mp4",
    ".moc": "application/octet-stream",
    ".json": "text/json",
    ".txt": "text/json",
    ".ico": "image/ico",
    ".mtn": "application/octet-stream",
    ".mp3": "application/octet-stream",
    ".mkv": "application/octet-stream",
    ".zip": "application/octet-stream",
    ".7z": "application/octet-stream",
    ".rar": "application/octet-stream",
    ".ipa": "application/vnd.iphone",
    ".apk": "application/octet-stream",
}


class Utils:

    @staticmethod
    def int_or_none(value):
        # 返回一个整数，如果值为None或无法转换为整数，则返回None
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def to_rfc822(time_local, zone=None):
        # 将本地时间转换为RFC 822格式的字符串
        if zone is None:
            zone = "GMT"
        return time.strftime('%a, %d %b %Y %H:%M:%S {0}'.format(zone), time_local)

    @staticmethod
    def exec_code(code, glob, loc=None):
        # 执行给定的代码字符串
        if isinstance(code, str):
            code = compile(code, '<string>', 'exec', dont_inherit=True)
        exec(code, glob, loc)

    @staticmethod
    def to_utf8(data):
        # 将数据转换为UTF-8编码
        try:
            if isinstance(data, str):
                return data
            elif isinstance(data, bytes):
                return data.decode("utf-8")
            else:
                return str(data)
        except Exception as e:
            logging.exception("to_utf8 error:%s data:%s", e, data)
        return data

    @staticmethod
    def html_escape(data):
        # 将数据进行HTML转义
        if isinstance(data, str):
            return data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#039;")
        return data

    @staticmethod
    def read_range(range_header:str):
        """
        解析请求头中的Range
        :param range_header:
        :return: 开始和结束位置，异常则返回空
        """
        unit, _, value = range_header.partition("=")
        unit, value = unit.strip(), value.strip()
        if unit != "bytes":
            return None
        start_b, _, end_b = value.partition("-")
        start = Utils.int_or_none(start_b)
        end = Utils.int_or_none(end_b)

        if end is not None:
            if start is None:
                if end != 0:
                    start = -end
                    end = None
            else:
                end += 1
        return start, end

    @staticmethod
    def file_modify_date(file_path):
        """
        获取文件的最后修改时间
        :param file_path:
        :return:
        """
        file_mt = time.localtime(os.stat(file_path).st_mtime)
        return Utils.to_rfc822(file_mt)

    @staticmethod
    def get_file_mime_type(filename):
        """ 根据文件扩展名获取文件类型 """
        dot_index = filename.rfind(".")
        if dot_index < 0:
            return "application/octet-stream"
        return MINE_TYPE_DEFINED.get(filename[dot_index:], "application/octet-stream")


class Buffer:
    def __init__(self, name, max_size=1024 * 1024 * 100):
        self.filename = "{0}_temp.dat".format(name)
        self.max_size = max_size
        self.buffer = io.BytesIO()
        self.file_buffer = None
        self.buffer_readable = False
        self.buffer_writeable = True

    def tell(self):
        if self.file_buffer:
            return self.file_buffer.tell()
        else:
            return self.buffer.tell()

    def seek(self, offset, where):
        if self.file_buffer:
            self.file_buffer.seek(offset, where)
        else:
            self.buffer.seek(offset, where)

    def size(self):
        if self.file_buffer:
            pos = self.file_buffer.tell()
            self.file_buffer.seek(0, 2)  # 移动到文件末尾
            size = self.file_buffer.tell()
            self.file_buffer.seek(pos)  # 恢复到原来的位置
            return size
        else:
            pos = self.buffer.tell()
            self.buffer.seek(0, 2)  # 移动到内存末尾
            size = self.buffer.tell()
            self.buffer.seek(pos)  # 恢复到原来的位置
            return size

    def write(self, data):
        assert self.buffer_writeable, "Buffer不可写"
        if self.file_buffer:
            self.file_buffer.write(data)
        else:
            self.buffer.write(data)
            if self.buffer.tell() > self.max_size:
                # 切换到文件IO
                self.file_buffer = io.FileIO(self.filename, "wb")
                self.file_buffer.write(self.buffer.getvalue())
                self.buffer.close()
                self.buffer = None

    def flip(self):
        # Buffer写入完成后，必须调用flip()方法切换到可读状态
        assert self.buffer_writeable, "Buffer不可写"
        if self.file_buffer:
            self.file_buffer.close()
            self.file_buffer = io.FileIO(self.filename, "rb")
            self.buffer_writeable = False
            self.buffer_readable = True
        else:
            self.buffer_writeable = False
            self.buffer_readable = True
            self.buffer.seek(0)

    def read(self, size=-1):
        assert self.buffer_readable, "Buffer不可读"
        if self.file_buffer:
            data = self.file_buffer.read(size)
            return data
        else:
            return self.buffer.read(size)

    def readline(self):
        assert self.buffer_readable, "Buffer不可读"
        if self.file_buffer:
            data = self.file_buffer.readline()
            return data
        else:
            return self.buffer.readline()

    def get_value(self):
        assert self.buffer_readable, "Buffer不可读"
        if self.file_buffer:
            self.file_buffer.seek(0)
            data = self.file_buffer.read()
            return data
        else:
            self.buffer.seek(0)
            return self.buffer.getvalue()


# 模板渲染
class UIModuleNameSpace(object):
    """ """

    def __init__(self, handler, modules):
        """ """
        self.handler = handler
        self.ui_modules = modules

    def __getitem__(self, key):
        """ """
        ui_module = getattr(self.handler, "_ui_module")
        if ui_module:
            return ui_module(key, self.ui_modules[key])
        raise NotImplementedError

    def __getattr__(self, key):
        """ """
        return self[key]


class UIModule(object):
    """ """

    def __init__(self, handler):
        """ """
        self.handler = handler

    def render(self, *args, **kwargs):
        """ """
        pass

    def render_string(self, path, **kwargs):
        """Renders a template and returns it as a string."""
        return self.handler.render_string(path, **kwargs)


class Template(object):
    """ html渲染模版 使用tornado的模版去掉了他里面我不需要的内容重新组成 """

    def __init__(self, template_string, name="<string>", modules=None, compress_whitespace=False):
        """
        template_string  需要渲染的模版文本
        name  可选传入文件名方便识别
        compress_whitespace  是否需要压缩空行和换行等 一般js css需要
        """
        self.name = name
        self.autoescape = "xhtml_escape"
        # modules 模块列表，用于html中引用其他模块 内置对象为 _tt_modules
        self.namespace = {"_tt_modules": modules} if modules else {}
        # 编译资源
        self.compiled = None
        self._compile_code(self.name, template_string, compress_whitespace)

    def generate(self, **kwargs):
        """ 根据指定的参数 生成模版 """
        # 内置的转换函数
        namespace = {
            "escape": Utils.html_escape,
            "xhtml_escape": Utils.html_escape,
            "_tt_utf8": Utils.to_utf8,
        }
        namespace.update(self.namespace)
        namespace.update(kwargs)
        Utils.exec_code(self.compiled, namespace)
        execute = namespace["_tt_execute"]
        return execute()

    def _compile_code(self, name, template_string, compress_whitespace):
        """ 编译模版 """
        # 对模版进行解析
        body = _TemplateReader.parse_template(name, template_string, self)
        # 解析后的资源存入file中等待编译
        temp_file = _File(self, body)
        # 创建内存buff
        buffer = io.StringIO()
        try:
            writer = _CodeWriter(buffer, self, compress_whitespace)
            temp_file.generate(writer)
            self.compiled = compile(buffer.getvalue(), name, "exec", dont_inherit=True)
        except Exception as e:
            logging.exception("compile code error:%s", e)
            raise
        finally:
            buffer.close()


class _Node(object):
    def generate(self, writer):
        raise NotImplementedError()


class _File(_Node):
    def __init__(self, template, body):
        self.template = template
        self.body = body
        self.line = 0

    def generate(self, writer):
        writer.write_line("def _tt_execute():", self.line)
        with writer.indent():
            writer.write_line("_tt_buffer = []", self.line)
            writer.write_line("_tt_append = _tt_buffer.append", self.line)
            self.body.generate(writer)
            writer.write_line("return _tt_utf8('').join(_tt_buffer)", self.line)


class _ChunkList(_Node):
    def __init__(self, chunks):
        self.chunks = chunks

    def generate(self, writer):
        for chunk in self.chunks:
            chunk.generate(writer)


class _ControlBlock(_Node):
    def __init__(self, statement, line, body=None):
        self.statement = statement
        self.line = line
        self.body = body

    def generate(self, writer):
        writer.write_line("%s:" % self.statement, self.line)
        with writer.indent():
            self.body.generate(writer)
            # Just in case the body was empty
            writer.write_line("pass", self.line)


class _IntermediateControlBlock(_Node):
    def __init__(self, statement, line):
        self.statement = statement
        self.line = line

    def generate(self, writer):
        # In case the previous block was empty
        writer.write_line("pass", self.line)
        writer.write_line("%s:" % self.statement, self.line, writer.indent_size() - 1)


class _Statement(_Node):
    def __init__(self, statement, line):
        self.statement = statement
        self.line = line

    def generate(self, writer):
        writer.write_line(self.statement, self.line)


class _Expression(_Node):
    def __init__(self, expression, line, raw=False):
        self.expression = expression
        self.line = line
        self.raw = raw

    def generate(self, writer):
        writer.write_line("_tt_tmp = %s" % self.expression, self.line)
        writer.write_line("_tt_tmp = _tt_utf8(_tt_tmp)", self.line)
        # writer.write_line("if isinstance(_tt_tmp, (str,unicode)):"
        #                  " _tt_tmp = _tt_utf8(_tt_tmp)", self.line)
        # writer.write_line("else: _tt_tmp = _tt_utf8(str(_tt_tmp))", self.line)
        if not self.raw and writer.current_template.autoescape is not None:
            # In python3 functions like xhtml_escape return unicode,
            # so we have to convert to utf8 again.
            writer.write_line("_tt_tmp = _tt_utf8(%s(_tt_tmp))" %
                              writer.current_template.autoescape, self.line)
        writer.write_line("_tt_append(_tt_tmp)", self.line)


class _Module(_Expression):
    def __init__(self, expression, line):
        super(_Module, self).__init__("_tt_modules." + expression, line, raw=True)


class _Text(_Node):
    def __init__(self, value, line):
        self.value = value
        self.line = line

    def generate(self, writer):
        value = self.value

        # Compress lots of white space to a single character. If the whitespace
        # breaks a line, have it continue to break a line, but just with a
        # single \n character
        if writer.compress_whitespace and "<pre>" not in value:
            value = re.sub(r"([\t ]+)", " ", value)
            value = re.sub(r"(\s*\n\s*)", "\n", value)

        if value:
            writer.write_line('_tt_append(%r)' % Utils.to_utf8(value), self.line)


class ParseError(Exception):
    """Raised for template syntax errors."""
    pass


class _CodeWriter(object):
    def __init__(self, file, current_template, compress_whitespace):
        self.file = file
        self.current_template = current_template
        self.compress_whitespace = compress_whitespace
        self._indent = 0

    def indent_size(self):
        return self._indent

    def indent(self):
        this = self

        class indent_context(object):
            def __enter__(self):
                this._indent += 1
                return this

            def __exit__(self, *args):
                assert this._indent > 0
                this._indent -= 1

        return indent_context()

    def write_line(self, line, line_number, indent=None):
        if indent is None:
            indent = self._indent
        line_comment = '  # %s:%d' % (self.current_template.name, line_number)
        # print("    " * indent + line + line_comment,self.file)
        self.file.write("    " * indent + line + line_comment + "\r\n")


class _TemplateReader(object):
    def __init__(self, name, text):
        self.name = name
        self.text = text
        self.line = 1
        self.pos = 0

    def find(self, needle, start=0, end=None):
        assert start >= 0, start
        pos = self.pos
        start += pos
        if end is None:
            index = self.text.find(needle, start)
        else:
            end += pos
            assert end >= start
            index = self.text.find(needle, start, end)
        if index != -1:
            index -= pos
        return index

    def consume(self, count=None):
        if count is None:
            count = len(self.text) - self.pos
        new_pos = self.pos + count
        self.line += self.text.count("\n", self.pos, new_pos)
        s = self.text[self.pos:new_pos]
        self.pos = new_pos
        return s

    def remaining(self):
        return len(self.text) - self.pos

    def __len__(self):
        return self.remaining()

    def __getitem__(self, key):
        if type(key) is slice:
            size = len(self)
            start, stop, step = key.indices(size)
            if start is None:
                start = self.pos
            else:
                start += self.pos
            if stop is not None:
                stop += self.pos
            return self.text[slice(start, stop, step)]
        elif key < 0:
            return self.text[key]
        else:
            return self.text[self.pos + key]

    def __str__(self):
        return self.text[self.pos:]

    @staticmethod
    def parse_template(name, text, template):
        return _TemplateReader._parse(_TemplateReader(name, text), template)

    @staticmethod
    def _parse(reader, template, in_block=None, in_loop=None):
        body = _ChunkList([])
        while True:
            # Find next template directive
            curly = 0
            while True:
                curly = reader.find("{", curly)
                if curly == -1 or curly + 1 == reader.remaining():
                    # EOF
                    if in_block:
                        raise ParseError("Missing {%% end %%} block for %s" %
                                         in_block)
                    body.chunks.append(_Text(reader.consume(), reader.line))
                    return body
                # If the first curly brace is not the start of a special token,
                # start searching from the character after it
                if reader[curly + 1] not in ("{", "%", "#"):
                    curly += 1
                    continue
                # When there are more than 2 curlies in a row, use the
                # innermost ones.  This is useful when generating languages
                # like latex where curlies are also meaningful
                if (curly + 2 < reader.remaining() and
                        reader[curly + 1] == '{' and reader[curly + 2] == '{'):
                    curly += 1
                    continue
                break

            # Append any text before the special token
            if curly > 0:
                cons = reader.consume(curly)
                body.chunks.append(_Text(cons, reader.line))

            start_brace = reader.consume(2)
            line = reader.line

            # Template directives may be escaped as "{{!" or "{%!".
            # In this case output the braces and consume the "!".
            # This is especially useful in conjunction with jquery templates,
            # which also use double braces.
            if reader.remaining() and reader[0] == "!":
                reader.consume(1)
                body.chunks.append(_Text(start_brace, line))
                continue

            # Comment
            if start_brace == "{#":
                end = reader.find("#}")
                if end == -1:
                    raise ParseError("Missing end expression #} on line %d" % line)
                reader.consume(end).strip()
                reader.consume(2)
                continue

            # Expression
            if start_brace == "{{":
                end = reader.find("}}")
                if end == -1:
                    raise ParseError("Missing end expression }} on line %d" % line)
                contents = reader.consume(end).strip()
                reader.consume(2)
                if not contents:
                    raise ParseError("Empty expression on line %d" % line)
                body.chunks.append(_Expression(contents, line))
                continue

            # Block
            assert start_brace == "{%", start_brace
            end = reader.find("%}")
            if end == -1:
                raise ParseError("Missing end block %%} on line %d" % line)
            contents = reader.consume(end).strip()
            reader.consume(2)
            if not contents:
                raise ParseError("Empty block tag ({%% %%}) on line %d" % line)

            operator, space, suffix = contents.partition(" ")
            suffix = suffix.strip()

            # Intermediate ("else", "elif", etc) blocks
            intermediate_blocks = {
                "else": {"if", "for", "while", "try"},
                "elif": {"if"},
                "except": {"try"},
                "finally": {"try"},
            }
            allowed_parents = intermediate_blocks.get(operator)
            if allowed_parents is not None:
                if not in_block:
                    raise ParseError("%s outside %s block" %
                                     (operator, allowed_parents))
                if in_block not in allowed_parents:
                    raise ParseError("%s block cannot be attached to %s block" % (operator, in_block))
                body.chunks.append(_IntermediateControlBlock(contents, line))
                continue

            # End tag
            elif operator == "end":
                if not in_block:
                    raise ParseError("Extra {%% end %%} block on line %d" % line)
                return body

            elif operator in ("set", "autoescape", "raw", "module"):
                block = None
                if operator == "set":
                    if not suffix:
                        raise ParseError("set missing statement on line %d" % line)
                    block = _Statement(suffix, line)
                elif operator == "autoescape":
                    fn = suffix.strip()
                    if fn == "None":
                        fn = None
                    template.autoescape = fn
                    continue
                elif operator == "raw":
                    block = _Expression(suffix, line, raw=True)
                elif operator == "module":
                    block = _Module(suffix, line)
                if block:
                    body.chunks.append(block)
                continue

            elif operator in ("try", "if", "for", "while"):
                # parse inner body recursively
                if operator in ("for", "while"):
                    block_body = _TemplateReader._parse(reader, template, operator, operator)
                else:
                    block_body = _TemplateReader._parse(reader, template, operator, in_loop)

                block = _ControlBlock(contents, line, block_body)
                body.chunks.append(block)
                continue

            elif operator in ("break", "continue"):
                if not in_loop:
                    raise ParseError("%s outside %s block" % (operator, {"for", "while"}))
                body.chunks.append(_Statement(contents, line))
                continue

            else:
                raise ParseError("unknown operator: %r" % operator)


class Field:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return "name={0}, value={1}".format(self.name, self.value)

class FileField:
    def __init__(self, name, filename, filetype, buffer, size:int):
        self.name = name
        self.filename = filename
        self.filetype = filetype
        self._buffer = buffer   #type: io.FileIO or io.BytesIO
        self.size = size

    def __str__(self):
        return "name={0}, filename={1}, type={2}, size={3}".format(self.name, self.filename, self.filetype, self.size)

    def save(self, path):
        with open(path, 'wb') as f:
            content_length = self.size
            while content_length > 0:
                chunk = self._buffer.read(content_length)
                if not chunk:
                    break
                f.write(chunk)
                content_length -= len(chunk)

    def read(self, size):
        assert size <= self.size, "读取超过"
        return self._buffer.read(size)


class MultipartParser:
    def __init__(self, buffer:Buffer, boundary:bytes):
        self.buffer = buffer
        self.boundary = b"--" + boundary
        self.end_boundary = self.boundary + b'--'
        self.leftover = b""
        self.buffer_size = 8192
        self.HTTP_LRE = "\r\n"

    def read_boundary(self):
        size = len(self.boundary) * 2   # 读取
        buf = b""
        while True:
            chunk = self.buffer.read(size)
            if not chunk:
                break
            buf += chunk
            boundary_idx = buf.find(self.boundary)
            if boundary_idx == -1:  # 说明没找到
                buf = chunk     # 将buf指向当前的chunk部分，与下一个chunk拼接后查找
                continue
            # 假设boundary长度为5， 那么读取10字节后，位置在900， 那么开始的位置是890
            # 真正的数据范围是890 + boundary_idx的位置。
            end_pos = self.buffer.tell() - len(buf) + boundary_idx
            # 将buffer的读取位置指向刚好跳过分割位置
            return end_pos
        return -1

    @staticmethod
    def parse_multipart_form_head(data: str):
        # form-data的头内容解析
        # Content-Disposition: form-data; name="name of pdf"; filename="pdf-file.pdf"
        # Content-Type: application/octet-stream
        headers = {}
        for i, item in enumerate(data.split(";")):
            if i == 0:
                kv = item.split(":")
            else:
                kv = item.split("=")
            if len(kv) == 2:
                headers[kv[0].strip().lower()] = kv[1].strip()
        return headers

    def read_headers(self):
        form_headers = {}  # 读取multipart/form-data的头
        while True:
            line = self.buffer.readline()
            if line.startswith(b"\r\n"):  # 读取结束
                break
            headers = self.parse_multipart_form_head(line.decode("utf-8"))
            form_headers.update(headers)
        return form_headers

    def read_data(self, content_length):
        buffer = io.BytesIO()
        while content_length > 0:
            chunk = self.buffer.read(content_length)
            if not chunk:
                break
            buffer.write(chunk)
            content_length -= len(chunk)
        return buffer

    def parse(self):
        # 跳过第一个boundary
        fields = []
        while True:
            field = self.parse_field()
            if not field:
                break
            fields.append(field)
        return fields

    def parse_field(self):
        line = self.buffer.readline()
        if not line or not line.startswith(self.boundary):
            return
        # 结束标记
        if line.startswith(self.end_boundary):
            return
        headers = self.read_headers()
        start_pos = self.buffer.tell()      # 上面已经读取完头，那么这里的起始位置就是body的开始
        end_pos = self.read_boundary()      # 下一个body的开始位置，就是整个body的内容
        if end_pos == -1:
            return
        disposition = headers.get("content-disposition", "")
        name = headers.get("name", "")
        if not disposition or not name or not disposition.startswith("form-data"):
            raise RequestParseException(400, "Bad Request")
        # 只有文件才会有这个字段
        filename = headers.get("filename", "")
        if not filename:
            # 不是文件，则直接读取出里面的内容
            self.buffer.seek(start_pos, io.SEEK_SET)
            value = self.read_data(end_pos - start_pos).getvalue()
            self.buffer.seek(end_pos, io.SEEK_SET)
            return Field(name, value.decode("utf-8").strip(self.HTTP_LRE))
        # 文件数据
        content_type = headers.get("content-type", "")
        size = end_pos - start_pos - 2  # 去掉最后的\r\n
        # 如果文件很小，没有落地，那么直接从内存读取
        if not self.buffer.file_buffer:
            self.buffer.seek(start_pos, io.SEEK_SET)
            value = self.read_data(size)
            self.buffer.seek(end_pos, io.SEEK_SET)
            return FileField(name, filename, content_type, value, size)

        self.buffer.seek(end_pos, io.SEEK_SET)
        value = io.FileIO(self.buffer.filename, "rb")
        value.seek(start_pos, io.SEEK_SET)
        return FileField(name, filename, content_type, value, size)


class HttpConfig:
    def __init__(self):
        self.logger = None      # type: logging.Logger or None
        self.logger_level = logging.INFO   # 日志等级
        self.namespace = {}
        self.static_path = None
        self.upload_path = None
        self.script_path = None
        self.template_path = None
        self.support_static_cache = True
        self.support_chunk = False
        self.support_range = True
        self.max_buff_size = 1024 * 1024 * 10
        self.backlog = 1024
        self.max_thread = 2
        self.runtime_global_params = {}

    def bind_runtime(self, name, runtime):
        if not isinstance(runtime, Runtime):
            raise ValueError("runtime must be an instance of AntRuntime")
        self.namespace[name] = runtime

    def bind_param(self, name, symbol):
        self.runtime_global_params[name] = symbol

    def static_path_root(self, path):
        self.static_path = path

    def upload_path_root(self, path):
        self.upload_path = path

    def script_path_root(self, path):
        self.script_path = path

    def template_path_root(self, path):
        self.template_path = path

    def set_logger(self, logger):
        self.logger = logger

    def set_logger_level(self, level):
        self.logger_level = level


class Runtime:
    def __init__(self):
        pass


class Response:

    def __init__(self):
        self.status_code = 200
        self.msg = ""
        self.headers = {}
        self.cookies = {}
        self.body = io.BytesIO()
        self.version = "HTTP/1.1"

    def set_status(self, code, msg=""):
        self.status_code = code
        if not msg:
            self.msg = RESPONSE_CODE_DEFINED.get(code, "Server Error")
        else:
            self.msg = msg

    def set_header(self, name, value):
        self.headers[name] = value

    def set_cookie(self, name, value, path='/', expires=None):
        self.cookies[name] = f"{name}={value}; Path={path}; Expires={expires}"

    def set_charset(self, charset):
        if "Content-Type" not in self.headers:
            self.headers["Content-Type"] = "text/html; charset={0}".format(charset)
        else:
            self.headers["Content-Type"] += "; charset={0}".format(charset)

    def write(self, text):
        if isinstance(text, str):
            self.body.write(text.encode("utf-8"))
        elif isinstance(text, bytes):
            self.body.write(text)
        else:
            raise ValueError("text must be str or bytes")

    def _before_write_header(self):
        # 提供一个在写入响应头前的处理方法
        if "Content-Type" not in self.headers:
            self.set_header("Content-Type", "text/html; charset=utf-8")
        if "Date" not in self.headers:
            self.set_header("Date", Utils.to_rfc822(time.localtime()))
        if "Content-Length" not in self.headers:
            self.set_header("Content-Length", self.body.tell())

    async def send_header(self, session):
        if self.version == "HTTP/0.9":
            return
        self._before_write_header() # 发送前提供一个处理的接口
        # 写入响应结果
        session.write("{0} {1} {2}\r\n".format(self.version, self.status_code, self.msg))
        # 写入响应头
        for name, value in self.headers.items():
            session.write("{0}: {1}\r\n".format(name, value))
        # 写入Cookies
        for value in self.cookies.values():
            session.write("Set-Cookie: : {0}\r\n".format(value))
        # 头写入完成
        session.write("\r\n")

    async def send_body(self, session):
        session.write_raw(self.body.getvalue())

    def __str__(self):
        return f"Response(status_code={self.status_code}, headers={self.headers}, body={self.body})"


class FileResponse(Response):
    DEFAULT = 0x0
    CHUNKED = 0x1
    RANGE = 0x2

    def __init__(self):
        super().__init__()
        self._file_path = None
        self._range = None
        self._file_size = 0
        self._using_mode = FileResponse.DEFAULT
        self._include_body = True

    def set_file(self, filepath:str, mine_type:str):
        self._file_path = filepath
        self._file_size = os.path.getsize(filepath)
        self.set_header("Content-Type", mine_type)

    def only_header(self):
        self._include_body = False

    def enable_range(self, request_range:str):
        if not Application.ins().range_support:
            return
        max_buff_size = Application.ins().max_buff_size
        start, end = Utils.read_range(request_range)
        if start is None and end is None:
            self.set_header("Content-Range", "bytes */%s" % (self._file_size,))
            self.set_status(416)
            return
        if start is not None and start >= self._file_size:
            self.set_header("Content-Range", "bytes */%s" % (self._file_size,))
            self.set_status(416)
            return
        if end is not None and end >= self._file_size:
            self.set_header("Content-Range", "bytes */%s" % (self._file_size,))
            self.set_status(416)
            return
        # Range: -1024表示从资源末尾往前读取1024个字节的内容
        if start is None and end is not None:
            start = self._file_size - end
        # Range: 0- 表示从资源开始到末尾，为了防止资源过大，这里并不一定需要一次性将全部读取返回
        if end is None:
            end = self._file_size - 1
        read_size = end - start + 1
        if read_size > max_buff_size:
            read_size = max_buff_size
            end = read_size + start - 1
        self.set_header("Content-Range", "bytes %s-%s/%s" % (start, end, self._file_size))
        self.set_header("Content-Length", read_size)
        self.set_status(206)
        self._using_mode = FileResponse.RANGE
        self._range = [start, end]

    def enable_trunked(self):
        if Application.ins().chunk_support:
            self._using_mode = FileResponse.CHUNKED

    def _before_write_header(self):
        super()._before_write_header()
        # 对于开启了缓存的，只会发304过去，不会有body，因此不需要将Content-Length发过去，否则会导致浏览器出异常
        if not self._file_path:
            return
        self.set_header("Content-Disposition", "attachment; filename={0}".format(os.path.basename(self._file_path)))
        # 使用chunked 发送数据，不需要设置Content-Length
        if self._using_mode == FileResponse.CHUNKED:
            self.set_header("Transfer-Encoding", "chunked")
            return
        elif self._using_mode == FileResponse.RANGE and self._range:
            pass
        else:
            self.set_header("Content-Length", self._file_size)

    def write_with_chunk(self, session):
        with open(self._file_path, "rb") as fp:
            while True:
                chunk = fp.read(Application.ins().max_buff_size)
                if not chunk:
                    self._send_chunk(session, b"")
                    break
                self._send_chunk(session, chunk)

    @staticmethod
    def _send_chunk(session, chunk:bytes):
        chunk_size = len(chunk)
        session.write("%X\r\n" % chunk_size)
        if chunk_size > 0:
            session.write_raw(chunk)
        session.write("\r\n")

    def write_with_range(self, session):
        start_pos = self._range[0]
        size = self._range[1]
        with open(self._file_path, "rb") as fp:
            fp.seek(start_pos, io.SEEK_SET)
            chunk = fp.read(size)
            session.write_raw(chunk)

    async def send_body(self, session):
        if not self._file_path:
            return
        if self._using_mode == FileResponse.CHUNKED:
            return self.write_with_chunk(session)
        elif self._using_mode == FileResponse.RANGE and self._range:
            return self.write_with_range(session)
        with open(self._file_path, "rb") as fp:
            while True:
                data = fp.read(Application.ins().max_buff_size)
                if not data:
                    break
                session.write_raw(data)


class Request:
    def __init__(self):
        self.method = "get"
        self.path = "/"
        self.headers = {}
        self.body = None        # type: Buffer or None
        self.version = "HTTP/1.1"
        self.version_number = (1, 1)
        self.cookies = {}
        self.arguments = {}
        self.files = {}

    def clear(self):
        if self.files:
            self.files.clear()
        # 当客户端上传大文件的时候会触发临时落地数据，因此在请求结束后需要清楚掉这个缓存数据
        if not self.body or not isinstance(self.body, Buffer):
            return
        # 清理请求的数据
        if self.body.file_buffer:
            self.body.file_buffer.close()
            os.remove(self.body.filename)

    def get_header(self, name):
        return self.headers.get(name.lower(), None)

    def get_cookie(self, name):
        return self.cookies.get(name, None)

    def get_argument(self, name, default=None):
        values = self.arguments.get(name, None)
        if not values:
            return default
        if isinstance(values, list):
            return values[0]
        return values

    def __str__(self):
        return f"Request(method={self.method}, path={self.path})"


class Session:
    # 默认接收数据大小
    DEFAULT_RECV_SIZE = 1024 * 1024
    DEFAULT_MEMORY_SIZE = 1024 * 1024 * 100

    def __init__(self, client_sock:socket.socket):
        super().__init__()
        self.client_sock = client_sock
        self.session_id = uuid.uuid4().hex
        self.closed = False
        self.read_fd = client_sock.makefile("rb")
        self.write_fd = client_sock.makefile("wb")
        self.raw_buffer = Buffer(self.session_id, self.DEFAULT_MEMORY_SIZE)

    @property
    def remote_ip(self):
        return self.client_sock.getpeername()[0]

    def read(self, size):
        # 读取指定大小字节的数据
        try:
            data = self.read_fd.read(size)
            if not data:
                self.closed = True
            return data
        except Exception as e:
            logging.exception("Error reading data: %s", e)
        return None

    def read_line(self):
        # 读取一行数据
        try:
            line = self.read_fd.readline()
            if not line:
                self.closed = True
                return None
            return line.decode()
        except socket.error as e:
            if e.errno == 10053:
                pass
        except Exception as e:
            logging.exception("Error reading line: %s", e)
        return None

    def write(self, text:str):
        if self.closed:
            return
        try:
            self.write_fd.write(text.encode("utf-8"))
            self.write_fd.flush()
        except socket.error as e:
            if e.errno == 10053:
                self.closed = True

    def write_raw(self, raw:bytes):
        if self.closed:
            return
        try:
            self.write_fd.write(raw)
            self.write_fd.flush()
        except socket.error as e:
            if e.errno == 10053:
                self.closed = True

    def finish(self):
        if self.closed:
            return
        self.write_fd.flush()

    def close(self):
        try:
            self.client_sock.close()
        except socket.error as e:
            logging.error("close session:%s error:%s", self.session_id, e.errno)
        except Exception as e:
            logging.exception("Error closing session: %s", e)


class RequestParseException(Exception):
    def __init__(self, code, msg):
        super().__init__()
        self.code = code
        self.msg = msg
        

class RequestCloseException(Exception):
    def __init__(self):
        super().__init__()


class SessionHandler:
    # 请求链接处理类
    HTTP_LRE = "\r\n"       # HTTP换行符
    def __init__(self, session:Session):
        self.session = session
        self.request = Request()
        self.close_connection = True

    async def do_handler(self):
        # 处理当前session的请求
        try:
            await self.do_parse()
            await self.do_method()
        except RequestCloseException:
            self.close_connection = True
        except RequestParseException as e:
            await self.do_default_response(e.code, e.msg)

        try:
            self.request.clear()
        except Exception as e:
            logging.exception("request clear error:%s", e)

    async def do_method(self):
        route_path = self.request.path
        method_name = self.request.method
        handler_cls = Application.ins().match_route(route_path)
        logging.debug("Session:%s request url:%s method:%s", self.session.session_id, route_path, method_name)
        if handler_cls is None or not issubclass(handler_cls, BaseRequestHandler):
            logging.error("request url:%s not found", route_path)
            raise RequestParseException(400, "Bad Request")
        handler = handler_cls(self.session, self.request)
        if not hasattr(handler, method_name):
            raise RequestParseException(405, "Method Not Allowed")
        method = getattr(handler, method_name)
        if not callable(method):
            raise RequestParseException(405, "Method Not Allowed")
        method()
        await self.do_response(handler.response)

    async def do_response(self, response:Response):
        # 处理响应
        if not isinstance(response, Response):
            raise RequestParseException(500, "Server Error")
        try:
            if self.close_connection:
                response.set_header("Connection", "close")
            else:
                response.set_header("Connection", "keep-alive")
            await response.send_header(self.session)
            await response.send_body(self.session)
            self.session.finish()
        except socket.error as e:
            logging.exception("do_response session:%s error:%s", self.session.session_id, e.errno)
        except Exception as e:
            logging.exception("Error sending response: %s", e)

    async def do_default_response(self, code, message=""):
        # 处理响应
        self.close_connection = True
        if self.request.version == "HTTP/0.9":
            return
        self.session.write("{0} {1} {2}\r\n".format(self.request.version, code, RESPONSE_CODE_DEFINED.get(code, "Server Error")))
        self.session.write("Content-Type: text/html; charset=utf-8\r\n")
        self.session.write("Date: {0}\r\n".format(Utils.to_rfc822(time.localtime())))
        if self.close_connection:
            self.session.write("Connection: close\r\n")
        else:
            self.session.write("Connection: keep-alive\r\n")
        if message:
            self.session.write("Content-Length: {0}\r\n".format(len(message)))
        self.session.write("\r\n")
        self.session.write(message)

    async def do_parse(self):
        # 解析请求头
        await self.parse_method()
        # 非HTTP/0.9的需要解析请求头和请求体
        if self.request.version != "HTTP/0.9":
            await self.parse_header()
            # post 才有请求体
            if self.request.method == "post":
                await self.parse_body()
        # 最后解析参数，因为post的参数在body里面，需要先处理body
        self.do_parse_args()
        if not self.close_connection:
            # POST请求的链接先不复用
            if self.request.method == "post":
                self.close_connection = True
                return
            # 客户端没有提供keep-alive的也不复用
            keep_alive = self.request.get_header("Connection")
            if not keep_alive or keep_alive.lower() == "close":
                self.close_connection = True
                return

    async def parse_method(self):
        # 解析请求行  （Request Line）：
        # 方法：如 GET、POST、PUT、DELETE等，指定要执行的操作。
        # 请求 URI（统一资源标识符）：请求的资源路径，通常包括主机名、端口号（如果非默认）、路径和查询字符串。
        # HTTP 版本：如 HTTP/1.1 或 HTTP/2。
        line = self.session.read_line()
        if not line or not line.endswith(self.HTTP_LRE):
            raise RequestCloseException()
        params = line.split()
        params_size = len(params)
        # HTTP/0.9
        if params_size == 2:
            method, path = params
            if method.upper() != "GET":
                raise RequestParseException(400, "Bad Request")
            version = "HTTP/0.9"
        elif params_size == 3:
            method, path, version = params
        else:
            raise RequestParseException(400, "Bad Request")
        # 检查客户端的HTTP版本
        if version[0:5] != "HTTP/":
            raise RequestParseException(400, "Bad Request")
        base_version_number = version.split('/', 1)[1]
        version_number = base_version_number.split(".")
        if len(version_number) != 2:
            raise RequestParseException(400, "Bad Request")
        version_number = int(version_number[0]), int(version_number[1])
        # 版本大于等于HTTP/1.1时，支持持续链接
        if version_number >= (1, 1):
            self.close_connection = False
        # 目前不支持http/2的版本
        if version_number >= (2, 0):
            raise RequestParseException(400, "Bad Request")
        self.request.version = version.strip()
        self.request.method = method.lower()
        self.request.version_number = version_number
        self.request.path = path

    async def parse_header(self):
        # 解析请求头Request Headers）：
        # 包含了客户端环境信息、请求体的大小（如果有）、客户端支持的压缩类型等。
        # 常见的请求头包括Host、User-Agent、Accept、Accept-Encoding、Content-Length等。
        while True:
            line = self.session.read_line()
            if not line or not line.endswith(self.HTTP_LRE):
                raise RequestParseException(400, "Bad Request")
            if line == self.HTTP_LRE:   # 请求头和请求体之间的分隔符，表示请求头的结束。
                break
            index = line.find(":")
            if index < 0:
                raise RequestParseException(400, "Bad Request")
            key = line[0:index].strip().lower()
            value = line[index + 1:].strip()
            self.request.headers[key] = value
        # 解析出Cookie
        self.do_parse_cookies()

    async def parse_body(self):
        # 解析请求体
        # 在某些类型的HTTP请求（如 POST 和 PUT）中，请求体包含要发送给服务器的数据。
        content_length = self.request.get_header("Content-Length")
        if content_length:  # 前端在请求头里面指定了请求体的大小
            content_length = int(content_length)
            buffer = await self.read_content(content_length)
            if not buffer or not isinstance(buffer, Buffer):
                raise RequestParseException(400, "Bad Request")
            buffer.flip()
            self.request.body = buffer
        else:
            # 前端在请求头里面指定了Transfer-Encoding: chunked，采用chunk上传数据
            tc = self.request.get_header("Transfer-Encoding")
            if tc and tc.lower() == "chunked":
                buffer = await self.read_chunked()
                if not buffer or not isinstance(buffer, Buffer):
                    raise RequestParseException(400, "Bad Request")
                buffer.flip()
                self.request.body = buffer
            else:
                # 都没有那么就按行读取到结束
                buffer = await self.read_body()
                if not buffer or not isinstance(buffer, Buffer):
                    raise RequestParseException(400, "Bad Request")
                buffer.flip()
                self.request.body = buffer

    async def read_chunked(self):
        # 读取Transfer-Encoding: chunked的请求体
        buffer = Buffer(self.session.session_id)
        while True:
            chunk_size = self.session.read_line()
            if not chunk_size or not chunk_size.endswith(self.HTTP_LRE):
                raise RequestParseException(400, "Bad Request")
            chunk_size = int(chunk_size.strip(), 16)
            if chunk_size == 0:
                return buffer
            data = self.session.read(chunk_size)
            if not data:
                raise RequestParseException(400, "Bad Request")
            buffer.write(data)

    async def read_content(self, content_length:int):
        # 读取Content-Length的请求体
        buffer = Buffer(self.session.session_id)
        while content_length > 0:
            chunk = self.session.read(content_length)
            if not chunk:
                break
            buffer.write(chunk)
            content_length -= len(chunk)
        return buffer

    async def read_body(self):
        # 读取其他的请求体
        buffer = Buffer(self.session.session_id)
        while True:
            line = self.session.read_line()
            if not line:
                break
            buffer.write(line.encode())
        return buffer

    def do_parse_args(self):
        index = self.request.path.find("?")
        if index > 0:
            self.request.path, args = self.request.path.split("?", 1)
            self.parse_args(args)
        if self.request.method == "post":
            self.parse_args()

    def do_parse_cookies(self):
        # 解析cookie
        # 其中cookie的格式为：name1=value1; name2=value2; name3=value3
        cookies = self.request.get_header("Cookie")
        if not cookies:
            return
        cookies = cookies.split(";")
        for cookie in cookies:
            k, op, v = cookie.partition("=")
            if op != "=":
                continue
            self.request.cookies[k.strip()] = v.strip()

    def parse_args(self, url_args=None):
        if url_args:
            args = urllib.parse.parse_qs(url_args, keep_blank_values=True)
            self.request.arguments.update(args)
        # 如果请求体是空的，则不需要解析
        buffer = self.request.body
        if not buffer:
            return
        # 解析表单参数
        # application/x-www-form-urlencoded 格式 与URL参数一样
        # multipart/form-data 格式则比较特殊
        # Content-Type: text/html; charset=utf-8
        # Content-Type: multipart/form-data; boundary=something
        content_type = self.request.get_header("Content-Type")
        if not content_type:
            return
        ctype, params = cgi.parse_header(content_type)
        if ctype == "multipart/form-data":
            boundary = params.get("boundary")
            if not boundary:
                return
            self.parse_multipart_form_data(buffer, boundary)
        elif ctype == "application/x-www-form-urlencoded":
            # 这种格式的请求体和URL参数一样 因此不会有太大的数据量，直接读取操作
            args = urllib.parse.parse_qs(buffer.get_value().decode(), keep_blank_values=True)
            self.request.arguments.update(args)

    def parse_multipart_form_data(self, buffer:Buffer, boundary):
        # # 请求头 - 这个是必须的，需要指定Content-Type为multipart/form-data，指定唯一边界值
        # Content-Type: multipart/form-data; boundary=${Boundary}
        #
        # # 请求体
        # --${Boundary}
        # Content-Disposition: form-data; name="name of file"
        # Content-Type: application/octet-stream
        #
        # bytes of file
        # --${Boundary}
        # Content-Disposition: form-data; name="name of pdf"; filename="pdf-file.pdf"
        # Content-Type: application/octet-stream
        #
        # bytes of pdf file
        # --${Boundary}
        # Content-Disposition: form-data; name="key"
        # Content-Type: text/plain;charset=UTF-8
        #
        # text encoded in UTF-8
        # --${Boundary}--
        boundary = boundary.encode("utf-8")
        if boundary.startswith(b'"') and boundary.endswith(b'"'):
            boundary = boundary[1:-1]
        # multipart/form-data流式解析类，解决上传大文件用内存处理会崩的问题。
        # 客户端上传的大文件时，服务器会有一个临时的缓存文件接受内容，通过self.request.files里面的FileField对象进行存储到指定的地方
        # 如果没有调用存储，那么本次响应结束后，缓存数据会删除
        multipart_parser = MultipartParser(buffer, boundary)
        parts = multipart_parser.parse()
        for field in parts:
            if isinstance(field, Field):
                self.request.arguments.setdefault(field.name, []).append(field.value)
            elif isinstance(field, FileField):
                self.request.files.setdefault(field.name, []).append(field)


class BaseRequestHandler:
    def __init__(self, session:Session, request:Request):
        self.session = session
        self.request = request
        self.response = self.setup_response()

    def setup_response(self):
        raise NotImplementedError

    def write(self, body:str):
        self.response.write(body)

    def write_error(self, code, msg="", body=""):
        self.response.set_status(code, msg)
        self.write(body)

    def get(self):
        self.write_error(405)

    def post(self):
        self.write_error(405)

    def head(self):
        self.write_error(400)


class RequestHandler(BaseRequestHandler):
    def __init__(self, session:Session, request:Request):
        super().__init__(session, request)
        self.ui = {}

    def setup_response(self):
        return Response()

    def redirect(self, url, code=None):
        """
        重定向URL，来自bottle的方式，原来我的写法是直接发一个html中带有脚本，执行location.href 赋值跳转
        :param url:
        :param code:
        :return:
        """
        if not code:
            code = 303 if self.request.version == "HTTP/1.1" else 302
        self.response.set_status(code)
        self.response.set_header("Location", url)

    def render(self, file, **kwargs):
        filename = os.path.join(Application.ins().template_path, file)
        if not os.path.exists(filename):
            raise FileExistsError("{0} not found".format(filename))
        if not os.path.isfile(filename):
            raise FileNotFoundError("{0} not file".format(filename))
        with open(filename, "r", encoding="utf-8") as fp:
            self.render_string(fp.read(), filename, **kwargs)

    def render_string(self, html, name, **kwargs):
        t = Template(html, name, self.ui)
        self.write(t.generate(**kwargs))


class StaticFileHandler(RequestHandler):
    # 下载静态文件

    def __init__(self, session:Session, request:Request):
        super().__init__(session, request)

    def setup_response(self):
        return FileResponse()

    def request_info(self, include_body):
        file_path = self.get_file_path()
        if not file_path:
            self.write_error(404, "", "{0} FILE NOT FOUND".format(file_path))
            return False
        # 尝试读取文件的类型
        mine_type = Utils.get_file_mime_type(file_path)
        # 特殊处理head请求，只返回头，不发body数据
        if not include_body:
            self.response.only_header()
        # 客户端想通过range读取数据
        request_range = self.request.get_header("Range")
        if request_range and Application.ins().range_support:
            self.response.set_file(file_path, mine_type)
            self.response.enable_range(request_range)
            return
        # 如果服务器开启了缓存模式
        if Application.ins().static_cache:
            # 检查客户端是否带有缓存请求
            if_modify_date = self.request.get_header("If-Modified-Since")
            cache_control = self.request.get_header("Cache-Control")
            file_modify_date = Utils.file_modify_date(file_path)
            # 如果客户端明确说不使用缓存，那么不走缓存
            if cache_control and cache_control.find("no-store") >= 0:
                self.response.set_file(file_path, mine_type)
                return
            # 服务器建议客户端走缓存
            self.response.set_header("Cache-Control", "max-age=3600")
            self.response.set_header("Last-Modified", file_modify_date)
            # 如果客户端确实有带有文件修改时间，那就检查缓存
            if if_modify_date and if_modify_date == file_modify_date:
                self.response.set_status(304)
                return
        # 如果HTTP/1.1 那么可以让客户端请求使用range模式
        if self.request.version_number >= (1, 1) and Application.ins().range_support:
            self.response.set_header("Accept-Ranges", "bytes")
        # 设置文件路径
        self.response.set_file(file_path, mine_type)

    def head(self):
        """
        head 请求
        """
        self.request_info(False)

    def get(self):
        """
        静态文件get请求
        """
        self.request_info(True)

    def get_file_path(self):
        """
        获取文件的路径
        """
        # 对url进行解码，有可能有带空格的文件之类的
        path = urllib.parse.unquote(self.request.path)
        if not path.startswith("/static/"):
            return None
        path = path[len("/static/"):]
        url_route_path = path if not path.startswith("/") else path[1:]
        file_path = os.path.join(Application.ins().static_path, url_route_path)
        if not os.path.isfile(file_path) or not os.path.exists(file_path):
            return None
        return file_path


class ThreadLoopPool:
    def __init__(self, max_work=2):
        self.max_work = max_work
        self.active_thread = []
        self.task_queue = queue.Queue()
        self._shutdown = False

    def thread_void(self):
        loop = asyncio.new_event_loop()
        while not self._shutdown:
            try:
                if self.task_queue.empty():
                    time.sleep(0.001)
                    continue
                task = self.task_queue.get(False, 1)
                if not task:
                    continue
                fn, params = task[0], task[1]
                fn(loop, *params)
            except Exception as e:
                logging.exception("run task error:%s", e)

    def submit(self, fn, *params):
        size = len(self.active_thread)
        if size < self.max_work:
            p = threading.Thread(target=self.thread_void, args=())
            p.start()
            self.active_thread.append(p)
        task = [fn, params]
        self.task_queue.put(task)

    def shutdown(self):
        self._shutdown = True


class HttpServer:
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.selector = selectors.DefaultSelector()
        self.server_socket = None
        self.routes = {}
        self.session_map = {}
        self.thread_pool = ThreadLoopPool(Application.ins().max_thread)

    def create_server_socket(self):
        # 启动HTTP服务器
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(Application.ins().backlog)
        self.selector.register(self.server_socket, selectors.EVENT_READ, self.accept)
        logging.debug(f"Server started at {self.host}:{self.port}")

    def start(self):
        self.create_server_socket()
        asyncio.run(self.server_loop())

    async def server_loop(self):
        try:
            while True:
                events = self.selector.select(timeout=0.1)
                for key, _ in events:
                    callback = key.data
                    callback(key.fileobj)
                # await asyncio.sleep(0.001)
        except KeyboardInterrupt:
            logging.debug("Server shutting down...")
        finally:
            self.thread_pool.shutdown()
            self.server_socket.close()

    def accept(self, server_socket):
        try:
            client_socket, addr = server_socket.accept()
            logging.debug(f"Connection from {addr}")
            client_socket.setblocking(False)
            self.selector.register(client_socket, selectors.EVENT_READ, self.read)
        except Exception as e:
            logging.exception(f"Error accepting connection: {e}")

    def read(self, client_socket):
        self.selector.unregister(client_socket)
        client_socket.setblocking(True)     # 为了减少write的设计复杂度，这里直接进行切换了socket的阻塞模式。
        session = self.session_map.get(client_socket, None)
        if session is None:
            session = Session(client_socket)
            self.session_map[client_socket] = session
        # loop = asyncio.get_event_loop()
        # loop.create_task(self.handle_session(session))
        self.thread_pool.submit(self.handle_task, session)

    def handle_task(self, loop:asyncio.AbstractEventLoop, session:Session):
        try:
            loop.run_until_complete(self.handle_session(session))
        except Exception as e:
            logging.exception("handle task error:%s", e)

    async def handle_session(self, session:Session):
        handler = SessionHandler(session)
        await handler.do_handler()
        if handler.close_connection:
            session.close()
            logging.debug(f"Session {session.session_id} closed")
            self.session_map.pop(session.client_sock)
        else:
            session.client_sock.setblocking(False)
            self.selector.register(session.client_sock, selectors.EVENT_READ, self.read)


class HttpSSLServer(HttpServer):
    def __init__(self, host, port, cert_file, keyfile):
        super().__init__(host, port)
        self.cert_file = cert_file
        self.keyfile = keyfile

    def create_server_socket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(Application.ins().backlog)
        self.server_socket = ssl.wrap_socket(self.server_socket, certfile=self.cert_file, keyfile=self.keyfile, server_side=True)
        logging.info(f"SSL Server started at {self.host}:{self.port}")


class Application:
    # 单例对象
    _instance = None

    @staticmethod
    def ins():
        if Application._instance is None:
            Application._instance = Application()
        return Application._instance

    def __init__(self):
        super().__init__()
        self.config = None  # type: HttpConfig or None
        self.routes = {}
        self.system_start_handlers = {}
        self.system_stop_handlers = {}

    @property
    def static_cache(self):
        return self.config.support_static_cache

    @property
    def chunk_support(self):
        return self.config.support_chunk

    @property
    def range_support(self):
        return self.config.support_range

    @property
    def static_path(self):
        return self.config.static_path

    @property
    def upload_path(self):
        return self.config.upload_path

    @property
    def template_path(self):
        return self.config.template_path

    @property
    def max_buff_size(self):
        return self.config.max_buff_size

    @property
    def backlog(self):
        return self.config.backlog

    @property
    def max_thread(self):
        return self.config.max_thread

    def get_runtime_argument(self, name):
        return self.config.runtime_global_params.get(name, None)

    def add_route(self, path, handler_cls):
        if not issubclass(handler_cls, BaseRequestHandler):
            raise ValueError("handler_cls must be a subclass of BaseRequestHandler")
        self.routes[path] = handler_cls

    def match_route(self, path):
        if path.startswith("/static/"):
            return StaticFileHandler
        return self.routes.get(path, None)

    def load_all_scripts(self):
        # 加载所有的脚本
        for root, dirs, files in os.walk(self.config.script_path):
            for file in files:
                if not file.endswith(".py"):
                    continue
                # 读取文件内容，编译生成模板
                filename = os.path.join(root, file)
                if not os.path.isfile(filename):
                    continue
                with open(filename, "rb") as fp:
                    code = fp.read()
                code_obj = compile(code, filename, "exec")
                # 创建一个新的模块，然后在模块的__dict__中执行
                module_name = os.path.splitext(filename)[0]
                dynamic_module = types.ModuleType(module_name)
                dynamic_module.__dict__.update(self.config.namespace)
                exec(code_obj, dynamic_module.__dict__)
                # 在全局globals中执行
                # exec(code_obj, globals(), self.config.namespace)

    def start_server(self, config:HttpConfig, host="127.0.0.1", port=8080):
        self.config = config
        if self.config.script_path and os.path.exists(self.config.script_path):
            sys.path.append(self.config.script_path)
            self.load_all_scripts()
        logging.debug("do system start call")
        for name, handle in self.system_start_handlers.items():
            handle()
        server = HttpServer(host, port)
        server.start()
        logging.debug("do system stop call")
        for name, handle in self.system_stop_handlers.items():
            handle()

    def add_system_start_handle(self, handle):
        if not callable(handle):
            raise TypeError("add_system_start_handle: {0} it not callable".format(handle))
        name = handle.__name__
        self.system_start_handlers[name] = handle

    def add_system_stop_handle(self, handle):
        if not callable(handle):
            raise TypeError("add_system_stop_handle: {0} it not callable".format(handle))
        name = handle.__name__
        self.system_stop_handlers[name] = handle

    def reload(self):
        root = os.path.normpath(os.path.abspath(self.config.script_path))
        all_modules = list(sys.modules.values())
        for m in all_modules:
            if not hasattr(m, "__file__") or not m.__file__:
                continue
            filename = os.path.normpath(os.path.abspath(m.__file__))
            if filename.startswith(root):
                importlib.reload(m)
        self.load_all_scripts()


def route(path):
    # 装饰器 绑定路由
    def decorator(cls):
        Application.ins().add_route(path, cls)
        return cls
    return decorator


def start_server(config:HttpConfig, host="127.0.0.1", port=8080):
    # 启动HTTP服务器
    Application.ins().start_server(config, host, port)


def reload():
    Application.ins().reload()


def get_argument(name):
    return Application.ins().get_runtime_argument(name)

def on_start():
    # 程序启动时的回调注册
    def decorator(method):
        Application.ins().add_system_start_handle(method)
        return method
    return decorator


def on_stop():
    # 程序停止时的回调注册
    def decorator(method):
        Application.ins().add_system_stop_handle(method)
        return method
    return decorator


def debug(msg, *args):
    logging.debug(msg, *args)


def info(msg, *args):
    logging.info(msg, *args)


def warning(msg, *args):
    logging.warning(msg, *args)


def error(msg, *args):
    logging.error(msg, *args)


def exception(msg, *args):
    logging.exception(msg, *args)