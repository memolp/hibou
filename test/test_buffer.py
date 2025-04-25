# -*- coding:utf-8 -*-

import ant.buffer

# 测试Buffer类
# Buffer是一个支持读写的缓冲区，但是它的读写是分开的

b = ant.buffer.Buffer("aaa", 1000)
b.write(b"12312\r\n")
b.write(b"7777\r\n")
b.write(b"8888\r\n")

print(b.size())
b.flip()
print(b.size())
print(b.readline())

print(b.get_value())

