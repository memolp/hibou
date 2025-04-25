# -*- coding:utf-8 -*-


# 保存上传的文件类
class UploadFile:
    def __init__(self, filename, filetype, filedata):
        self.filename = filename
        self.filetype = filetype
        self.filedata = filedata

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.filedata)
        return path
