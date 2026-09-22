# Contributing

1. 不要提交 API Key、访问令牌或真实请求日志。
2. 新功能必须保留 `response_format=url` 的结果展示路径。
3. 修改脚本后运行：

```sh
python3 -m py_compile scripts/modbapi_imagegen.py
python3 -m unittest discover -s tests -v
```

4. 提交前确认 `git diff --check` 通过。
